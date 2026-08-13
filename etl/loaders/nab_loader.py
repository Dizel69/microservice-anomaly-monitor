"""Загрузчик данных NAB (Numenta Anomaly Benchmark).

Источник: https://github.com/numenta/NAB

Файлы NAB — это CSV с колонками ``timestamp`` и ``value``. Меток аномалий
в самих файлах данных нет: официальная разметка лежит отдельно в
``labels/combined_windows.json`` в виде временных окон. Загрузчик находит
этот файл рядом с данными (см. :mod:`etl.labels.nab_labels`) и ставит
``label = 1`` точкам, попавшим в окно, и ``label = 0`` остальным.

Имя сервиса берётся из имени файла
(``ec2_cpu_utilization_5f5533.csv`` -> ``ec2_cpu_utilization_5f5533``),
имя метрики — эвристически из имени файла, а если эвристика не сработала —
из категории NAB (``realTweets`` -> ``tweet_volume``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from etl.labels.nab_labels import (
    NabWindowIndex,
    find_nab_labels_dir,
    label_series_by_windows,
    load_nab_windows,
)
from etl.logging_config import get_logger
from etl.schema import (
    LABEL,
    LABEL_NORMAL,
    METRIC_AD_COST_PER_CLICK,
    METRIC_NAME,
    METRIC_TWEET_VOLUME,
    METRIC_UNKNOWN,
    SERVICE,
    SOURCE,
    SOURCE_NAB,
    TIMESTAMP,
    UNIFIED_COLUMNS,
    VALUE,
    infer_metric_name,
)

logger = get_logger(__name__)

_TIMESTAMP_CANDIDATES: List[str] = ["timestamp", "time", "datetime", "date", "ts"]
_VALUE_CANDIDATES: List[str] = ["value", "val", "metric", "y"]

#: Колонки, однозначно указывающие на другой набор данных (KPI AIOps).
#: NAB-файлы таких колонок не содержат, поэтому их наличие — ошибка вызова.
_FOREIGN_COLUMNS: Dict[str, str] = {
    "kpi id": "KPI",
    "kpi_id": "KPI",
    "kpiid": "KPI",
}

#: Метрика по умолчанию для категории NAB (каталог, в котором лежит файл).
#: Локальные каталоги могут называться короче официальных, поэтому в карте
#: присутствуют оба варианта.
_CATEGORY_METRICS: Dict[str, str] = {
    "artificialnoanomaly": "synthetic_metric",
    "artificialwithanomaly": "synthetic_metric",
    "realadexchange": METRIC_AD_COST_PER_CLICK,
    "realawscloudwatch": "aws_cloudwatch_metric",
    "awscloudwatch": "aws_cloudwatch_metric",
    "realknowncause": "system_metric",
    "knowncause": "system_metric",
    "realtraffic": "traffic_metric",
    "realtweets": METRIC_TWEET_VOLUME,
}


def _find_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    """Найти первую подходящую колонку без учёта регистра."""

    lowered = {col.lower(): col for col in columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def _reject_foreign_dataset(columns: List[str], path: Path) -> None:
    """Прервать загрузку, если CSV принадлежит другому набору данных.

    Защищает от смешения источников: файл KPI, прочитанный загрузчиком NAB,
    получил бы ``source = NAB`` и испортил единый набор.

    Raises:
        ValueError: Если обнаружены колонки чужого набора данных.
    """

    lowered = {col.lower() for col in columns}
    for column, dataset in _FOREIGN_COLUMNS.items():
        if column in lowered:
            raise ValueError(
                f"Файл '{path}' содержит колонку '{column}' и относится к набору "
                f"{dataset}, а не к NAB. Используйте загрузчик {dataset} "
                f"(например, 'python main.py {dataset.lower()}')."
            )


def _resolve_metric(path: Path) -> str:
    """Определить имя метрики по имени файла, затем по категории NAB."""

    inferred = infer_metric_name(path.stem)
    if inferred != METRIC_UNKNOWN:
        return inferred
    return _CATEGORY_METRICS.get(path.parent.name.lower(), METRIC_UNKNOWN)


def _resolve_windows(
    path: Path,
    windows: Optional[NabWindowIndex],
) -> Optional[List[tuple]]:
    """Получить окна аномалий для файла (загрузив индекс при необходимости)."""

    index = windows
    if index is None:
        labels_dir = find_nab_labels_dir(path)
        if labels_dir is None:
            return None
        try:
            index = load_nab_windows(labels_dir)
        except (FileNotFoundError, ValueError) as exc:
            logger.warning("NAB: не удалось загрузить окна аномалий: %s", exc)
            return None
    return index.lookup(path)


def load_nab(
    csv_path: Union[str, Path],
    *,
    service: Optional[str] = None,
    metric_name: Optional[str] = None,
    windows: Optional[NabWindowIndex] = None,
) -> pd.DataFrame:
    """Загрузить CSV-файл NAB и привести к единому формату.

    Args:
        csv_path: Путь к CSV-файлу набора данных NAB.
        service: Имя сервиса. Если ``None`` — берётся из имени файла.
        metric_name: Тип метрики. Если ``None`` — определяется эвристически
            по имени файла и категории.
        windows: Готовый индекс окон аномалий. Если ``None`` — файл меток
            ищется автоматически рядом с данными.

    Returns:
        DataFrame с колонками
        ``timestamp``, ``service``, ``metric_name``, ``value``, ``label``, ``source``.

    Raises:
        FileNotFoundError: Если файл не существует.
        ValueError: Если не удалось определить колонки ``timestamp``/``value``
            либо файл принадлежит другому набору данных.
    """

    path = Path(csv_path)
    logger.info("NAB: загрузка файла %s", path)

    if not path.is_file():
        raise FileNotFoundError(f"Файл NAB не найден: {path}")

    # Заголовок читаем отдельно: это позволяет отбраковать файл чужого набора
    # данных, не вычитывая его целиком (файлы KPI весят сотни мегабайт).
    try:
        header = pd.read_csv(path, nrows=0)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Не удалось прочитать CSV-файл NAB '{path}': {exc}") from exc

    columns = list(header.columns)
    _reject_foreign_dataset(columns, path)

    ts_col = _find_column(columns, _TIMESTAMP_CANDIDATES)
    val_col = _find_column(columns, _VALUE_CANDIDATES)

    if ts_col is None or val_col is None:
        raise ValueError(
            "NAB: не удалось определить колонки timestamp/value. "
            f"Доступные колонки: {columns}"
        )

    try:
        raw = pd.read_csv(path, usecols=[ts_col, val_col])
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Не удалось прочитать CSV-файл NAB '{path}': {exc}") from exc

    if raw.empty:
        logger.warning("NAB: файл %s не содержит строк", path)

    resolved_service = service or path.stem
    resolved_metric = metric_name or _resolve_metric(path)
    logger.info(
        "NAB: service='%s', metric_name='%s'", resolved_service, resolved_metric
    )

    frame = pd.DataFrame()
    frame[TIMESTAMP] = pd.to_datetime(raw[ts_col], errors="coerce")
    frame[SERVICE] = resolved_service
    frame[METRIC_NAME] = resolved_metric
    frame[VALUE] = raw[val_col]

    series_windows = _resolve_windows(path, windows)
    if series_windows is None:
        logger.warning(
            "NAB: окна аномалий для '%s' не найдены, label = %s "
            "(проверьте labels/combined_windows.json)",
            path.name,
            LABEL_NORMAL,
        )
        frame[LABEL] = LABEL_NORMAL
    else:
        frame[LABEL] = label_series_by_windows(frame[TIMESTAMP], series_windows)
        logger.info(
            "NAB: применено %d окон аномалий, размечено %d точек как аномалии",
            len(series_windows),
            int(frame[LABEL].sum()),
        )

    frame[SOURCE] = SOURCE_NAB

    logger.info("NAB: загружено %d строк", len(frame))
    return frame[UNIFIED_COLUMNS]
