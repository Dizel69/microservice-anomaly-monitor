"""Prometheus: работаем только с локальными дампами, метки — «неизвестно»."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import main as cli
from etl.loaders import load_prometheus_dump
from etl.schema import (
    LABEL,
    LABEL_UNKNOWN,
    SOURCE,
    SOURCE_PROMETHEUS,
    UNIFIED_COLUMNS,
)


def test_dump_label_is_unknown(real_prometheus_dump: Path) -> None:
    """Все точки дампа получают label=-1: настоящих меток у Prometheus нет."""

    frame = load_prometheus_dump(real_prometheus_dump)

    assert frame[LABEL].unique().tolist() == [LABEL_UNKNOWN]
    assert frame[SOURCE].unique().tolist() == [SOURCE_PROMETHEUS]


def test_dump_has_schema_columns(real_prometheus_dump: Path) -> None:
    """Дамп приводится к колонкам единой схемы."""

    frame = load_prometheus_dump(real_prometheus_dump)

    assert UNIFIED_COLUMNS == list(frame.columns)[: len(UNIFIED_COLUMNS)]


def test_existing_labels_in_dump_are_overridden(tmp_path: Path) -> None:
    """Посторонние метки в дампе заменяются на -1, а не переносятся как есть."""

    dump = tmp_path / "raw_prometheus_fake.parquet"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="15s"),
            "service": "node-exporter",
            "metric_name": "cpu_usage",
            "value": [1.0, 2.0, 3.0],
            "label": [1, 1, 0],
            "source": "SOMETHING_ELSE",
        }
    ).to_parquet(dump)

    frame = load_prometheus_dump(dump)

    assert frame[LABEL].unique().tolist() == [LABEL_UNKNOWN]
    assert frame[SOURCE].unique().tolist() == [SOURCE_PROMETHEUS]


def test_all_command_uses_local_dumps_without_http(
    monkeypatch, tmp_path: Path
) -> None:
    """Команда 'all' без --prom-url не обращается к живому HTTP API."""

    def fail(*args, **kwargs):
        raise AssertionError("живой Prometheus API не должен вызываться")

    monkeypatch.setattr(cli, "load_prometheus", fail)
    dump_root = tmp_path / "PROMETHEUS"
    live = dump_root / "live"
    live.mkdir(parents=True)
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-08-04", periods=3, freq="15s"),
            "service": "backend",
            "metric_name": "app_events",
            "value": [1.0, 2.0, 3.0],
            "label": [1, 0, 1],
            "source": "SOMETHING_ELSE",
        }
    )
    frame.to_parquet(live / "app_events.parquet")
    monkeypatch.setattr(cli, "RAW_PROMETHEUS_DIR", dump_root)

    args = cli.build_parser().parse_args(["all"])

    assert args.prom_url is None
    assert args.prom_query is None
    sources = cli._prometheus_local_sources()
    assert len(sources) == 1, "ожидался один склеенный источник Prometheus"
    assert sources[0].dataframe[SOURCE].unique().tolist() == [SOURCE_PROMETHEUS]
    assert sources[0].dataframe[LABEL].unique().tolist() == [LABEL_UNKNOWN]


def test_series_with_different_labels_stay_separate(real_prometheus_dump: Path) -> None:
    """Ряды одной метрики с разными метками не сливаются в один и не теряются."""

    frame = load_prometheus_dump(real_prometheus_dump)
    duplicated = frame.duplicated(subset=UNIFIED_COLUMNS).sum()

    assert duplicated == 0, "точки разных рядов схлопнулись бы при дедупликации"


def test_metric_name_qualified_only_by_varying_labels(tmp_path: Path) -> None:
    """Уточняются только различающиеся метки; постоянные не попадают в имя."""

    dump = tmp_path / "raw_prometheus_cpu.parquet"
    pd.DataFrame(
        {
            "timestamp": list(pd.date_range("2024-01-01", periods=2, freq="15s")) * 2,
            "service": "node-exporter",
            "metric_name": "cpu_usage",
            "value": [0.0, 0.0, 1.0, 1.0],
            "label": -1,
            "source": "PROMETHEUS",
            "labels": [
                '{"__name__": "node_cpu_seconds_total", "job": "node-exporter", "mode": "idle"}',
                '{"__name__": "node_cpu_seconds_total", "job": "node-exporter", "mode": "idle"}',
                '{"__name__": "node_cpu_seconds_total", "job": "node-exporter", "mode": "user"}',
                '{"__name__": "node_cpu_seconds_total", "job": "node-exporter", "mode": "user"}',
            ],
        }
    ).to_parquet(dump)

    frame = load_prometheus_dump(dump)

    assert sorted(frame["metric_name"].unique()) == [
        'cpu_usage{mode="idle"}',
        'cpu_usage{mode="user"}',
    ]


def test_single_series_metric_name_unchanged(tmp_path: Path) -> None:
    """Когда различающих меток нет, имя метрики остаётся каноническим."""

    dump = tmp_path / "raw_prometheus_mem.parquet"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=2, freq="15s"),
            "service": "node-exporter",
            "metric_name": "memory_usage",
            "value": [1.0, 2.0],
            "label": -1,
            "source": "PROMETHEUS",
            "labels": ['{"__name__": "node_memory_MemAvailable_bytes"}'] * 2,
        }
    ).to_parquet(dump)

    frame = load_prometheus_dump(dump)

    assert frame["metric_name"].unique().tolist() == ["memory_usage"]


def test_qualification_is_idempotent(tmp_path: Path) -> None:
    """Повторная обработка уже уточнённого дампа не наращивает имя метрики."""

    dump = tmp_path / "raw_prometheus_cpu.parquet"
    frame = pd.DataFrame(
        {
            "timestamp": list(pd.date_range("2024-01-01", periods=2, freq="15s")) * 2,
            "service": "node-exporter",
            "metric_name": "cpu_usage",
            "value": [0.0, 0.5, 1.0, 1.5],
            "label": -1,
            "source": "PROMETHEUS",
            "labels": [
                '{"__name__": "node_cpu_seconds_total", "mode": "idle"}',
                '{"__name__": "node_cpu_seconds_total", "mode": "idle"}',
                '{"__name__": "node_cpu_seconds_total", "mode": "user"}',
                '{"__name__": "node_cpu_seconds_total", "mode": "user"}',
            ],
        }
    )
    frame.to_parquet(dump)

    once = load_prometheus_dump(dump)
    once.to_parquet(dump)
    twice = load_prometheus_dump(dump)

    assert sorted(twice["metric_name"].unique()) == sorted(
        once["metric_name"].unique()
    )
    assert not any("}{" in name for name in twice["metric_name"])


def test_pipeline_does_not_overwrite_its_own_input_dump(tmp_path: Path) -> None:
    """Конвейер не затирает исходный дамп результатом обработки."""

    from etl.config import PipelinePaths
    from etl.pipeline import LoadedSource, run_pipeline

    raw_dir = tmp_path / "raw"
    dump = raw_dir / SOURCE_PROMETHEUS / "raw_prometheus_cpu.parquet"
    dump.parent.mkdir(parents=True)
    original = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=4, freq="15s"),
            "service": "node-exporter",
            "metric_name": "cpu_usage",
            "value": [1.0, 2.0, 3.0, 4.0],
            "label": -1,
            "source": SOURCE_PROMETHEUS,
            "labels": ['{"__name__": "node_cpu_seconds_total"}'] * 4,
        }
    )
    original.to_parquet(dump)
    checksum_before = dump.read_bytes()

    run_pipeline(
        [
            LoadedSource(
                name="prometheus_cpu",
                dataframe=load_prometheus_dump(dump),
                source_path=dump,
            )
        ],
        paths=PipelinePaths(
            raw_dir=raw_dir,
            processed_dir=tmp_path / "processed",
            unified_dir=tmp_path / "unified",
            reports_dir=tmp_path / "reports",
        ),
        make_visualizations=False,
    )

    assert dump.read_bytes() == checksum_before


def test_unsupported_dump_format_is_rejected(tmp_path: Path) -> None:
    """Файл неподдерживаемого формата не принимается молча."""

    bogus = tmp_path / "dump.txt"
    bogus.write_text("nope", encoding="utf-8")

    with pytest.raises(ValueError):
        load_prometheus_dump(bogus)


def _write_prom_dump(
    path: Path,
    *,
    service: str,
    metric_name: str,
    labels: str,
    rows: int = 3,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-08-04", periods=rows, freq="1min"),
            "service": service,
            "metric_name": metric_name,
            "value": [float(i) for i in range(rows)],
            "label": 0,
            "source": "OTHER",
            "labels": [labels] * rows,
        }
    ).to_parquet(path)
    return path


def test_local_sources_recurse_live_and_concat(tmp_path: Path) -> None:
    """live/**/*.parquet находятся рекурсивно и склеиваются в один источник."""

    root = tmp_path / "PROMETHEUS"
    _write_prom_dump(
        root / "raw_prometheus_cpu.parquet",
        service="node-exporter",
        metric_name="cpu_usage",
        labels='{"__name__": "node_cpu_seconds_total", "job": "node-exporter"}',
    )
    _write_prom_dump(
        root / "live" / "app_events.parquet",
        service="backend",
        metric_name="app_events",
        labels='{"__name__": "app_events", "job": "backend"}',
    )
    _write_prom_dump(
        root / "live" / "nested" / "postgres__pg_database_size_bytes.parquet",
        service="database",
        metric_name="pg_database_size_bytes",
        labels='{"__name__": "pg_database_size_bytes", "job": "postgres"}',
    )
    _write_prom_dump(
        root / "live" / "telegram_request_duration_seconds_bucket.parquet",
        service="bot",
        metric_name="http_latency",
        labels='{"__name__": "telegram_request_duration_seconds_bucket"}',
    )

    files = cli._prometheus_dump_files(root)
    names = sorted(p.name for p in files)
    assert "telegram_request_duration_seconds_bucket.parquet" not in names
    assert "app_events.parquet" in names
    assert "postgres__pg_database_size_bytes.parquet" in names

    sources = cli._prometheus_local_sources([str(root)])
    assert len(sources) == 1
    frame = sources[0].dataframe
    assert frame[LABEL].unique().tolist() == [LABEL_UNKNOWN]
    assert set(frame["service"].unique()) == {"backend", "database", "node-exporter"}
    assert sources[0].persist_raw is False


def test_job_prefix_in_filename_does_not_change_metric_name(tmp_path: Path) -> None:
    """Префикс job__ только в имени файла, qualify_metric_names его не видит."""

    dump = _write_prom_dump(
        tmp_path / "live" / "postgres__pg_database_size_bytes.parquet",
        service="database",
        metric_name="pg_database_size_bytes",
        labels='{"__name__": "pg_database_size_bytes", "datname": "m15db", "job": "postgres"}',
        rows=2,
    )

    frame = load_prometheus_dump(dump)

    assert frame["metric_name"].unique().tolist() == ["pg_database_size_bytes"]
    assert "postgres__" not in "".join(frame["metric_name"].astype(str))


def test_prometheus_cli_without_url_is_local_mode() -> None:
    """python main.py prometheus без URL — локальный режим, не HTTP."""

    args = cli.build_parser().parse_args(["prometheus"])
    assert args.targets == []
    assert cli._looks_like_url("http://127.0.0.1:9090")
    assert cli._looks_like_url("https://prom.example:9090")
    assert not cli._looks_like_url("datasets/raw/PROMETHEUS/live")


def test_prometheus_cli_url_still_parsed() -> None:
    """Старый вызов с URL остаётся HTTP-режимом."""

    args = cli.build_parser().parse_args(
        ["prometheus", "http://127.0.0.1:9090", "up"]
    )
    assert args.targets[0] == "http://127.0.0.1:9090"
    assert args.targets[1] == "up"
