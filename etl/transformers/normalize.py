"""Нормализация и очистка унифицированного DataFrame (уровень PROCESSED).

Шаги нормализации:

1. ``timestamp`` -> ``datetime``;
2. ``value`` -> ``float``;
3. приведение ``service`` / ``metric_name`` / ``source`` к строкам;
4. удаление строк с пропусками (NaN) в обязательных колонках;
5. удаление дубликатов;
6. сортировка по (``source``, ``service``, ``metric_name``, ``timestamp``).
"""

from __future__ import annotations

import pandas as pd

from etl.logging_config import get_logger
from etl.schema import (
    LABEL,
    LABEL_UNKNOWN,
    METRIC_NAME,
    METRIC_UNKNOWN,
    SERVICE,
    SOURCE,
    TIMESTAMP,
    UNIFIED_COLUMNS,
    VALUE,
)

logger = get_logger(__name__)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Привести DataFrame к чистому нормализованному виду (PROCESSED).

    Args:
        df: Входной DataFrame единого формата (как минимум ``timestamp`` и
            ``value``).

    Returns:
        Нормализованный DataFrame с колонками
        ``timestamp``, ``service``, ``metric_name``, ``value``, ``label``,
        ``source``: без NaN и дубликатов, отсортированный по времени.

    Raises:
        ValueError: Если во входных данных отсутствуют обязательные колонки.
    """

    missing = [col for col in (TIMESTAMP, VALUE) if col not in df.columns]
    if missing:
        raise ValueError(f"Отсутствуют обязательные колонки: {missing}")

    work = df.copy()
    rows_before = len(work)
    logger.info("Нормализация: на входе %d строк", rows_before)

    # 1. timestamp -> datetime
    work[TIMESTAMP] = pd.to_datetime(work[TIMESTAMP], errors="coerce", utc=False)

    # 2. value -> float
    work[VALUE] = pd.to_numeric(work[VALUE], errors="coerce").astype("float64")

    # 3. категориальные/строковые колонки и значения по умолчанию
    if SERVICE not in work.columns:
        work[SERVICE] = "unknown_service"
    if METRIC_NAME not in work.columns:
        work[METRIC_NAME] = METRIC_UNKNOWN
    if LABEL not in work.columns:
        work[LABEL] = LABEL_UNKNOWN
    if SOURCE not in work.columns:
        work[SOURCE] = "UNKNOWN"

    for col in (SERVICE, METRIC_NAME, SOURCE):
        work[col] = work[col].astype(str)

    work[LABEL] = pd.to_numeric(work[LABEL], errors="coerce").fillna(LABEL_UNKNOWN)
    work[LABEL] = work[LABEL].astype(int)

    # 4. удаление NaN в обязательных колонках
    work = work.dropna(subset=[TIMESTAMP, VALUE])
    logger.info("Нормализация: после удаления NaN осталось %d строк", len(work))

    # 5. удаление дубликатов
    work = work.drop_duplicates(subset=UNIFIED_COLUMNS)
    logger.info("Нормализация: после удаления дубликатов осталось %d строк", len(work))

    # 6. сортировка
    work = work.sort_values(
        by=[SOURCE, SERVICE, METRIC_NAME, TIMESTAMP]
    ).reset_index(drop=True)

    result = work[UNIFIED_COLUMNS]
    logger.info("Нормализация завершена: %d -> %d строк", rows_before, len(result))
    return result
