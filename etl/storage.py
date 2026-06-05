"""Хранение наборов данных ETL-конвейера.

Основной формат — Apache Parquet (компактно, с типами и сжатием).
CSV используется только как формат экспорта для совместимости.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from etl.logging_config import get_logger

logger = get_logger(__name__)

PARQUET_ENGINE = "pyarrow"
PARQUET_COMPRESSION = "snappy"


def save_parquet(df: pd.DataFrame, path: Path) -> Path:
    """Сохранить DataFrame в формате Parquet.

    Args:
        df: Данные для сохранения.
        path: Путь к ``.parquet``-файлу.

    Returns:
        Абсолютный путь к сохранённому файлу.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(
        path, engine=PARQUET_ENGINE, compression=PARQUET_COMPRESSION, index=False
    )
    resolved = path.resolve()
    logger.info("Parquet сохранён: %s (%d строк)", resolved, len(df))
    return resolved


def save_csv(df: pd.DataFrame, path: Path) -> Path:
    """Экспортировать DataFrame в CSV.

    Args:
        df: Данные для экспорта.
        path: Путь к ``.csv``-файлу.

    Returns:
        Абсолютный путь к сохранённому файлу.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    resolved = path.resolve()
    logger.info("CSV экспортирован: %s (%d строк)", resolved, len(df))
    return resolved


def read_parquet(path: Path) -> pd.DataFrame:
    """Загрузить DataFrame из Parquet-файла."""

    return pd.read_parquet(path, engine=PARQUET_ENGINE)
