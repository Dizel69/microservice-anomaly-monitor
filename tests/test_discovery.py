"""Поиск исходных файлов: сжатые .csv.gz должны находиться наравне с .csv."""

from __future__ import annotations

from pathlib import Path

import pytest

from etl.discovery import (
    collect_csv_files,
    collect_dump_files,
    find_csv_files,
    find_dump_files,
    is_histogram_remnant,
)


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


def _touch_parquet(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"PAR1")
    return path


def test_find_dump_files_recurses_into_live(tmp_path: Path) -> None:
    """Каталог PROMETHEUS сканируется рекурсивно, включая live/."""

    _touch_parquet(tmp_path / "raw_prometheus_cpu.parquet")
    _touch_parquet(tmp_path / "live" / "app_events.parquet")
    _touch_parquet(tmp_path / "live" / "nested" / "postgres__pg_stat.parquet")
    (tmp_path / "live" / "zabbix_history.dump").write_bytes(b"PGDMP")

    found = find_dump_files(tmp_path)
    names = sorted(p.name for p in found)

    assert names == [
        "app_events.parquet",
        "postgres__pg_stat.parquet",
        "raw_prometheus_cpu.parquet",
    ]


def test_directory_scan_skips_histogram_remnants(tmp_path: Path) -> None:
    """Ошмётки *_bucket / *_created не попадают в выдачу при обходе каталога."""

    _touch_parquet(tmp_path / "live" / "app_events.parquet")
    bucket = _touch_parquet(tmp_path / "live" / "telegram_request_duration_seconds_bucket.parquet")
    created = _touch_parquet(tmp_path / "live" / "telegram_messages_sent_created.parquet")
    _touch_parquet(tmp_path / "live" / "postgres__pg_stat_activity_count_created.parquet")

    names = sorted(p.name for p in find_dump_files(tmp_path))

    assert names == ["app_events.parquet"]
    assert is_histogram_remnant(bucket)
    assert is_histogram_remnant(created)


def test_explicit_dump_path_is_kept_even_if_bucket(tmp_path: Path) -> None:
    """Явно указанный файл не отфильтровывается — это отладка, не обход каталога."""

    bucket = _touch_parquet(tmp_path / "live" / "foo_bucket.parquet")

    assert find_dump_files(bucket) == [bucket]


def test_collect_dump_files_ignores_pg_dump(tmp_path: Path) -> None:
    """Custom-format .dump Zabbix не считается входом ETL."""

    _touch_parquet(tmp_path / "zabbix_history.parquet")
    (tmp_path / "zabbix_history.dump").write_bytes(b"PGDMP")

    names = [p.name for p in collect_dump_files([tmp_path])]

    assert names == ["zabbix_history.parquet"]
