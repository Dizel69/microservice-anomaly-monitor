"""Загрузчик ранее восстановленных дампов Zabbix (parquet/CSV).

Живой HTTP API здесь не вызывается: вход — файлы, которые собрал
``scripts/restore_zabbix_dumps.py`` (history и trends раздельно, ``label=-1``).

``metric_name`` берётся из дампа как есть (ключ item ``key_``, для trends —
с суффиксом ``{grain="trend_avg"}``). Каноникализация в ``cpu_usage`` и т. п.
не применяется: ключи Zabbix — допустимые имена рядов.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

import pandas as pd

from etl.logging_config import get_logger
from etl.schema import (
    LABEL,
    LABELS,
    LABEL_UNKNOWN,
    SOURCE,
    SOURCE_ZABBIX,
    UNIFIED_COLUMNS,
)

logger = get_logger(__name__)

#: Колонки загрузчика Zabbix (единый формат + RAW-метки, если были).
ZABBIX_COLUMNS: List[str] = [*UNIFIED_COLUMNS, LABELS]


def load_zabbix_dump(path: Union[str, Path]) -> pd.DataFrame:
    """Загрузить parquet/CSV Zabbix и привести к единой схеме.

    Args:
        path: Путь к ``.parquet`` или ``.csv`` (не ``pg_dump -Fc``).

    Returns:
        DataFrame с колонками единого формата плюс ``labels``, если колонка
        была в файле.

    Raises:
        FileNotFoundError: Если файл не существует.
        ValueError: Если формат неподдерживаемый или нет обязательных колонок.
    """

    file_path = Path(path)
    logger.info("ZABBIX: загрузка дампа %s", file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Дамп Zabbix не найден: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix == ".parquet":
        frame = pd.read_parquet(file_path)
    elif suffix == ".csv":
        frame = pd.read_csv(file_path)
    else:
        raise ValueError(
            f"Неподдерживаемый формат дампа Zabbix (нужен parquet/csv, не .dump): {file_path}"
        )

    missing = [col for col in UNIFIED_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(
            f"В дампе Zabbix отсутствуют колонки {missing}: {file_path}"
        )

    frame[SOURCE] = SOURCE_ZABBIX
    # Эталонной разметки аномалий нет: любые метки в файле заменяются на -1.
    frame[LABEL] = LABEL_UNKNOWN

    extra = [LABELS] if LABELS in frame.columns else []
    logger.info("ZABBIX: из дампа загружено %d точек", len(frame))
    return frame[[*UNIFIED_COLUMNS, *extra]]
