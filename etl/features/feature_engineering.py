"""Инженерия признаков для моделей обнаружения аномалий.

Рассчитываются скользящие статистики и разностные признаки по каждому
временному ряду, идентифицируемому тройкой (``source``, ``service``,
``metric_name``). Полученный набор пригоден для алгоритмов вида
Isolation Forest, One-Class SVM, LOF и т. п.

Рассчитываемые признаки:

* ``rolling_mean_5``, ``rolling_mean_15``  — скользящее среднее;
* ``rolling_std_5``, ``rolling_std_15``    — скользящее СКО;
* ``rolling_min_5``, ``rolling_max_5``     — скользящие минимум/максимум;
* ``delta``                                — разность с предыдущим значением;
* ``percent_change``                       — относительное изменение.
"""

from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

from etl.logging_config import get_logger
from etl.schema import (
    LABEL,
    METRIC_NAME,
    SERVICE,
    SOURCE,
    TIMESTAMP,
    UNIFIED_COLUMNS,
    VALUE,
)

logger = get_logger(__name__)

#: Колонки-признаки, формируемые модулем.
FEATURE_COLUMNS: List[str] = [
    "rolling_mean_5",
    "rolling_mean_15",
    "rolling_std_5",
    "rolling_std_15",
    "rolling_min_5",
    "rolling_max_5",
    "delta",
    "percent_change",
]

#: Колонки, идентифицирующие отдельный временной ряд.
_GROUP_KEYS = [SOURCE, SERVICE, METRIC_NAME]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Добавить инженерные признаки к нормализованному набору данных.

    Args:
        df: Нормализованный DataFrame единого формата.

    Returns:
        DataFrame с исходными колонками и добавленными признаками
        из :data:`FEATURE_COLUMNS`.

    Raises:
        ValueError: Если отсутствуют обязательные колонки.
    """

    required = set(UNIFIED_COLUMNS)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Отсутствуют обязательные колонки: {sorted(missing)}")

    if df.empty:
        logger.warning("Feature engineering: пустой DataFrame")
        empty = df.copy()
        for col in FEATURE_COLUMNS:
            empty[col] = pd.Series(dtype="float64")
        return empty

    logger.info(
        "Feature engineering: %d строк, %d временных рядов",
        len(df),
        df.groupby(_GROUP_KEYS, dropna=False).ngroups,
    )

    enriched = df.sort_values([*_GROUP_KEYS, TIMESTAMP]).reset_index(drop=True)
    grouped = enriched.groupby(_GROUP_KEYS, dropna=False, sort=False)[VALUE]

    enriched["rolling_mean_5"] = grouped.transform(
        lambda s: s.rolling(window=5, min_periods=1).mean()
    )
    enriched["rolling_mean_15"] = grouped.transform(
        lambda s: s.rolling(window=15, min_periods=1).mean()
    )
    enriched["rolling_std_5"] = grouped.transform(
        lambda s: s.rolling(window=5, min_periods=1).std()
    ).fillna(0.0)
    enriched["rolling_std_15"] = grouped.transform(
        lambda s: s.rolling(window=15, min_periods=1).std()
    ).fillna(0.0)
    enriched["rolling_min_5"] = grouped.transform(
        lambda s: s.rolling(window=5, min_periods=1).min()
    )
    enriched["rolling_max_5"] = grouped.transform(
        lambda s: s.rolling(window=5, min_periods=1).max()
    )
    enriched["delta"] = grouped.transform(lambda s: s.diff()).fillna(0.0)
    enriched["percent_change"] = (
        grouped.transform(lambda s: s.pct_change())
        .replace([np.inf, -np.inf], 0.0)
        .fillna(0.0)
    )

    logger.info("Feature engineering: добавлено %d признаков", len(FEATURE_COLUMNS))
    return enriched


def build_ml_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Сформировать финальный ML-набор для обучения моделей.

    Возвращает колонки-идентификаторы, значение, метку и все признаки —
    без NaN в признаках, пригодные для Isolation Forest и др.

    Args:
        df: DataFrame с уже рассчитанными признаками (см. :func:`add_features`).

    Returns:
        DataFrame с колонками: идентификаторы, ``value``, признаки, ``label``.
    """

    enriched = df if set(FEATURE_COLUMNS).issubset(df.columns) else add_features(df)

    ordered = [
        TIMESTAMP,
        SOURCE,
        SERVICE,
        METRIC_NAME,
        VALUE,
        *FEATURE_COLUMNS,
        LABEL,
    ]
    ml = enriched[ordered].copy()
    ml[FEATURE_COLUMNS] = ml[FEATURE_COLUMNS].fillna(0.0)

    logger.info(
        "ML-набор сформирован: %d строк, %d признаков", len(ml), len(FEATURE_COLUMNS)
    )
    return ml
