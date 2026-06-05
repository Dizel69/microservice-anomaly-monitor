"""Единая схема данных ETL-конвейера.

Все источники приводятся к единому формату из шести колонок:

* ``timestamp``    — время измерения;
* ``service``      — имя сервиса (микросервиса / временного ряда);
* ``metric_name``  — тип метрики (``cpu_usage``, ``memory_usage`` и т. д.);
* ``value``        — числовое значение метрики;
* ``label``        — метка аномалии (0 — норма, 1 — аномалия, -1 — неизвестно);
* ``source``       — источник данных (``NAB``, ``KPI``, ``PROMETHEUS``).

Дополнительно у источников (например, Prometheus) может присутствовать
служебная колонка :data:`LABELS` с исходными метками в формате JSON —
она сохраняется на уровне RAW и не входит в финальный унифицированный набор.
"""

from __future__ import annotations

from typing import Final, List

TIMESTAMP: Final[str] = "timestamp"
SERVICE: Final[str] = "service"
METRIC_NAME: Final[str] = "metric_name"
VALUE: Final[str] = "value"
LABEL: Final[str] = "label"
SOURCE: Final[str] = "source"

#: Служебная колонка с исходными метками Prometheus (JSON), только для RAW.
LABELS: Final[str] = "labels"

#: Порядок колонок единого набора данных.
UNIFIED_COLUMNS: Final[List[str]] = [
    TIMESTAMP,
    SERVICE,
    METRIC_NAME,
    VALUE,
    LABEL,
    SOURCE,
]

# Допустимые значения меток аномалий.
LABEL_NORMAL: Final[int] = 0
LABEL_ANOMALY: Final[int] = 1
LABEL_UNKNOWN: Final[int] = -1

# Источники данных.
SOURCE_NAB: Final[str] = "NAB"
SOURCE_KPI: Final[str] = "KPI"
SOURCE_PROMETHEUS: Final[str] = "PROMETHEUS"

# Канонические имена метрик микросервисов.
METRIC_CPU: Final[str] = "cpu_usage"
METRIC_MEMORY: Final[str] = "memory_usage"
METRIC_DISK: Final[str] = "disk_usage"
METRIC_LATENCY: Final[str] = "http_latency"
METRIC_REQUEST_RATE: Final[str] = "request_rate"
METRIC_ERROR_RATE: Final[str] = "error_rate"
METRIC_UNKNOWN: Final[str] = "unknown_metric"

#: Ключевые слова -> каноническое имя метрики (для эвристического разбора
#: имён файлов NAB и метрик Prometheus).
METRIC_KEYWORDS: Final[List[tuple[tuple[str, ...], str]]] = [
    (("cpu", "processor", "cpu_usage", "cpu_utilization"), METRIC_CPU),
    (("mem", "memory", "ram", "memory_usage"), METRIC_MEMORY),
    (("disk", "fs", "filesystem", "storage"), METRIC_DISK),
    (("latency", "response_time", "duration", "rt"), METRIC_LATENCY),
    (("request", "rps", "throughput", "req_rate", "traffic"), METRIC_REQUEST_RATE),
    (("error", "err", "failure", "5xx"), METRIC_ERROR_RATE),
]


def infer_metric_name(text: str) -> str:
    """Эвристически определить каноническое имя метрики по строке.

    Args:
        text: Произвольная строка (имя файла, метрики, путь).

    Returns:
        Каноническое имя метрики либо :data:`METRIC_UNKNOWN`.
    """

    if not text:
        return METRIC_UNKNOWN

    lowered = text.lower()
    for keywords, canonical in METRIC_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return canonical
    return METRIC_UNKNOWN
