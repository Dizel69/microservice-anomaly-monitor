"""Загрузчик данных из Prometheus через HTTP API.

Источник: Prometheus HTTP API
(https://prometheus.io/docs/prometheus/latest/querying/api/).

Загрузчик сохраняет максимум контекста о каждой серии:

* ``service``     — выводится из меток ``job`` / ``service`` / ``container`` /
  ``pod`` / ``instance``;
* ``metric_name`` — каноническое имя метрики, выведенное из ``__name__``
  (с резервным сохранением исходного имени);
* ``labels``      — полный набор меток Prometheus в формате JSON (уровень RAW),
  чтобы не терять информацию о типе метрики.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from etl.logging_config import get_logger
from etl.schema import (
    LABEL,
    LABELS,
    LABEL_UNKNOWN,
    METRIC_NAME,
    METRIC_UNKNOWN,
    SERVICE,
    SOURCE,
    SOURCE_PROMETHEUS,
    TIMESTAMP,
    UNIFIED_COLUMNS,
    VALUE,
    infer_metric_name,
)

logger = get_logger(__name__)

DEFAULT_RANGE_SECONDS = 3600  # 1 час истории по умолчанию
DEFAULT_STEP_SECONDS = 15
DEFAULT_TIMEOUT = 30

#: Колонки, возвращаемые загрузчиком Prometheus (единый формат + RAW-метки).
PROMETHEUS_COLUMNS: List[str] = [*UNIFIED_COLUMNS, LABELS]

#: Приоритет меток Prometheus для определения имени сервиса.
_SERVICE_LABEL_PRIORITY = (
    "service",
    "job",
    "container",
    "container_name",
    "pod",
    "deployment",
    "app",
    "instance",
)


class PrometheusError(RuntimeError):
    """Ошибка взаимодействия с Prometheus HTTP API."""


def _build_base_url(prometheus_url: str) -> str:
    """Нормализовать базовый URL Prometheus (убрать завершающий слэш)."""

    return prometheus_url.rstrip("/")


def _request(url: str, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """Выполнить GET-запрос к Prometheus и разобрать JSON-ответ."""

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise PrometheusError(f"Сетевая ошибка при запросе к {url}: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise PrometheusError(f"Некорректный JSON в ответе от {url}: {exc}") from exc

    if payload.get("status") != "success":
        raise PrometheusError(
            f"Prometheus вернул ошибку: {payload.get('error', 'неизвестная ошибка')}"
        )

    return payload.get("data", {})


def _resolve_service(metric_labels: Dict[str, str]) -> str:
    """Определить имя сервиса по набору меток Prometheus."""

    for label in _SERVICE_LABEL_PRIORITY:
        if metric_labels.get(label):
            return str(metric_labels[label])
    return "prometheus"


def _resolve_metric_name(metric_labels: Dict[str, str]) -> str:
    """Определить каноническое имя метрики, не теряя исходное ``__name__``."""

    raw_name = metric_labels.get("__name__", "")
    canonical = infer_metric_name(raw_name)
    if canonical != METRIC_UNKNOWN:
        return canonical
    return raw_name or METRIC_UNKNOWN


def _series_to_records(
    series: Dict[str, Any],
    points: List[List[Any]],
) -> List[Dict[str, Any]]:
    """Преобразовать одну серию Prometheus в список записей единого формата."""

    metric_labels: Dict[str, str] = series.get("metric", {})
    service = _resolve_service(metric_labels)
    metric_name = _resolve_metric_name(metric_labels)
    labels_json = json.dumps(metric_labels, ensure_ascii=False, sort_keys=True)

    records: List[Dict[str, Any]] = []
    for ts, raw_value in points:
        records.append(
            {
                TIMESTAMP: float(ts),
                SERVICE: service,
                METRIC_NAME: metric_name,
                VALUE: raw_value,
                LABEL: LABEL_UNKNOWN,
                SOURCE: SOURCE_PROMETHEUS,
                LABELS: labels_json,
            }
        )
    return records


def _matrix_to_records(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Преобразовать результат типа ``matrix`` (query_range) в записи."""

    records: List[Dict[str, Any]] = []
    for series in result:
        records.extend(_series_to_records(series, series.get("values", [])))
    return records


def _vector_to_records(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Преобразовать результат типа ``vector`` (query) в записи."""

    records: List[Dict[str, Any]] = []
    for series in result:
        value = series.get("value")
        if not value:
            continue
        records.extend(_series_to_records(series, [value]))
    return records


def load_prometheus(
    prometheus_url: str,
    promql_query: str,
    *,
    start: Optional[float] = None,
    end: Optional[float] = None,
    step_seconds: int = DEFAULT_STEP_SECONDS,
    range_seconds: int = DEFAULT_RANGE_SECONDS,
    timeout: int = DEFAULT_TIMEOUT,
) -> pd.DataFrame:
    """Выгрузить временные ряды из Prometheus и привести к единому формату.

    Args:
        prometheus_url: Базовый URL сервера Prometheus
            (например, ``http://185.28.85.183:9090``).
        promql_query: PromQL-выражение
            (например, ``container_cpu_usage_seconds_total``).
        start: Начало диапазона (UNIX-секунды). По умолчанию ``end - range_seconds``.
        end: Конец диапазона (UNIX-секунды). По умолчанию — текущее время.
        step_seconds: Шаг дискретизации для ``query_range`` в секундах.
        range_seconds: Длина диапазона по умолчанию (если ``start`` не задан).
        timeout: Таймаут HTTP-запроса в секундах.

    Returns:
        DataFrame с колонками единого формата плюс служебной колонкой
        ``labels`` (исходные метки Prometheus в JSON).

    Raises:
        PrometheusError: При сетевых ошибках или ошибках API.
        ValueError: Если переданы пустые аргументы.
    """

    if not prometheus_url:
        raise ValueError("Не задан URL Prometheus")
    if not promql_query:
        raise ValueError("Не задан PromQL-запрос")

    base_url = _build_base_url(prometheus_url)
    end_ts = float(end) if end is not None else time.time()
    start_ts = float(start) if start is not None else end_ts - range_seconds

    logger.info(
        "PROMETHEUS: запрос '%s' к %s (диапазон %.0f..%.0f, шаг %ds)",
        promql_query,
        base_url,
        start_ts,
        end_ts,
        step_seconds,
    )

    range_url = f"{base_url}/api/v1/query_range"
    range_params: Dict[str, Any] = {
        "query": promql_query,
        "start": start_ts,
        "end": end_ts,
        "step": step_seconds,
    }

    data = _request(range_url, range_params, timeout)
    result_type = data.get("resultType")
    result = data.get("result", [])

    if result_type == "matrix" and result:
        records = _matrix_to_records(result)
    else:
        logger.info("PROMETHEUS: пустой/неподходящий matrix, пробуем мгновенный query")
        instant_url = f"{base_url}/api/v1/query"
        instant_data = _request(instant_url, {"query": promql_query}, timeout)
        records = _vector_to_records(instant_data.get("result", []))

    if not records:
        logger.warning("PROMETHEUS: запрос не вернул данных")
        return pd.DataFrame(columns=PROMETHEUS_COLUMNS)

    frame = pd.DataFrame.from_records(records)
    frame[TIMESTAMP] = pd.to_datetime(frame[TIMESTAMP], unit="s", errors="coerce")

    series_count = frame[SERVICE].nunique()
    logger.info(
        "PROMETHEUS: получено %d точек, %d серий", len(frame), series_count
    )
    return frame[PROMETHEUS_COLUMNS]
