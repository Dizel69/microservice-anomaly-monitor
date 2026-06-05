"""ETL-конвейер подготовки данных для обучения моделей обнаружения аномалий.

Пакет объединяет загрузчики разнородных источников метрик (NAB, KPI,
Prometheus), трансформеры очистки/нормализации, модуль инженерии признаков
и визуализацию. Все источники приводятся к единому формату:

    timestamp | service | metric_name | value | label | source
"""

from __future__ import annotations

__all__ = [
    "UNIFIED_COLUMNS",
    "TIMESTAMP",
    "SERVICE",
    "METRIC_NAME",
    "VALUE",
    "LABEL",
    "SOURCE",
    "infer_metric_name",
]

from etl.schema import (
    LABEL,
    METRIC_NAME,
    SERVICE,
    SOURCE,
    TIMESTAMP,
    UNIFIED_COLUMNS,
    VALUE,
    infer_metric_name,
)
