"""Очередь моделей на одних данных: fit по ряду, один сводный отчёт.

Prometheus и Zabbix в таблицу качества не попадают. Ансамбль не строится.
Полный KPI / live Prometheus / Zabbix 31M этот модуль сам не загружает.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from etl.config import RAW_NAB_DIR, REPORTS_ROOT
from etl.features.feature_engineering import build_ml_dataset
from etl.labels.nab_labels import NabWindowIndex
from etl.loaders import load_nab
from etl.logging_config import get_logger
from etl.schema import LABEL, SOURCE, TIMESTAMP
from ml.metrics import (
    REPORT_COLUMNS,
    BinaryScores,
    empty_report,
    evaluate_binary,
    is_scored_source,
    report_row,
)
from ml.models import (
    MODEL_FEATURE_COLUMNS,
    OCSVM_MAX_TRAIN,
    TRAIN_ROW_CAPS,
    Detector,
    build_detectors,
    make_detector,
)
from ml.split import SERIES_KEYS, groups_map, split_by_time, split_kpi

logger = get_logger("ml.runner")

ML_REPORTS_DIR: Path = REPORTS_ROOT / "ml"

#: Короткие ряды NAB для дымового прогона (не весь бенчмарк, не unified).
SMOKE_NAB_FILES: Tuple[str, ...] = (
    "realTraffic/speed_7578.csv",
    "realAdExchange/exchange-2_cpc_results.csv",
    "artificialWithAnomaly/art_daily_jumpsup.csv",
)

MIN_TRAIN_POINTS = 5


def ensure_ml_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Вернуть кадр с ``value`` + FEATURE_COLUMNS, без выдуманных признаков."""

    if set(MODEL_FEATURE_COLUMNS).issubset(df.columns):
        return df
    return build_ml_dataset(df)


def _feature_matrix(frame: pd.DataFrame) -> np.ndarray:
    missing = [col for col in MODEL_FEATURE_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"Нет признаков {missing}; сначала build_ml_dataset / add_features")
    return frame[MODEL_FEATURE_COLUMNS].to_numpy(dtype="float64")


def _fresh(detector: Detector) -> Detector:
    return deepcopy(detector)


@dataclass
class PairEval:
    """Оценка одной модели на наборе рядов одного источника."""

    scores: BinaryScores
    n_train: int
    n_test: int
    y_true: np.ndarray
    y_score: np.ndarray
    y_pred: np.ndarray


@dataclass
class SourceModelEval(PairEval):
    """Та же оценка плюс имена модели и источника для отчёта и графиков."""

    model: str
    source: str


def _empty_pair_eval() -> PairEval:
    return PairEval(
        scores=BinaryScores(
            pr_auc=float("nan"),
            precision=float("nan"),
            recall=float("nan"),
            n_scored=0,
            skipped=True,
        ),
        n_train=0,
        n_test=0,
        y_true=np.array([], dtype="float64"),
        y_score=np.array([], dtype="float64"),
        y_pred=np.array([], dtype="int64"),
    )


def _evaluate_model_on_pairs(
    detector_template: Detector,
    pairs: Sequence[Tuple[pd.DataFrame, pd.DataFrame]],
    *,
    max_train: Optional[int] = None,
) -> PairEval:
    """Fit/score по каждому ряду, микро-усреднение на размеченном тесте."""

    y_parts: List[np.ndarray] = []
    score_parts: List[np.ndarray] = []
    pred_parts: List[np.ndarray] = []
    n_train = 0
    n_test = 0
    skipped_ocsvm = 0
    skipped_cap = 0

    for train, test in pairs:
        if len(train) < MIN_TRAIN_POINTS or test.empty:
            continue
        row_cap = TRAIN_ROW_CAPS.get(detector_template.name)
        if row_cap is not None and len(train) > row_cap:
            skipped_ocsvm += 1
            continue
        if max_train is not None and len(train) > max_train:
            skipped_cap += 1
            continue
        n_train += len(train)
        n_test += len(test)
        detector = _fresh(detector_template)
        detector.fit(_feature_matrix(train))
        X_test = _feature_matrix(test)
        y_parts.append(test[LABEL].to_numpy())
        score_parts.append(np.asarray(detector.score(X_test), dtype="float64"))
        pred_parts.append(np.asarray(detector.predict(X_test)))

    if skipped_ocsvm:
        logger.info(
            "%s: пропущено рядов с n_train>%d: %d",
            detector_template.name,
            TRAIN_ROW_CAPS.get(detector_template.name, OCSVM_MAX_TRAIN),
            skipped_ocsvm,
        )
    if skipped_cap:
        logger.info(
            "%s: пропущено рядов с n_train>%d: %d",
            detector_template.name,
            max_train,
            skipped_cap,
        )

    if not y_parts:
        return _empty_pair_eval()

    y_true = np.concatenate(y_parts)
    y_score = np.concatenate(score_parts)
    y_pred = np.concatenate(pred_parts)
    return PairEval(
        scores=evaluate_binary(y_true, y_score, y_pred),
        n_train=n_train,
        n_test=n_test,
        y_true=y_true,
        y_score=y_score,
        y_pred=y_pred,
    )


def _series_pairs(
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    train_map = {
        key: grp.sort_values(TIMESTAMP, kind="mergesort")
        for key, grp in groups_map(train, SERIES_KEYS).items()
    }
    pairs: List[Tuple[pd.DataFrame, pd.DataFrame]] = []
    for key, test_grp in groups_map(test, SERIES_KEYS).items():
        train_grp = train_map.get(key)
        if train_grp is None:
            continue
        pairs.append((train_grp, test_grp.sort_values(TIMESTAMP, kind="mergesort")))
    return pairs


def _resolve_detectors(
    models: Optional[Sequence[Union[str, Detector]]],
    *,
    include_ocsvm: bool,
) -> List[Detector]:
    if models is None:
        return build_detectors(include_ocsvm=include_ocsvm)
    return [item if not isinstance(item, str) else make_detector(item) for item in models]


def iter_source_evals(
    train: pd.DataFrame,
    test: pd.DataFrame,
    detectors: Sequence[Detector],
    *,
    max_train_by_model: Optional[Mapping[str, int]] = None,
) -> List[SourceModelEval]:
    """Оценить каждую модель на каждом размеченном источнике.

    ``PROMETHEUS`` и ``ZABBIX`` не попадают в результат. ``fit`` — по ряду,
    без меток. ``max_train_by_model`` дополнительно отсекает тяжёлые модели
    на длинных рядах (поверх лимита OCSVM).
    """

    train_sources = groups_map(train, [SOURCE])
    test_sources = groups_map(test, [SOURCE])
    found: List[SourceModelEval] = []

    for source, train_src in train_sources.items():
        source_name = str(source)
        if not is_scored_source(source_name):
            logger.info("Источник %s пропущен: нет эталонных меток", source_name)
            continue
        test_src = test_sources.get(source)
        if test_src is None or test_src.empty:
            continue
        pairs = _series_pairs(train_src, test_src)
        for detector in detectors:
            cap = None if max_train_by_model is None else max_train_by_model.get(detector.name)
            logger.info(
                "Считаю %s / %s: рядов %d%s",
                detector.name,
                source_name,
                len(pairs),
                f", лимит n_train<={cap}" if cap is not None else "",
            )
            evaluated = _evaluate_model_on_pairs(detector, pairs, max_train=cap)
            if evaluated.scores.skipped and evaluated.n_train == 0:
                continue
            logger.info(
                "%s / %s: PR-AUC=%s P=%s R=%s n_train=%d n_test=%d",
                detector.name,
                source_name,
                f"{evaluated.scores.pr_auc:.4f}" if evaluated.scores.pr_auc == evaluated.scores.pr_auc else "nan",
                f"{evaluated.scores.precision:.4f}" if evaluated.scores.precision == evaluated.scores.precision else "nan",
                f"{evaluated.scores.recall:.4f}" if evaluated.scores.recall == evaluated.scores.recall else "nan",
                evaluated.n_train,
                evaluated.n_test,
            )
            found.append(
                SourceModelEval(
                    scores=evaluated.scores,
                    n_train=evaluated.n_train,
                    n_test=evaluated.n_test,
                    y_true=evaluated.y_true,
                    y_score=evaluated.y_score,
                    y_pred=evaluated.y_pred,
                    model=detector.name,
                    source=source_name,
                )
            )
    return found


def evals_to_report(evals: Sequence[SourceModelEval]) -> pd.DataFrame:
    """Собрать сводную таблицу из уже посчитанных оценок."""

    if not evals:
        return empty_report()
    rows = [
        report_row(
            model=item.model,
            source=item.source,
            scores=item.scores,
            n_train=item.n_train,
            n_test=item.n_test,
        )
        for item in evals
    ]
    return pd.DataFrame(rows, columns=list(REPORT_COLUMNS))


def run_comparison(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    models: Optional[Sequence[Union[str, Detector]]] = None,
    include_ocsvm: bool = False,
    max_train_by_model: Optional[Mapping[str, int]] = None,
) -> pd.DataFrame:
    """Сравнить модели на уже разбитых train/test. Одна таблица.

    Скейлинг и ``fit`` — внутри каждого ряда. Метки в ``fit`` не передаются.
    Строки по ``PROMETHEUS`` / ``ZABBIX`` не пишутся.
    """

    train_ml = ensure_ml_frame(train)
    test_ml = ensure_ml_frame(test)
    detectors = _resolve_detectors(models, include_ocsvm=include_ocsvm)
    return evals_to_report(
        iter_source_evals(
            train_ml,
            test_ml,
            detectors,
            max_train_by_model=max_train_by_model,
        )
    )


def run_on_frame(
    frame: pd.DataFrame,
    *,
    include_ocsvm: bool = False,
    models: Optional[Sequence[Union[str, Detector]]] = None,
) -> pd.DataFrame:
    """Временной сплит кадра, затем :func:`run_comparison`."""

    ml_frame = ensure_ml_frame(frame)
    train, test = split_by_time(ml_frame)
    return run_comparison(train, test, models=models, include_ocsvm=include_ocsvm)


def run_kpi_frames(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    include_ocsvm: bool = False,
    models: Optional[Sequence[Union[str, Detector]]] = None,
) -> pd.DataFrame:
    """Сравнение на KPI: train-файл vs ground_truth (OCSVM по умолчанию выключен)."""

    train, test = split_kpi(ensure_ml_frame(train_df), ensure_ml_frame(test_df))
    return run_comparison(train, test, models=models, include_ocsvm=include_ocsvm)


def save_report(table: pd.DataFrame, path: Union[str, Path]) -> Path:
    """Записать таблицу в CSV или Parquet. Каталог создаётся при необходимости."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".parquet":
        table.to_parquet(output, index=False)
    else:
        table.to_csv(output, index=False)
    logger.info("Отчёт записан: %s (%d строк)", output, len(table))
    return output


def save_pr_auc_plot(table: pd.DataFrame, path: Union[str, Path]) -> Optional[Path]:
    """Один столбчатый график PR-AUC (не в reports/before и не в current/)."""

    if table.empty or "PR-AUC" not in table.columns:
        return None
    plot_df = table.dropna(subset=["PR-AUC"])
    if plot_df.empty:
        return None
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    labels = [f"{row.model} / {row.source}" for row in plot_df.itertuples()]
    fig, ax = plt.subplots(figsize=(8, 3 + 0.35 * len(plot_df)))
    ax.barh(labels, plot_df["PR-AUC"].astype(float), color="#3b6d99")
    ax.set_xlabel("PR-AUC")
    ax.set_xlim(0.0, 1.0)
    ax.set_title("Сравнение детекторов (размеченный тест)")
    fig.tight_layout()
    fig.savefig(output, dpi=120)
    plt.close(fig)
    return output


def load_nab_series(
    relative_paths: Sequence[str],
    *,
    windows: Optional[NabWindowIndex] = None,
) -> pd.DataFrame:
    """Загрузить указанные CSV NAB через ``load_nab`` (без unified).

    ``windows`` — уже прочитанный ``combined_windows.json``. Если не передан,
    каждый файл ищет окна сам, как раньше.
    """

    frames: List[pd.DataFrame] = []
    for relative in relative_paths:
        path = RAW_NAB_DIR / relative
        if not path.is_file():
            logger.warning("NAB-файл не найден, пропуск: %s", path)
            continue
        frames.append(load_nab(path, windows=windows))
    if not frames:
        raise FileNotFoundError(
            f"Не найдено ни одного NAB-файла из {list(relative_paths)} в {RAW_NAB_DIR}"
        )
    return pd.concat(frames, ignore_index=True)


def run_nab_smoke(
    *,
    files: Optional[Sequence[str]] = None,
    output: Optional[Union[str, Path]] = None,
    include_ocsvm: bool = True,
    plot: bool = True,
) -> pd.DataFrame:
    """Дымовой прогон на 1–3 коротких рядах NAB. Не грузит KPI/Prom/Zabbix."""

    chosen = tuple(files) if files is not None else SMOKE_NAB_FILES
    raw = load_nab_series(chosen)
    ml_frame = build_ml_dataset(raw)
    table = run_on_frame(ml_frame, include_ocsvm=include_ocsvm)
    target = Path(output) if output is not None else ML_REPORTS_DIR / "smoke_nab.csv"
    save_report(table, target)
    if plot:
        save_pr_auc_plot(table, target.with_name(target.stem + "_pr_auc.png"))
    return table
