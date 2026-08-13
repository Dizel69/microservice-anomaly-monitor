"""Определение metric_name: без ложных срабатываний и без «unknown» у NAB."""

from __future__ import annotations

from pathlib import Path

import pytest

from etl.config import RAW_NAB_DIR
from etl.loaders.nab_loader import _resolve_metric
from etl.schema import (
    METRIC_CPU,
    METRIC_DISK,
    METRIC_LATENCY,
    METRIC_MEMORY,
    METRIC_NETWORK,
    METRIC_REQUEST_RATE,
    METRIC_TAXI_DEMAND,
    METRIC_TEMPERATURE,
    METRIC_TWEET_VOLUME,
    METRIC_UNKNOWN,
    infer_metric_name,
    tokenize_metric_text,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ec2_cpu_utilization_5f5533", METRIC_CPU),
        ("rds_cpu_utilization_cc0c53", METRIC_CPU),
        ("node_memory_MemAvailable_bytes", METRIC_MEMORY),
        ("ec2_disk_write_bytes_1ef3de", METRIC_DISK),
        ("ec2_network_in_257a54", METRIC_NETWORK),
        ("iio_us-east-1_i-a2eb1cd9_NetworkIn", METRIC_NETWORK),
        ("ec2_request_latency_system_failure", METRIC_LATENCY),
        ("elb_request_count_8c0756", METRIC_REQUEST_RATE),
        ("machine_temperature_system_failure", METRIC_TEMPERATURE),
        ("nyc_taxi", METRIC_TAXI_DEMAND),
        ("Twitter_volume_AAPL", METRIC_TWEET_VOLUME),
    ],
)
def test_metric_inferred_from_name(text: str, expected: str) -> None:
    assert infer_metric_name(text) == expected


@pytest.mark.parametrize(
    "text", ["art_daily_flatmiddle", "art_daily_jumpsup", "art_noisy", "art_flatline"]
)
def test_art_prefix_is_not_mistaken_for_latency(text: str) -> None:
    """Подстрока 'rt' внутри 'art_' не должна давать метрику http_latency."""

    assert infer_metric_name(text) != METRIC_LATENCY


def test_tokenizer_splits_camel_case_and_separators() -> None:
    assert tokenize_metric_text("iio_us-east-1_i-a2eb1cd9_NetworkIn") == [
        "iio",
        "us",
        "east",
        "1",
        "i",
        "a2eb1cd9",
        "network",
        "in",
    ]


def test_category_fallback_for_synthetic_series(tmp_path: Path) -> None:
    """Если эвристика не сработала, метрика берётся из категории NAB."""

    path = tmp_path / "artificialWithAnomaly" / "art_daily_flatmiddle.csv"

    assert _resolve_metric(path) == "synthetic_metric"


def test_no_unknown_metric_across_local_nab_files() -> None:
    """Ни один локальный ряд NAB не остаётся с metric_name=unknown_metric."""

    csv_files = sorted(RAW_NAB_DIR.rglob("*.csv"))
    if not csv_files:
        pytest.skip("Нет локальных файлов NAB")

    unknown = [p.name for p in csv_files if _resolve_metric(p) == METRIC_UNKNOWN]

    assert unknown == []
