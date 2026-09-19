"""Zabbix: parquet единой схемы, label=-1, файлы .dump в ETL не принимаются."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import main as cli
from etl.loaders import load_zabbix_dump
from etl.schema import (
    LABEL,
    LABELS,
    LABEL_UNKNOWN,
    METRIC_NAME,
    METRIC_UNKNOWN,
    SOURCE,
    SOURCE_ZABBIX,
    UNIFIED_COLUMNS,
)


def _write_zabbix_parquet(
    path: Path,
    *,
    metric_name: str,
    grain: str,
    rows: int = 4,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-08-04", periods=rows, freq="1h"),
            "service": "zabbix-server",
            "metric_name": metric_name,
            "value": [float(i) for i in range(rows)],
            "label": 1,
            "source": "OTHER",
            "labels": [
                '{"grain": "%s", "host": "zabbix-server", "itemid": 1, "key_": "system.cpu.util", "units": "%%"}'
                % grain
            ]
            * rows,
        }
    ).to_parquet(path)
    return path


def test_dump_label_is_unknown(tmp_path: Path) -> None:
    """У Zabbix нет эталонных меток: любые значения в файле заменяются на -1."""

    dump = _write_zabbix_parquet(
        tmp_path / "zabbix_history.parquet",
        metric_name="system.cpu.util",
        grain="history",
    )
    frame = load_zabbix_dump(dump)

    assert frame[LABEL].unique().tolist() == [LABEL_UNKNOWN]
    assert frame[SOURCE].unique().tolist() == [SOURCE_ZABBIX]
    assert UNIFIED_COLUMNS == list(frame.columns)[: len(UNIFIED_COLUMNS)]
    assert METRIC_UNKNOWN not in frame[METRIC_NAME].tolist()
    assert frame[METRIC_NAME].unique().tolist() == ["system.cpu.util"]


def test_trends_keep_grain_suffix(tmp_path: Path) -> None:
    """Trends не смешиваются с history: суффикс grain остаётся в metric_name."""

    dump = _write_zabbix_parquet(
        tmp_path / "zabbix_trends.parquet",
        metric_name='system.cpu.util{grain="trend_avg"}',
        grain="trend_avg",
    )
    frame = load_zabbix_dump(dump)

    assert frame[METRIC_NAME].unique().tolist() == ['system.cpu.util{grain="trend_avg"}']
    assert LABELS in frame.columns


def test_pg_dump_file_is_rejected(tmp_path: Path) -> None:
    """Custom-format pg_dump pandas не читает — загрузчик это говорит явно."""

    dump = tmp_path / "zabbix_history.dump"
    dump.write_bytes(b"PGDMP")

    with pytest.raises(ValueError, match="dump"):
        load_zabbix_dump(dump)


def test_cli_concatenates_history_and_trends(tmp_path: Path) -> None:
    """Два parquet склеиваются в один источник ZABBIX, .dump игнорируется."""

    _write_zabbix_parquet(
        tmp_path / "zabbix_history.parquet",
        metric_name="system.cpu.util",
        grain="history",
    )
    _write_zabbix_parquet(
        tmp_path / "zabbix_trends.parquet",
        metric_name='system.cpu.util{grain="trend_avg"}',
        grain="trend_avg",
        rows=2,
    )
    (tmp_path / "zabbix_history.dump").write_bytes(b"PGDMP")

    sources = cli._zabbix_sources([str(tmp_path)])
    assert len(sources) == 1
    frame = sources[0].dataframe
    assert frame[SOURCE].unique().tolist() == [SOURCE_ZABBIX]
    assert frame[LABEL].unique().tolist() == [LABEL_UNKNOWN]
    assert set(frame[METRIC_NAME].unique()) == {
        "system.cpu.util",
        'system.cpu.util{grain="trend_avg"}',
    }
    assert len(frame) == 6
    assert sources[0].persist_raw is False


def test_zabbix_cli_subcommand_exists() -> None:
    """python main.py zabbix принимает необязательные пути, как kpi."""

    args = cli.build_parser().parse_args(["zabbix"])
    assert args.command == "zabbix"
    assert args.paths == []
