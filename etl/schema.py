"""Единая схема данных ETL-конвейера.

Все источники приводятся к единому формату из шести колонок:

* ``timestamp``    — время измерения;
* ``service``      — имя сервиса (микросервиса / временного ряда);
* ``metric_name``  — тип метрики (``cpu_usage``, ``memory_usage`` и т. д.);
* ``value``        — числовое значение метрики;
* ``label``        — метка аномалии (0 — норма, 1 — аномалия, -1 — неизвестно);
* ``source``       — источник данных (``NAB``, ``KPI``, ``PROMETHEUS``, ``ZABBIX``).

Дополнительно у источников (например, Prometheus) может присутствовать
служебная колонка :data:`LABELS` с исходными метками в формате JSON —
она сохраняется на уровне RAW и не входит в финальный унифицированный набор.
"""

from __future__ import annotations

import re
from typing import Final, List, Tuple

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
SOURCE_ZABBIX: Final[str] = "ZABBIX"

# Канонические имена метрик микросервисов и инфраструктуры.
METRIC_CPU: Final[str] = "cpu_usage"
METRIC_MEMORY: Final[str] = "memory_usage"
METRIC_DISK: Final[str] = "disk_usage"
METRIC_NETWORK: Final[str] = "network_traffic"
METRIC_LATENCY: Final[str] = "http_latency"
METRIC_REQUEST_RATE: Final[str] = "request_rate"
METRIC_ERROR_RATE: Final[str] = "error_rate"
METRIC_UNKNOWN: Final[str] = "unknown_metric"

# Канонические имена метрик прикладных рядов NAB.
METRIC_TEMPERATURE: Final[str] = "temperature"
METRIC_TWEET_VOLUME: Final[str] = "tweet_volume"
METRIC_TAXI_DEMAND: Final[str] = "taxi_demand"
METRIC_ROAD_OCCUPANCY: Final[str] = "road_occupancy"
METRIC_VEHICLE_SPEED: Final[str] = "vehicle_speed"
METRIC_TRAVEL_TIME: Final[str] = "travel_time"
METRIC_AD_COST_PER_CLICK: Final[str] = "ad_cost_per_click"
METRIC_AD_COST_PER_MILLE: Final[str] = "ad_cost_per_mille"
METRIC_KEYSTROKE_TIMING: Final[str] = "keystroke_timing"

#: Ключевые слова -> каноническое имя метрики (для эвристического разбора
#: имён файлов NAB и метрик Prometheus).
#:
#: Правила проверяются по порядку: сначала узкоспециальные (температура,
#: твиты, реклама), затем общие инфраструктурные. Ключ сопоставляется с
#: **токенами** имени, а не подстрокой, иначе короткие ключи дают ложные
#: срабатывания (например, ``rt`` внутри ``art_daily_flatmiddle``).
#: Ключ с ``_`` сопоставляется с последовательностью соседних токенов.
METRIC_KEYWORDS: Final[List[Tuple[Tuple[str, ...], str]]] = [
    (("temperature", "temp"), METRIC_TEMPERATURE),
    (("travel_time",), METRIC_TRAVEL_TIME),
    (("twitter", "tweet", "tweets"), METRIC_TWEET_VOLUME),
    (("taxi",), METRIC_TAXI_DEMAND),
    (("occupancy",), METRIC_ROAD_OCCUPANCY),
    (("speed",), METRIC_VEHICLE_SPEED),
    (("cpc",), METRIC_AD_COST_PER_CLICK),
    (("cpm",), METRIC_AD_COST_PER_MILLE),
    (("key_hold", "key_updown"), METRIC_KEYSTROKE_TIMING),
    (("cpu", "processor", "cpu_usage", "cpu_utilization"), METRIC_CPU),
    (("mem", "memory", "ram", "memory_usage"), METRIC_MEMORY),
    (("disk", "fs", "filesystem", "storage"), METRIC_DISK),
    (("network", "network_in", "network_out", "bytes_in"), METRIC_NETWORK),
    (("latency", "response_time", "duration", "rt"), METRIC_LATENCY),
    (("request", "requests", "rps", "throughput", "req_rate", "traffic"),
     METRIC_REQUEST_RATE),
    (("error", "err", "failure", "5xx"), METRIC_ERROR_RATE),
]

#: Границы слов: разделители и переход camelCase -> camel Case
#: (``NetworkIn`` -> ``network``/``in``, ``MemAvailable`` -> ``mem``/``available``).
_NON_ALNUM_RE: Final[re.Pattern[str]] = re.compile(r"[^0-9A-Za-z]+")
_CAMEL_RE: Final[re.Pattern[str]] = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def tokenize_metric_text(text: str) -> List[str]:
    """Разбить строку на токены для сопоставления с ключевыми словами.

    Args:
        text: Имя файла, метрики или путь (``ec2_NetworkIn_5abac7``).

    Returns:
        Список токенов в нижнем регистре (``['ec2', 'network', 'in', '5abac7']``).
    """

    if not text:
        return []
    spaced = _CAMEL_RE.sub(" ", text)
    return [token.lower() for token in _NON_ALNUM_RE.split(spaced) if token]


def _matches(tokens: List[str], keyword: str) -> bool:
    """Проверить, встречается ли ключевое слово среди токенов.

    Односложный ключ сравнивается с токеном целиком; ключ вида ``travel_time``
    — с последовательностью соседних токенов.
    """

    parts = keyword.split("_")
    if len(parts) == 1:
        return keyword in tokens
    window = len(parts)
    return any(
        tokens[i : i + window] == parts for i in range(len(tokens) - window + 1)
    )


def infer_metric_name(text: str) -> str:
    """Эвристически определить каноническое имя метрики по строке.

    Args:
        text: Произвольная строка (имя файла, метрики, путь).

    Returns:
        Каноническое имя метрики либо :data:`METRIC_UNKNOWN`.
    """

    tokens = tokenize_metric_text(text)
    if not tokens:
        return METRIC_UNKNOWN

    for keywords, canonical in METRIC_KEYWORDS:
        if any(_matches(tokens, keyword) for keyword in keywords):
            return canonical
    return METRIC_UNKNOWN
