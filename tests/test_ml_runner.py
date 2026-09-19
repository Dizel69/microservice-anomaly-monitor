"""Runner: таблица model/source/PR-AUC/P/R и fit без меток."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from etl.features.feature_engineering import build_ml_dataset
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
from ml.metrics import REPORT_COLUMNS
from ml.models import (
    IsolationForestDetector,
    MODEL_FEATURE_COLUMNS,
    OCSVMDetector,
    ZScoreDetector,
)
from ml.runner import run_comparison, run_kpi_frames, run_on_frame, save_report
from ml.split import split_by_time


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


def test_runner_writes_required_columns(tmp_path: Path) -> None:
    """Таблица: model, source, PR-AUC, P, R, n_train, n_test."""

    frame = build_ml_dataset(_nab_frame())
    table = run_on_frame(
        frame,
        models=[ZScoreDetector(), IsolationForestDetector()],
        include_ocsvm=False,
    )
    path = tmp_path / "ml_table.csv"
    save_report(table, path)

    loaded = pd.read_csv(path)
    assert list(loaded.columns) == list(REPORT_COLUMNS)
    assert set(loaded["model"]) <= {"zscore", "iforest"}
    assert loaded["source"].unique().tolist() == [SOURCE_NAB]
    assert (loaded["n_train"] > 0).all()
    assert (loaded["n_test"] > 0).all()
    assert loaded["n_train"].iloc[0] + loaded["n_test"].iloc[0] == len(frame)


def test_fit_does_not_receive_labels(monkeypatch) -> None:
    """Обёртка передаёт в fit только матрицу признаков, без колонки label."""

    frame = build_ml_dataset(_nab_frame(n=60, anomaly_at=42))
    train, test = split_by_time(frame)
    seen: list[tuple[int, int]] = []
    original = ZScoreDetector.fit

    def wrapped(self, X):
        seen.append(np.asarray(X).shape)
        assert np.asarray(X).shape[1] == len(MODEL_FEATURE_COLUMNS)
        return original(self, X)

    monkeypatch.setattr(ZScoreDetector, "fit", wrapped)
    run_comparison(train, test, models=[ZScoreDetector()])
    assert seen, "fit не вызывался"
    assert all(cols == len(MODEL_FEATURE_COLUMNS) for _, cols in seen)


def test_kpi_runner_on_two_file_fixture() -> None:
    """KPI: train и ground_truth с одним ID, OCSVM не в очереди."""

    kpi_id = "kpi-fixture-1"
    train_raw = pd.DataFrame(
        {
            TIMESTAMP: pd.date_range("2024-01-01", periods=50, freq="1min"),
            SERVICE: kpi_id,
            METRIC_NAME: "kpi_value",
            VALUE: np.linspace(0.0, 1.0, 50),
            LABEL: [0] * 50,
            SOURCE: SOURCE_KPI,
        }
    )
    test_values = np.linspace(1.0, 2.0, 30)
    test_values[20:24] = 50.0
    test_raw = pd.DataFrame(
        {
            TIMESTAMP: pd.date_range("2024-01-01 01:00:00", periods=30, freq="1min"),
            SERVICE: kpi_id,
            METRIC_NAME: "kpi_value",
            VALUE: test_values,
            LABEL: [0] * 20 + [1] * 4 + [0] * 6,
            SOURCE: SOURCE_KPI,
        }
    )
    table = run_kpi_frames(
        train_raw,
        test_raw,
        models=[ZScoreDetector()],
        include_ocsvm=False,
    )
    assert table["source"].tolist() == [SOURCE_KPI]
    assert table["model"].tolist() == ["zscore"]
    assert "ocsvm" not in set(table["model"])
    assert int(table["n_train"].iloc[0]) == 50
    assert int(table["n_test"].iloc[0]) == 30


def test_ocsvm_fits_on_small_fixture() -> None:
    """OCSVM допустим на маленьком срезе, не на полном KPI."""

    frame = build_ml_dataset(_nab_frame(n=80, anomaly_at=56))
    table = run_on_frame(frame, models=[OCSVMDetector()], include_ocsvm=True)
    assert table["model"].tolist() == ["ocsvm"]
    assert table["source"].tolist() == [SOURCE_NAB]
    assert int(table["n_test"].iloc[0]) > 0


def test_mixed_frame_reports_only_labeled_source() -> None:
    """NAB попадает в таблицу, PROMETHEUS из того же кадра — нет."""

    nab = _nab_frame(n=70, anomaly_at=49)
    prom = nab.copy()
    prom[SOURCE] = SOURCE_PROMETHEUS
    prom[SERVICE] = "prom-svc"
    prom[LABEL] = -1
    table = run_on_frame(
        pd.concat([nab, prom], ignore_index=True),
        models=[ZScoreDetector()],
    )
    assert table["source"].unique().tolist() == [SOURCE_NAB]
    assert SOURCE_PROMETHEUS not in set(table["source"])
