"""Сравнение моделей: PNG, четыре детектора, PROMETHEUS вне таблицы."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from etl.schema import (
    LABEL,
    METRIC_NAME,
    SERVICE,
    SOURCE,
    SOURCE_KPI,
    SOURCE_NAB,
    SOURCE_PROMETHEUS,
    TIMESTAMP,
    VALUE,
)
from ml.cli import build_parser
from ml.compare import (
    COMPARE_MODELS,
    KPI_IDS_NAME,
    SUMMARY_NAME,
    iter_artifact_names,
    run_compare,
    select_kpi_ids,
)
from ml.metrics import REPORT_COLUMNS


def _nab_frame(n: int = 80, anomaly_at: int = 56, service: str = "series-a") -> pd.DataFrame:
    stamps = pd.date_range("2014-04-01", periods=n, freq="5min")
    values = np.sin(np.linspace(0, 8 * np.pi, n)) + 10.0
    labels = np.zeros(n, dtype="int64")
    values = values.copy()
    values[anomaly_at: anomaly_at + 4] += 25.0
    labels[anomaly_at: anomaly_at + 4] = 1
    return pd.DataFrame(
        {
            TIMESTAMP: stamps,
            SERVICE: service,
            METRIC_NAME: "cpu_usage",
            VALUE: values,
            LABEL: labels,
            SOURCE: SOURCE_NAB,
        }
    )


def _kpi_pair(kpi_id: str = "kpi-b") -> tuple[pd.DataFrame, pd.DataFrame]:
    train = pd.DataFrame(
        {
            TIMESTAMP: pd.date_range("2024-01-01", periods=40, freq="1min"),
            SERVICE: kpi_id,
            METRIC_NAME: "kpi_value",
            VALUE: np.linspace(0.0, 1.0, 40),
            LABEL: [0] * 40,
            SOURCE: SOURCE_KPI,
        }
    )
    values = np.linspace(1.0, 2.0, 30)
    values[18:22] = 40.0
    test = pd.DataFrame(
        {
            TIMESTAMP: pd.date_range("2024-01-01 02:00:00", periods=30, freq="1min"),
            SERVICE: kpi_id,
            METRIC_NAME: "kpi_value",
            VALUE: values,
            LABEL: [0] * 18 + [1] * 4 + [0] * 8,
            SOURCE: SOURCE_KPI,
        }
    )
    return train, test


def test_compare_writes_png_and_keeps_prometheus_out(tmp_path: Path, monkeypatch) -> None:
    """Сводка содержит все модели сравнения; PNG создаются; PROMETHEUS в таблицу не входит."""

    def _forbid_show(*_args, **_kwargs):
        raise AssertionError("plt.show() вызываться не должен")

    monkeypatch.setattr(plt, "show", _forbid_show)

    nab = _nab_frame()
    prom = nab.copy()
    prom[SOURCE] = SOURCE_PROMETHEUS
    prom[SERVICE] = "prom-live"
    prom[LABEL] = -1
    mixed = pd.concat([nab, prom], ignore_index=True)
    kpi_train, kpi_test = _kpi_pair("kpi-b")
    extra_train, extra_test = _kpi_pair("kpi-a")
    kpi_train = pd.concat([kpi_train, extra_train], ignore_index=True)
    kpi_test = pd.concat([kpi_test, extra_test], ignore_index=True)

    table = run_compare(
        nab_frame=mixed,
        kpi_train=kpi_train,
        kpi_test=kpi_test,
        kpi_series=8,
        output_dir=tmp_path,
        models=list(COMPARE_MODELS),
    )

    assert list(table.columns) == list(REPORT_COLUMNS)
    nab_rows = table.loc[table["source"] == SOURCE_NAB, "model"].tolist()
    kpi_rows = table.loc[table["source"] == SOURCE_KPI, "model"].tolist()
    assert nab_rows == list(COMPARE_MODELS)
    assert kpi_rows == list(COMPARE_MODELS)
    assert SOURCE_PROMETHEUS not in set(table["source"])
    assert len(table) == 2 * len(COMPARE_MODELS)

    expected = iter_artifact_names((SOURCE_NAB, SOURCE_KPI), COMPARE_MODELS)
    for name in expected:
        path = tmp_path / name
        assert path.is_file(), name
        assert path.stat().st_size > 0
    assert not any("PROMETHEUS" in path.name for path in tmp_path.glob("*.png"))

    summary = pd.read_csv(tmp_path / SUMMARY_NAME)
    assert list(summary.columns) == list(REPORT_COLUMNS)
    assert set(summary["model"]) == set(COMPARE_MODELS)
    ids = (tmp_path / KPI_IDS_NAME).read_text(encoding="utf-8").split()
    assert ids == ["kpi-a", "kpi-b"]


def test_select_kpi_ids_is_sorted_intersection(tmp_path: Path) -> None:
    """Общие id сортируются; id только из одного файла в срез не попадают."""

    train = pd.DataFrame(
        {
            "timestamp": [1, 2, 3, 4],
            "value": [0.1, 0.2, 0.3, 0.4],
            "label": [0, 0, 0, 1],
            "KPI ID": ["b", "a", "only-train", "c"],
        }
    )
    test = pd.DataFrame(
        {
            "timestamp": [10, 11, 12],
            "value": [1.0, 1.1, 1.2],
            "label": [0, 1, 0],
            "KPI ID": ["c", "only-test", "a"],
        }
    )
    train_path = tmp_path / "phase2_train.csv.gz"
    test_path = tmp_path / "phase2_ground_truth.csv.gz"
    train.to_csv(train_path, index=False, compression="gzip")
    test.to_csv(test_path, index=False, compression="gzip")

    assert select_kpi_ids(train_path, test_path, 8) == ["a", "c"]
    assert select_kpi_ids(train_path, test_path, 1) == ["a"]


def test_compare_cli_flags() -> None:
    """Флаги compare: срез KPI по умолчанию 8, источники взаимоисключающие."""

    parser = build_parser()
    both = parser.parse_args(["compare"])
    assert both.kpi_series == 8
    assert both.nab_only is False
    assert both.kpi_only is False

    kpi = parser.parse_args(["compare", "--kpi-only", "--kpi-series", "3"])
    assert kpi.kpi_only is True
    assert kpi.nab_only is False
    assert kpi.kpi_series == 3
