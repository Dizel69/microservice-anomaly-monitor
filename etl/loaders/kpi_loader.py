"""Загрузчик данных KPI Anomaly Detection.

Источник: https://github.com/NetManAIOps/KPI-Anomaly-Detection

Поддерживаются CSV-файлы из каталога ``Finals_dataset`` — как несжатые
(``phase2_train.csv``), так и сжатые (``phase2_train.csv.gz``,
``phase2_ground_truth.csv.gz``); формат сжатия определяется по расширению.
Типичные колонки:

* ``timestamp`` — UNIX-время (секунды);
* ``value`` — значение KPI;
* ``label`` — метка аномалии (0/1), поставленная разметчиками;
* ``KPI ID`` — идентификатор временного ряда (используется как ``service``).

Метки набора KPI — настоящая эталонная разметка, поэтому они переносятся
в единый формат как есть, без доразметки и без замены на «неизвестно».
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
    SOURCE_KPI,
    TIMESTAMP,
    UNIFIED_COLUMNS,
    VALUE,
)

logger = get_logger(__name__)

#: KPI описывает обобщённый показатель качества обслуживания.
KPI_METRIC_NAME = "kpi_value"

_TIMESTAMP_CANDIDATES: List[str] = ["timestamp", "time", "ts"]
_VALUE_CANDIDATES: List[str] = ["value", "val"]
_LABEL_CANDIDATES: List[str] = ["label", "is_anomaly", "anomaly"]
_SERVICE_CANDIDATES: List[str] = ["kpi id", "kpi_id", "kpiid", "service", "id"]


def _find_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    """Найти первую подходящую колонку без учёта регистра."""

    lowered = {col.lower(): col for col in columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def _compression_of(path: Path) -> str:
    """Определить способ сжатия CSV по имени файла (для ``pandas``)."""

    return "gzip" if path.name.lower().endswith(".csv.gz") else "infer"


def _to_datetime(series: pd.Series) -> pd.Series:
    """Преобразовать колонку времени KPI в datetime.

    В KPI timestamp обычно хранится как UNIX-секунды. Если значения числовые,
    интерпретируем их как секунды; иначе пробуем разобрать как строку даты.
    """

    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().mean() > 0.5:
        return pd.to_datetime(numeric, unit="s", errors="coerce")
    return pd.to_datetime(series, errors="coerce")


def load_kpi(
    csv_path: Union[str, Path],
    *,
    service: Optional[str] = None,
) -> pd.DataFrame:
    """Загрузить CSV-файл KPI и привести к единому формату.

    Args:
        csv_path: Путь к CSV-файлу из набора данных KPI (Finals_dataset),
            допускается ``.csv`` и ``.csv.gz``.
        service: Принудительное имя сервиса. Если ``None`` — берётся из
            колонки ``KPI ID``.

    Returns:
        DataFrame с колонками
        ``timestamp``, ``service``, ``metric_name``, ``value``, ``label``, ``source``.

    Raises:
        FileNotFoundError: Если файл не существует.
        ValueError: Если не удалось определить обязательные колонки либо
            файл не похож на набор KPI (нет ``KPI ID`` и не задан ``service``).
    """

    path = Path(csv_path)
    logger.info("KPI: загрузка файла %s", path)

    if not path.is_file():
        raise FileNotFoundError(f"Файл KPI не найден: {path}")

    try:
        raw = pd.read_csv(path, compression=_compression_of(path))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Не удалось прочитать CSV-файл KPI '{path}': {exc}") from exc

    if raw.empty:
        logger.warning("KPI: файл %s не содержит строк", path)

    columns = list(raw.columns)
    ts_col = _find_column(columns, _TIMESTAMP_CANDIDATES)
    val_col = _find_column(columns, _VALUE_CANDIDATES)

    if ts_col is None or val_col is None:
        raise ValueError(
            "KPI: не удалось определить колонки timestamp/value. "
            f"Доступные колонки: {columns}"
        )

    label_col = _find_column(columns, _LABEL_CANDIDATES)
    service_col = _find_column(columns, _SERVICE_CANDIDATES)

    if service is None and service_col is None:
        raise ValueError(
            f"KPI: в файле '{path}' нет колонки идентификатора ряда "
            f"('KPI ID'). Доступные колонки: {columns}. Если это действительно "
            "набор KPI, укажите имя сервиса явно (service=...); файлы других "
            "наборов (например, NAB) следует грузить своим загрузчиком."
        )

    frame = pd.DataFrame()
    frame[TIMESTAMP] = _to_datetime(raw[ts_col])

    if service is not None:
        frame[SERVICE] = service
    else:
        logger.info("KPI: имя сервиса берётся из колонки '%s'", service_col)
        frame[SERVICE] = raw[service_col].astype(str)

    frame[METRIC_NAME] = KPI_METRIC_NAME
    frame[VALUE] = raw[val_col]

    if label_col is not None:
        logger.info("KPI: обнаружена колонка меток '%s'", label_col)
        frame[LABEL] = raw[label_col]
    else:
        logger.info("KPI: колонка меток отсутствует, label = %s", LABEL_NORMAL)
        frame[LABEL] = LABEL_NORMAL

    frame[SOURCE] = SOURCE_KPI

    logger.info(
        "KPI: загружено %d строк, %d рядов, аномалий %d",
        len(frame),
        frame[SERVICE].nunique(),
        int(pd.to_numeric(frame[LABEL], errors="coerce").eq(1).sum()),
    )
    return frame[UNIFIED_COLUMNS]
