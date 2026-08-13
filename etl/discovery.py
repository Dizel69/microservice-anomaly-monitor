"""Поиск CSV-файлов исходных данных.

Позволяет указывать как отдельные файлы, так и каталоги: каталоги
сканируются рекурсивно (вложенные папки также обходятся).

Поддерживаются ``*.csv`` и сжатые ``*.csv.gz`` (GitHub-лимит 100 МБ).
Если рядом лежат и ``file.csv``, и ``file.csv.gz``, берётся несжатый CSV.
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
