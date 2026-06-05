"""Загрузчик данных NAB (Numenta Anomaly Benchmark).

Источник: https://github.com/numenta/NAB

Файлы NAB — это CSV с колонками ``timestamp`` и ``value``. Имя сервиса и тип
метрики выводятся из имени файла (например,
``ec2_cpu_utilization_5f5533.csv`` -> service=``ec2_cpu_utilization_5f5533``,
metric_name=``cpu_usage``). Метки аномалий в самих файлах данных, как правило,
отсутствуют, поэтому при отсутствии колонки ``label`` ей присваивается ``0``.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

from etl.logging_config import get_logger
from etl.schema import (
    LABEL,
    LABEL_NORMAL,
    METRIC_NAME,
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
_LABEL_CANDIDATES: List[str] = ["label", "is_anomaly", "anomaly"]


def _find_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    """Найти первую подходящую колонку без учёта регистра."""

    lowered = {col.lower(): col for col in columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def load_nab(
    csv_path: Union[str, Path],
    *,
    service: Optional[str] = None,
    metric_name: Optional[str] = None,
) -> pd.DataFrame:
    """Загрузить CSV-файл NAB и привести к единому формату.

    Args:
        csv_path: Путь к CSV-файлу набора данных NAB.
        service: Имя сервиса. Если ``None`` — берётся из имени файла.
        metric_name: Тип метрики. Если ``None`` — определяется эвристически
            по имени файла.

    Returns:
        DataFrame с колонками
        ``timestamp``, ``service``, ``metric_name``, ``value``, ``label``, ``source``.

    Raises:
        FileNotFoundError: Если файл не существует.
        ValueError: Если не удалось определить колонки ``timestamp``/``value``.
    """

    path = Path(csv_path)
    logger.info("NAB: загрузка файла %s", path)

    if not path.is_file():
        raise FileNotFoundError(f"Файл NAB не найден: {path}")

    try:
        raw = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Не удалось прочитать CSV-файл NAB '{path}': {exc}") from exc

    if raw.empty:
        logger.warning("NAB: файл %s не содержит строк", path)

    columns = list(raw.columns)
    ts_col = _find_column(columns, _TIMESTAMP_CANDIDATES)
    val_col = _find_column(columns, _VALUE_CANDIDATES)

    if ts_col is None or val_col is None:
        raise ValueError(
            "NAB: не удалось определить колонки timestamp/value. "
            f"Доступные колонки: {columns}"
        )

    label_col = _find_column(columns, _LABEL_CANDIDATES)

    resolved_service = service or path.stem
    resolved_metric = metric_name or infer_metric_name(path.stem)
    logger.info(
        "NAB: service='%s', metric_name='%s'", resolved_service, resolved_metric
    )

    frame = pd.DataFrame()
    frame[TIMESTAMP] = raw[ts_col]
    frame[SERVICE] = resolved_service
    frame[METRIC_NAME] = resolved_metric
    frame[VALUE] = raw[val_col]

    if label_col is not None:
        logger.info("NAB: обнаружена колонка меток '%s'", label_col)
        frame[LABEL] = raw[label_col]
    else:
        logger.info("NAB: колонка меток отсутствует, label = %s", LABEL_NORMAL)
        frame[LABEL] = LABEL_NORMAL

    frame[SOURCE] = SOURCE_NAB

    logger.info("NAB: загружено %d строк", len(frame))
    return frame[UNIFIED_COLUMNS]
