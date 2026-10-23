"""Сравнение детекторов на NAB и срезе KPI.

Команда: ``python -m ml compare``.

NAB — все CSV из ``datasets/raw/NAB`` (не ``labels/*.json``), метки из
``combined_windows.json``. KPI — не больше ``--kpi-series`` идентификаторов
(по умолчанию 8), которые есть и в ``phase2_train.csv.gz``, и в
``phase2_ground_truth.csv.gz``. Идентификаторы выбираются сортировкой.
Полный кадр KPI (~6 млн строк) в память не собирается: колонка ``KPI ID``
читается потоком, затем через :func:`etl.loaders.load_kpi` проходят только
строки выбранных рядов.

Prometheus, Zabbix и живые parquet сюда не входят. Двенадцать детекторов без
учителя: zscore, iqr, iforest, lof, ocsvm, knn, pca, hbos, mahalanobis,
elliptic, gmm, kmeans. Сплит и ``fit`` по ряду — как в :mod:`ml.runner`.
OCSVM и kNN пропускают ряд, если train длиннее своего порога.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set

import pandas as pd

from etl.config import RAW_KPI_DIR, RAW_NAB_DIR
from etl.labels.nab_labels import find_nab_labels_dir, load_nab_windows
from etl.loaders import load_kpi
from etl.logging_config import get_logger
from etl.schema import SERVICE, SOURCE_KPI, SOURCE_NAB
from ml.models import OCSVM_MAX_TRAIN, build_detectors
from ml.plots import (
    labeled_predictions,
    save_confusion_png,
    save_pr_auc_bars,
    save_pr_overlay,
    save_pr_png,
    save_roc_overlay,
)
from ml.runner import (
    ML_REPORTS_DIR,
    SourceModelEval,
    ensure_ml_frame,
    evals_to_report,
    iter_source_evals,
    load_nab_series,
    save_report,
)
from ml.split import split_by_time, split_kpi

logger = get_logger("ml.compare")

COMPARE_MODELS: tuple[str, ...] = (
    "zscore",
    "iqr",
    "iforest",
    "lof",
    "ocsvm",
    "knn",
    "pca",
    "hbos",
    "mahalanobis",
    "elliptic",
    "gmm",
    "kmeans",
)
SUMMARY_NAME = "compare_summary.csv"
KPI_IDS_NAME = "kpi_slice_ids.txt"
KPI_TRAIN_NAME = "phase2_train.csv.gz"
KPI_TEST_NAME = "phase2_ground_truth.csv.gz"
_KPI_CHUNK = 200_000


def list_nab_csv_files(root: Path = RAW_NAB_DIR) -> List[Path]:
    """Все CSV рядов NAB. JSON разметки и каталог ``labels`` не включаются."""

    files = [
        path
        for path in root.rglob("*.csv")
        if path.is_file() and path.suffix.lower() == ".csv" and "labels" not in path.parts
    ]
    return sorted(files)


def load_all_nab(files: Optional[Sequence[Path]] = None) -> pd.DataFrame:
    """Загрузить перечисленные (или все) ряды NAB одним индексом окон."""

    chosen = list(files) if files is not None else list_nab_csv_files()
    if not chosen:
        raise FileNotFoundError(f"CSV NAB не найдены в {RAW_NAB_DIR}")
    labels_dir = find_nab_labels_dir(RAW_NAB_DIR)
    windows = load_nab_windows(labels_dir) if labels_dir is not None else None
    if windows is None:
        logger.warning("NAB: combined_windows.json не найден, метки останутся нулевыми")
    relative = [path.relative_to(RAW_NAB_DIR).as_posix() for path in chosen]
    frame = load_nab_series(relative, windows=windows)
    logger.info("NAB: файлов %d, строк %d", len(relative), len(frame))
    return frame


def _compression(path: Path) -> str:
    return "gzip" if path.name.lower().endswith(".gz") else "infer"


def _kpi_id_column(path: Path) -> str:
    header = pd.read_csv(path, nrows=0, compression=_compression(path))
    for column in header.columns:
        normalized = column.lower().replace("_", "").replace(" ", "")
        if normalized == "kpiid":
            return column
    raise ValueError(f"В {path} нет колонки KPI ID. Колонки: {list(header.columns)}")


def _scan_kpi_ids(path: Path) -> Set[str]:
    """Множество KPI ID. В память попадает только колонка идентификатора."""

    column = _kpi_id_column(path)
    found: Set[str] = set()
    reader = pd.read_csv(
        path,
        usecols=[column],
        chunksize=_KPI_CHUNK,
        compression=_compression(path),
    )
    for chunk in reader:
        found.update(chunk[column].dropna().astype(str).unique().tolist())
    return found


def select_kpi_ids(train_path: Path, test_path: Path, n: int) -> List[str]:
    """Первые ``n`` общих KPI ID в лексикографическом порядке."""

    if n < 1:
        raise ValueError("Число рядов KPI должно быть не меньше 1")
    common = sorted(_scan_kpi_ids(train_path) & _scan_kpi_ids(test_path))
    chosen = common[:n]
    logger.info(
        "KPI: общих id %d, в срез %d",
        len(common),
        len(chosen),
    )
    return chosen


def write_kpi_slice_ids(ids: Sequence[str], path: Path) -> Path:
    """Записать выбранные KPI ID, по одному на строку."""

    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(ids)
    path.write_text(f"{body}\n" if body else "", encoding="utf-8")
    logger.info("Список KPI ID: %s (%d)", path, len(ids))
    return path


def load_kpi_ids(path: Path, ids: Sequence[str]) -> pd.DataFrame:
    """Прочитать только перечисленные KPI ID и прогнать их через ``load_kpi``.

    Остальные строки чанка отбрасываются и в итоговый кадр не попадают.
    """

    if not ids:
        raise ValueError(f"Пустой список KPI ID для {path}")
    column = _kpi_id_column(path)
    wanted = {str(item) for item in ids}
    with tempfile.TemporaryDirectory(prefix="ml-kpi-slice-") as tmp:
        dest = Path(tmp) / "slice.csv"
        wrote = False
        reader = pd.read_csv(path, chunksize=_KPI_CHUNK, compression=_compression(path))
        for chunk in reader:
            part = chunk[chunk[column].astype(str).isin(wanted)]
            if part.empty:
                continue
            part.to_csv(dest, mode="a", header=not wrote, index=False)
            wrote = True
        if not wrote:
            raise ValueError(f"В {path} нет строк для KPI ID: {list(ids)}")
        frame = load_kpi(dest)
    logger.info("KPI: из %s загружено %d строк, рядов %d", path.name, len(frame), frame[SERVICE].nunique())
    return frame


def _ids_present_in_both(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    n: int,
) -> List[str]:
    left = set(train_df[SERVICE].astype(str))
    right = set(test_df[SERVICE].astype(str))
    return sorted(left & right)[:n]


def _filter_services(frame: pd.DataFrame, ids: Sequence[str]) -> pd.DataFrame:
    wanted = {str(item) for item in ids}
    return frame.loc[frame[SERVICE].astype(str).isin(wanted)].copy()


def _heavy_cap(limit: Optional[int]) -> Optional[dict]:
    """Лимит n_train только для LOF и OCSVM. Z-score и Isolation Forest без него."""

    if limit is None:
        return None
    return {"lof": int(limit), "ocsvm": int(limit)}


def _plot_source(items: Sequence[SourceModelEval], table: pd.DataFrame, output: Path) -> None:
    if not items:
        return
    source = items[0].source
    curves = []
    for item in items:
        y_true, y_score, y_pred = labeled_predictions(item.y_true, item.y_score, item.y_pred)
        title = f"{item.model} / {source}"
        save_confusion_png(
            y_true,
            y_pred,
            output / f"cm_{source}_{item.model}.png",
            title=f"Матрица ошибок: {title}",
        )
        save_pr_png(
            y_true,
            y_score,
            output / f"pr_{source}_{item.model}.png",
            title=f"PR-кривая: {title}",
        )
        curves.append((item.model, y_true, y_score))
    save_pr_overlay(
        curves,
        output / f"pr_curves_{source}.png",
        title=f"PR-кривые моделей, {source}",
    )
    save_roc_overlay(
        curves,
        output / f"roc_curves_{source}.png",
        title=f"ROC, {source} (справочно; главная метрика — PR-AUC)",
    )
    subset = table.loc[table["source"] == source]
    save_pr_auc_bars(
        subset,
        output / f"pr_auc_bars_{source}.png",
        title=f"PR-AUC по моделям, {source}",
    )


def run_compare(
    *,
    nab: bool = True,
    kpi: bool = True,
    kpi_series: int = 8,
    output_dir: Path = ML_REPORTS_DIR,
    models: Optional[Sequence[str]] = None,
    nab_frame: Optional[pd.DataFrame] = None,
    kpi_train: Optional[pd.DataFrame] = None,
    kpi_test: Optional[pd.DataFrame] = None,
    kpi_ids: Optional[Sequence[str]] = None,
    write_kpi_ids: bool = True,
    nab_heavy_max_train: Optional[int] = None,
) -> pd.DataFrame:
    """Сравнить модели и записать CSV/PNG в ``output_dir``.

    ``nab_frame`` / ``kpi_train`` / ``kpi_test`` подменяют чтение с диска
    (для тестов на синтетике). ``nab_heavy_max_train`` ограничивает LOF и
    OCSVM на NAB рядами с ``n_train`` не выше порога; zscore и iforest
    остаются на всех рядах. ``None`` — без дополнительного порога
    (у OCSVM остаётся свой :data:`OCSVM_MAX_TRAIN`).
    """

    if not nab and not kpi:
        raise ValueError("Нужен хотя бы один источник: NAB или KPI")
    if kpi and kpi_series < 1:
        raise ValueError("Число рядов KPI должно быть не меньше 1")
    if nab_heavy_max_train is not None and nab_heavy_max_train < 1:
        raise ValueError("nab_heavy_max_train должен быть >= 1")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    chosen_models = list(models) if models is not None else list(COMPARE_MODELS)
    detectors = build_detectors(chosen_models)
    model_order = {name: index for index, name in enumerate(chosen_models)}
    source_order = {SOURCE_NAB: 0, SOURCE_KPI: 1}
    evals: List[SourceModelEval] = []

    if nab:
        raw_nab = nab_frame if nab_frame is not None else load_all_nab()
        nab_ml = ensure_ml_frame(raw_nab)
        train, test = split_by_time(nab_ml)
        if nab_heavy_max_train is not None:
            logger.info(
                "NAB: lof/ocsvm только на рядах с n_train<=%d (zscore/iforest — все ряды)",
                nab_heavy_max_train,
            )
        evals.extend(
            iter_source_evals(
                train,
                test,
                detectors,
                max_train_by_model=_heavy_cap(nab_heavy_max_train),
            )
        )

    if kpi:
        if kpi_train is None or kpi_test is None:
            train_path = RAW_KPI_DIR / KPI_TRAIN_NAME
            test_path = RAW_KPI_DIR / KPI_TEST_NAME
            ids = select_kpi_ids(train_path, test_path, kpi_series)
            kpi_train_df = load_kpi_ids(train_path, ids)
            kpi_test_df = load_kpi_ids(test_path, ids)
        else:
            ids = (
                list(kpi_ids)
                if kpi_ids is not None
                else _ids_present_in_both(kpi_train, kpi_test, kpi_series)
            )
            kpi_train_df = _filter_services(kpi_train, ids)
            kpi_test_df = _filter_services(kpi_test, ids)
        if write_kpi_ids:
            write_kpi_slice_ids(ids, output / KPI_IDS_NAME)
        train, test = split_kpi(
            ensure_ml_frame(kpi_train_df),
            ensure_ml_frame(kpi_test_df),
        )
        evals.extend(iter_source_evals(train, test, detectors))

    evals.sort(key=lambda item: (source_order.get(item.source, 9), model_order.get(item.model, 9)))
    table = evals_to_report(evals)
    save_report(table, output / SUMMARY_NAME)
    by_source: dict[str, List[SourceModelEval]] = {}
    for item in evals:
        by_source.setdefault(item.source, []).append(item)
    for items in by_source.values():
        _plot_source(items, table, output)
    if nab_heavy_max_train == OCSVM_MAX_TRAIN:
        logger.info(
            "Дополнительный лимит NAB для lof/ocsvm совпадает с OCSVM_MAX_TRAIN=%d",
            OCSVM_MAX_TRAIN,
        )
    return table


def iter_artifact_names(sources: Iterable[str], models: Sequence[str]) -> List[str]:
    """Имена PNG, которые ``run_compare`` пишет для пар (source, model) и сводов."""

    names: List[str] = []
    for source in sources:
        for model in models:
            names.append(f"cm_{source}_{model}.png")
            names.append(f"pr_{source}_{model}.png")
        names.append(f"pr_curves_{source}.png")
        names.append(f"pr_auc_bars_{source}.png")
        names.append(f"roc_curves_{source}.png")
    return names
