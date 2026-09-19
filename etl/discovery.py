"""Поиск исходных файлов данных.

Позволяет указывать как отдельные файлы, так и каталоги: каталоги
сканируются рекурсивно (вложенные папки также обходятся).

CSV: ``*.csv`` и сжатые ``*.csv.gz`` (GitHub-лимит 100 МБ).
Если рядом лежат и ``file.csv``, и ``file.csv.gz``, берётся несжатый CSV.

Дампы Prometheus/Zabbix: ``*.parquet`` и ``*.csv`` (не ``*.dump``).
Ошмётки histogram Prometheus (``*_bucket``, ``*_created``) при сканировании
каталога пропускаются — в ML-набор они не входят.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Union

from etl.logging_config import get_logger

logger = get_logger(__name__)

CSV_PATTERN = "*.csv"
CSV_GZ_PATTERN = "*.csv.gz"


def _logical_stem(path: Path) -> str:
    """Имя файла без ``.csv`` / ``.csv.gz`` (для дедупликации)."""

    name = path.name.lower()
    if name.endswith(".csv.gz"):
        return name[: -len(".csv.gz")]
    if name.endswith(".csv"):
        return name[: -len(".csv")]
    return name


def _is_tabular(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".csv") or name.endswith(".csv.gz")


def find_csv_files(path: Union[str, Path]) -> List[Path]:
    """Найти CSV-файлы по указанному пути.

    Args:
        path: Путь к CSV/CSV.GZ-файлу или каталогу. Каталог обходится рекурсивно.

    Returns:
        Отсортированный список путей к найденным файлам.

    Raises:
        FileNotFoundError: Если путь не существует.
    """

    target = Path(path)
    if target.is_file():
        return [target]
    if target.is_dir():
        candidates = [p for p in target.rglob("*") if p.is_file() and _is_tabular(p)]
        uncompressed = {_logical_stem(p) for p in candidates if p.name.lower().endswith(".csv")}
        files = sorted(
            p
            for p in candidates
            if not (
                p.name.lower().endswith(".csv.gz") and _logical_stem(p) in uncompressed
            )
        )
        logger.info("Найдено %d CSV-файлов в каталоге %s", len(files), target)
        return files
    raise FileNotFoundError(f"Путь не найден: {target}")


DUMP_SUFFIXES = {".parquet", ".csv"}
#: Суффиксы имён метрик Prometheus, которые не тащим в обучающую выборку.
_HISTOGRAM_REMNANT_SUFFIXES = ("_bucket", "_created")


def dump_metric_stem(path: Path) -> str:
    """Имя метрики из файла дампа: ``job__metric`` → ``metric``, иначе stem."""

    stem = path.stem
    if "__" in stem:
        return stem.split("__", 1)[1]
    return stem


def is_histogram_remnant(path: Path) -> bool:
    """True для ошмётков histogram/created, которые не входят в ML-набор."""

    metric = dump_metric_stem(path)
    return metric.endswith(_HISTOGRAM_REMNANT_SUFFIXES)


def _is_dump_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in DUMP_SUFFIXES


def find_dump_files(
    path: Union[str, Path],
    *,
    skip_histogram_remnants: bool = True,
) -> List[Path]:
    """Найти parquet/csv-дампы по пути (файл или каталог рекурсивно).

    Каталог обходится через ``rglob``, поэтому ``PROMETHEUS/live/**/*.parquet``
    находится вместе с файлами в корне источника. Файлы ``*.dump`` не
    подхватываются: pandas их не читает.

    Явно указанный файл принимается как есть (даже ``*_bucket``), чтобы
    не ломать точечную отладку. Фильтр ошмётков действует только на каталоги.

    Args:
        path: Файл дампа или каталог.
        skip_histogram_remnants: Пропускать ``*_bucket`` / ``*_created`` при
            сканировании каталога.

    Returns:
        Отсортированный список путей.

    Raises:
        FileNotFoundError: Если путь не существует.
    """

    target = Path(path)
    if target.is_file():
        return [target]
    if target.is_dir():
        files = [
            candidate
            for candidate in target.rglob("*")
            if _is_dump_file(candidate)
            and not (
                skip_histogram_remnants and is_histogram_remnant(candidate)
            )
        ]
        files.sort()
        logger.info("Найдено %d дампов (parquet/csv) в каталоге %s", len(files), target)
        return files
    raise FileNotFoundError(f"Путь не найден: {target}")


def collect_dump_files(
    paths: Iterable[Union[str, Path]],
    *,
    skip_histogram_remnants: bool = True,
) -> List[Path]:
    """Собрать уникальные parquet/csv-дампы из файлов и/или каталогов."""

    collected: List[Path] = []
    seen: set[Path] = set()
    for path in paths:
        for dump_file in find_dump_files(
            path, skip_histogram_remnants=skip_histogram_remnants
        ):
            resolved = dump_file.resolve()
            if resolved not in seen:
                seen.add(resolved)
                collected.append(dump_file)
    return collected


def collect_csv_files(paths: Iterable[Union[str, Path]]) -> List[Path]:
    """Собрать уникальные CSV-файлы из набора путей (файлов и/или каталогов).

    Args:
        paths: Набор путей к файлам и/или каталогам.

    Returns:
        Отсортированный список уникальных путей к CSV-файлам.
    """

    collected: List[Path] = []
    seen: set[Path] = set()
    for path in paths:
        for csv_file in find_csv_files(path):
            resolved = csv_file.resolve()
            if resolved not in seen:
                seen.add(resolved)
                collected.append(csv_file)
    return collected
