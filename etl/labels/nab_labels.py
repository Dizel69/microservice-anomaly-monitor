"""Официальные метки аномалий NAB (Numenta Anomaly Benchmark).

В CSV-файлах NAB меток нет: они хранятся отдельно в
``labels/combined_windows.json`` — по одному списку окон
``[начало, конец]`` на каждый временной ряд::

    {
      "realKnownCause/nyc_taxi.csv": [
        ["2014-10-30 15:30:00.000000", "2014-11-03 22:30:00.000000"],
        ...
      ],
      "artificialNoAnomaly/art_daily_no_noise.csv": []
    }

Точка считается аномальной (``label = 1``), если её ``timestamp`` попадает
в любое из окон (границы включительно), иначе — нормальной (``label = 0``).
Ряды с пустым списком окон (категория ``artificialNoAnomaly``) полностью
размечаются нулями — это тоже настоящая разметка, а не «нет данных».

Ключи в JSON содержат официальное имя категории
(``realAWSCloudwatch/...``), тогда как локальные каталоги могут называться
короче (``AWSCloudwatch/...``), поэтому индекс дополнительно строится по
имени файла.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from etl.logging_config import get_logger
from etl.schema import LABEL_ANOMALY, LABEL_NORMAL

logger = get_logger(__name__)

#: Имя каталога с файлами меток внутри каталога набора данных NAB.
LABELS_DIRNAME: str = "labels"

#: Окна аномалий — основной источник разметки.
COMBINED_WINDOWS_FILE: str = "combined_windows.json"

#: Точечные метки — используются справочно (в разметке не участвуют).
COMBINED_LABELS_FILE: str = "combined_labels.json"

#: Временное окно аномалии (начало, конец).
Window = Tuple[pd.Timestamp, pd.Timestamp]


@dataclass(frozen=True)
class NabWindowIndex:
    """Индекс окон аномалий NAB с поиском по ключу или имени файла."""

    #: Окна по официальному ключу ``<category>/<file>.csv``.
    by_key: Dict[str, List[Window]] = field(default_factory=dict)
    #: Окна по имени файла без расширения (в нижнем регистре).
    by_stem: Dict[str, List[Window]] = field(default_factory=dict)
    #: Путь к файлу, из которого загружен индекс.
    source_path: Optional[Path] = None

    def __len__(self) -> int:
        return len(self.by_key)

    @property
    def series_with_anomalies(self) -> int:
        """Сколько рядов имеет хотя бы одно окно аномалии."""

        return sum(1 for windows in self.by_key.values() if windows)

    def lookup(self, csv_path: Union[str, Path]) -> Optional[List[Window]]:
        """Найти окна для CSV-файла ряда NAB.

        Сначала проверяется официальный ключ ``<category>/<file>.csv``
        (по последним двум элементам пути), затем — имя файла.

        Args:
            csv_path: Путь к CSV-файлу временного ряда.

        Returns:
            Список окон (возможно пустой) либо ``None``, если ряд не
            представлен в файле меток.
        """

        path = Path(csv_path)
        key = f"{path.parent.name}/{path.name}"
        if key in self.by_key:
            return self.by_key[key]

        stem = path.name.lower()
        if stem.endswith(".csv"):
            stem = stem[: -len(".csv")]
        return self.by_stem.get(stem)


def find_nab_labels_dir(start: Union[str, Path]) -> Optional[Path]:
    """Найти каталог ``labels`` набора NAB, поднимаясь вверх от пути.

    Args:
        start: Путь к CSV-файлу ряда или к каталогу внутри набора NAB.

    Returns:
        Путь к каталогу с ``combined_windows.json`` либо ``None``.
    """

    current = Path(start).resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        candidate = directory / LABELS_DIRNAME / COMBINED_WINDOWS_FILE
        if candidate.is_file():
            return candidate.parent
        # Каталог меток может быть указан напрямую.
        if (directory / COMBINED_WINDOWS_FILE).is_file():
            return directory
    return None


def _parse_windows(raw_windows: object, key: str) -> List[Window]:
    """Разобрать список окон одного ряда в пары ``pd.Timestamp``."""

    if not isinstance(raw_windows, list):
        logger.warning("NAB labels: некорректное значение для ключа '%s'", key)
        return []

    windows: List[Window] = []
    for item in raw_windows:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            logger.warning("NAB labels: пропущено окно %r в ключе '%s'", item, key)
            continue
        start = pd.to_datetime(item[0], errors="coerce")
        end = pd.to_datetime(item[1], errors="coerce")
        if pd.isna(start) or pd.isna(end):
            logger.warning("NAB labels: непарсируемое окно %r в ключе '%s'", item, key)
            continue
        if start > end:
            start, end = end, start
        windows.append((start, end))
    return windows


def load_nab_windows(
    labels_source: Union[str, Path],
) -> NabWindowIndex:
    """Загрузить окна аномалий NAB из ``combined_windows.json``.

    Args:
        labels_source: Путь к JSON-файлу окон либо к каталогу, где он лежит.

    Returns:
        :class:`NabWindowIndex` с окнами по ключам и по именам файлов.

    Raises:
        FileNotFoundError: Если файл окон не найден.
        ValueError: Если файл содержит некорректный JSON.
    """

    source = Path(labels_source)
    if source.is_dir():
        source = source / COMBINED_WINDOWS_FILE
    if not source.is_file():
        raise FileNotFoundError(f"Файл окон NAB не найден: {source}")

    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Некорректный JSON окон NAB '{source}': {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Ожидался объект JSON в '{source}'")

    by_key: Dict[str, List[Window]] = {}
    by_stem: Dict[str, List[Window]] = {}
    for key, raw_windows in payload.items():
        windows = _parse_windows(raw_windows, key)
        by_key[key] = windows

        stem = key.split("/")[-1].lower()
        if stem.endswith(".csv"):
            stem = stem[: -len(".csv")]
        if stem in by_stem:
            logger.warning(
                "NAB labels: имя ряда '%s' встречается в нескольких категориях", stem
            )
        by_stem[stem] = windows

    index = NabWindowIndex(by_key=by_key, by_stem=by_stem, source_path=source)
    logger.info(
        "NAB labels: загружено %d рядов из %s (%d с окнами аномалий)",
        len(index),
        source,
        index.series_with_anomalies,
    )
    return index


def label_series_by_windows(
    timestamps: pd.Series,
    windows: List[Window],
) -> pd.Series:
    """Разметить точки ряда по окнам аномалий.

    Args:
        timestamps: Колонка времени (будет приведена к ``datetime``).
        windows: Список окон ``(начало, конец)``, границы включительно.

    Returns:
        Целочисленная серия меток: ``1`` внутри окна, ``0`` вне окон.
    """

    times = pd.to_datetime(timestamps, errors="coerce")
    labels = np.full(len(times), LABEL_NORMAL, dtype="int64")

    for start, end in windows:
        inside = (times >= start) & (times <= end)
        labels[inside.to_numpy(dtype=bool, na_value=False)] = LABEL_ANOMALY

    return pd.Series(labels, index=timestamps.index, dtype="int64")
