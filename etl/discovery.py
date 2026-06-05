"""Поиск CSV-файлов исходных данных.

Позволяет указывать как отдельные файлы, так и каталоги: каталоги
сканируются рекурсивно (вложенные папки также обходятся).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Union

from etl.logging_config import get_logger

logger = get_logger(__name__)

CSV_PATTERN = "*.csv"


def find_csv_files(path: Union[str, Path]) -> List[Path]:
    """Найти CSV-файлы по указанному пути.

    Args:
        path: Путь к CSV-файлу или каталогу. Каталог обходится рекурсивно.

    Returns:
        Отсортированный список путей к найденным CSV-файлам.

    Raises:
        FileNotFoundError: Если путь не существует.
    """

    target = Path(path)
    if target.is_file():
        return [target]
    if target.is_dir():
        files = sorted(p for p in target.rglob(CSV_PATTERN) if p.is_file())
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
