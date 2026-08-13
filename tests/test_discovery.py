"""Поиск исходных файлов: сжатые .csv.gz должны находиться наравне с .csv."""

from __future__ import annotations

from pathlib import Path

import pytest

from etl.discovery import collect_csv_files, find_csv_files


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("timestamp,value\n", encoding="utf-8")
    return path


def test_finds_csv_gz_in_directory(tmp_path: Path) -> None:
    """Сжатый CSV находится при сканировании каталога."""

    _touch(tmp_path / "phase2_train.csv.gz")

    found = find_csv_files(tmp_path)

    assert [p.name for p in found] == ["phase2_train.csv.gz"]


def test_prefers_uncompressed_when_both_present(tmp_path: Path) -> None:
    """Если рядом лежат .csv и .csv.gz одного набора, берётся несжатый."""

    _touch(tmp_path / "phase2_train.csv")
    _touch(tmp_path / "phase2_train.csv.gz")

    found = find_csv_files(tmp_path)

    assert [p.name for p in found] == ["phase2_train.csv"]


def test_keeps_gz_without_uncompressed_twin(tmp_path: Path) -> None:
    """Файл .csv.gz без несжатой пары не отбрасывается."""

    _touch(tmp_path / "phase2_train.csv")
    _touch(tmp_path / "phase2_ground_truth.csv.gz")

    names = sorted(p.name for p in find_csv_files(tmp_path))

    assert names == ["phase2_ground_truth.csv.gz", "phase2_train.csv"]


def test_scans_nested_directories(tmp_path: Path) -> None:
    """Каталоги обходятся рекурсивно (категории NAB лежат во вложенных папках)."""

    _touch(tmp_path / "realTweets" / "Twitter_volume_AAPL.csv")
    _touch(tmp_path / "artificialNoAnomaly" / "art_flatline.csv")

    names = sorted(p.name for p in find_csv_files(tmp_path))

    assert names == ["Twitter_volume_AAPL.csv", "art_flatline.csv"]


def test_direct_gz_file_path_is_accepted(tmp_path: Path) -> None:
    """Путь к конкретному .csv.gz принимается без сканирования каталога."""

    target = _touch(tmp_path / "phase2_train.csv.gz")

    assert find_csv_files(target) == [target]


def test_collect_deduplicates_paths(tmp_path: Path) -> None:
    """Повторно указанные пути не дублируются в результате."""

    target = _touch(tmp_path / "phase2_train.csv.gz")

    collected = collect_csv_files([tmp_path, target])

    assert len(collected) == 1


def test_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        find_csv_files(tmp_path / "нет-такого")
