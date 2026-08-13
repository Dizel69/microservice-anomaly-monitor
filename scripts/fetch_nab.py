"""Догрузка эталонного набора NAB (данные + официальные метки).

Скачивает из репозитория https://github.com/numenta/NAB:

* ``labels/combined_windows.json`` — окна аномалий (основной источник меток);
* ``labels/combined_labels.json``  — точечные метки (справочно);
* недостающие ``data/<category>/<file>.csv`` — до официальных 58 рядов.

Список рядов берётся из ключей ``combined_windows.json``, поэтому состав
всегда соответствует версии NAB, с которой скачаны метки. Уже имеющиеся
локально файлы (в том числе лежащие в каталогах с укороченными именами
категорий, например ``AWSCloudwatch`` вместо ``realAWSCloudwatch``)
повторно не скачиваются.

Запуск::

    python scripts/fetch_nab.py
    python scripts/fetch_nab.py --labels-only
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.config import RAW_NAB_DIR  # noqa: E402
from etl.labels.nab_labels import (  # noqa: E402
    COMBINED_LABELS_FILE,
    COMBINED_WINDOWS_FILE,
    LABELS_DIRNAME,
)
from etl.logging_config import configure_logging, get_logger  # noqa: E402

logger = get_logger("etl.scripts.fetch_nab")

NAB_RAW_BASE = "https://raw.githubusercontent.com/numenta/NAB/master"
HTTP_TIMEOUT = 60


def _download(url: str, destination: Path) -> int:
    """Скачать файл по URL в указанный путь. Возвращает размер в байтах."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Скачивание %s", url)
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as response:
            payload = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Не удалось скачать {url}: {exc}") from exc

    destination.write_bytes(payload)
    return len(payload)


def fetch_labels(nab_dir: Path = RAW_NAB_DIR) -> Dict[str, Path]:
    """Скачать файлы меток NAB в ``<nab_dir>/labels/``."""

    labels_dir = nab_dir / LABELS_DIRNAME
    saved: Dict[str, Path] = {}
    for name in (COMBINED_WINDOWS_FILE, COMBINED_LABELS_FILE):
        target = labels_dir / name
        try:
            size = _download(f"{NAB_RAW_BASE}/labels/{name}", target)
        except RuntimeError as exc:
            # combined_labels.json носит справочный характер: его отсутствие
            # не должно ломать разметку по окнам.
            if name == COMBINED_LABELS_FILE:
                logger.warning("Пропущен необязательный файл меток: %s", exc)
                continue
            raise
        logger.info("Сохранено %s (%d байт)", target, size)
        saved[name] = target
    return saved


def _existing_basenames(nab_dir: Path) -> Dict[str, Path]:
    """Карта «имя файла -> путь» для уже имеющихся локально CSV-рядов NAB."""

    return {p.name: p for p in nab_dir.rglob("*.csv") if p.is_file()}


def fetch_missing_series(nab_dir: Path = RAW_NAB_DIR) -> List[Path]:
    """Догрузить недостающие CSV-ряды NAB до полного официального состава."""

    windows_path = nab_dir / LABELS_DIRNAME / COMBINED_WINDOWS_FILE
    if not windows_path.is_file():
        raise FileNotFoundError(
            f"Сначала скачайте метки: файл не найден {windows_path}"
        )

    keys: List[str] = sorted(json.loads(windows_path.read_text(encoding="utf-8")))
    existing = _existing_basenames(nab_dir)
    downloaded: List[Path] = []

    for key in keys:
        basename = key.split("/")[-1]
        if basename in existing:
            continue
        target = nab_dir / key
        size = _download(f"{NAB_RAW_BASE}/data/{key}", target)
        logger.info("Сохранено %s (%d байт)", target, size)
        downloaded.append(target)

    total = len(_existing_basenames(nab_dir))
    logger.info(
        "NAB: рядов локально %d из %d официальных (скачано сейчас %d)",
        total,
        len(keys),
        len(downloaded),
    )
    return downloaded


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fetch_nab.py",
        description="Скачать официальные метки NAB и недостающие ряды данных.",
    )
    parser.add_argument(
        "--labels-only",
        action="store_true",
        help="Скачать только файлы меток, без CSV-рядов.",
    )
    args = parser.parse_args(argv)

    configure_logging()
    try:
        fetch_labels()
        if not args.labels_only:
            fetch_missing_series()
    except (RuntimeError, FileNotFoundError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
