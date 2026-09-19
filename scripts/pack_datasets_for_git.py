"""Упаковать живые дампы Prometheus/Zabbix для GitHub (< 90 МБ на файл).

Распакованные parquet остаются в ``datasets/raw/.../live/`` для обучения.
В git идут только ``datasets/archives/*.tar.gz`` или ``*.tar.gz.partNN``.

    python scripts/pack_datasets_for_git.py
    python scripts/pack_datasets_for_git.py --unpack
"""

from __future__ import annotations

import argparse
import tarfile
import tempfile
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVES = PROJECT_ROOT / "datasets" / "archives"
MAX_PART = 90 * 1024 * 1024

SOURCES = {
    "prometheus_live": PROJECT_ROOT / "datasets" / "raw" / "PROMETHEUS" / "live",
    "zabbix_live": PROJECT_ROOT / "datasets" / "raw" / "ZABBIX" / "live",
}


def _has_payload(directory: Path) -> bool:
    """Есть ли в каталоге что упаковывать кроме .gitkeep."""

    if not directory.is_dir():
        return False
    return any(p.is_file() and p.name != ".gitkeep" for p in directory.iterdir())


def _split(src: Path, dest_stem: Path) -> List[Path]:
    """Разрезать файл на части dest_stem.part01, ..."""

    parts: List[Path] = []
    with src.open("rb") as fh:
        index = 1
        while True:
            chunk = fh.read(MAX_PART)
            if not chunk:
                break
            part = dest_stem.parent / f"{dest_stem.name}.part{index:02d}"
            part.write_bytes(chunk)
            parts.append(part)
            index += 1
    return parts


def pack_one(name: str, src: Path) -> List[Path]:
    """Собрать tar.gz каталога; при необходимости разрезать."""

    ARCHIVES.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / f"{name}.tar.gz"
        with tarfile.open(raw, "w:gz") as tar:
            tar.add(src, arcname=name)
        size = raw.stat().st_size
        print(f"{name}: {size / (1024 * 1024):.1f} МБ до нарезки")
        if size <= MAX_PART:
            dest = ARCHIVES / f"{name}.tar.gz"
            dest.write_bytes(raw.read_bytes())
            for stale in ARCHIVES.glob(f"{name}.tar.gz.part*"):
                stale.unlink()
            print(f"  → {dest.relative_to(PROJECT_ROOT)}")
            return [dest]
        parts = _split(raw, ARCHIVES / f"{name}.tar.gz")
        single = ARCHIVES / f"{name}.tar.gz"
        if single.exists():
            single.unlink()
        for part in parts:
            print(f"  → {part.relative_to(PROJECT_ROOT)} ({part.stat().st_size / (1024 * 1024):.1f} МБ)")
        return parts


def unpack_one(name: str, dest: Path) -> None:
    """Склеить части при необходимости и распаковать в dest.parent."""

    single = ARCHIVES / f"{name}.tar.gz"
    parts = sorted(ARCHIVES.glob(f"{name}.tar.gz.part*"))
    if not single.exists() and not parts:
        print(f"{name}: архива нет, пропуск")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        blob = Path(tmp) / f"{name}.tar.gz"
        if parts:
            with blob.open("wb") as out:
                for part in parts:
                    out.write(part.read_bytes())
        else:
            blob.write_bytes(single.read_bytes())
        with tarfile.open(blob, "r:gz") as tar:
            tar.extractall(dest.parent)
    print(f"{name}: распаковано в {dest}")


def main() -> int:
    """Точка входа pack/unpack."""

    parser = argparse.ArgumentParser(description="Архивы live-дампов для GitHub")
    parser.add_argument("--unpack", action="store_true", help="Распаковать archives/ в live/")
    args = parser.parse_args()
    if args.unpack:
        for name, dest in SOURCES.items():
            unpack_one(name, dest)
        return 0
    written: List[Path] = []
    for name, src in SOURCES.items():
        if not _has_payload(src):
            print(f"{name}: пусто ({src})")
            continue
        written.extend(pack_one(name, src))
    if not written:
        print("Нечего упаковывать.")
        return 1
    print("Готово. Коммить datasets/archives/, не datasets/raw/*/live/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
