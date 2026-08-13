"""Единый набор данных: схема, несколько источников, сохранение меток."""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd
import pytest

from etl.config import PipelinePaths
from etl.features.feature_engineering import FEATURE_COLUMNS
from etl.pipeline import LoadedSource, run_pipeline
from etl.schema import (
    LABEL,
    LABEL_ANOMALY,
    LABEL_NORMAL,
    LABEL_UNKNOWN,
    METRIC_NAME,
    SERVICE,
    SOURCE,
    SOURCE_KPI,
    SOURCE_NAB,
    SOURCE_PROMETHEUS,
    TIMESTAMP,
    UNIFIED_COLUMNS,
    VALUE,
)


def _frame(source: str, service: str, metric: str, labels: List[int]) -> pd.DataFrame:
    stamps = pd.date_range("2024-01-01", periods=len(labels), freq="1min")
    return pd.DataFrame(
        {
            TIMESTAMP: stamps,
            SERVICE: service,
            METRIC_NAME: metric,
            VALUE: [float(i) for i in range(len(labels))],
            LABEL: labels,
            SOURCE: source,
        }
    )


@pytest.fixture
def pipeline_paths(tmp_path: Path) -> PipelinePaths:
    """Пути конвейера внутри tmp_path, чтобы не трогать реальные reports/datasets."""

    return PipelinePaths(
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
        unified_dir=tmp_path / "unified",
        reports_dir=tmp_path / "reports" / "current",
    )


@pytest.fixture
def three_sources() -> List[LoadedSource]:
    return [
        LoadedSource(
            name="nyc_taxi",
            dataframe=_frame(SOURCE_NAB, "nyc_taxi", "taxi_demand", [0, 1, 1, 0]),
        ),
        LoadedSource(
            name="phase2_train",
            dataframe=_frame(SOURCE_KPI, "kpi-0001", "kpi_value", [0, 0, 1, 0]),
        ),
        LoadedSource(
            name="node_cpu",
            dataframe=_frame(
                SOURCE_PROMETHEUS, "node-exporter", "cpu_usage", [-1, -1, -1, -1]
            ),
        ),
    ]


def test_unified_has_schema_columns(three_sources, pipeline_paths) -> None:
    """Итоговый unified-набор содержит ровно колонки единой схемы и в порядке."""

    result = run_pipeline(
        three_sources, paths=pipeline_paths, make_visualizations=False
    )
    unified = pd.read_parquet(result.unified_parquet)

    assert list(unified.columns) == UNIFIED_COLUMNS


def test_unified_keeps_all_three_sources(three_sources, pipeline_paths) -> None:
    """В едином наборе присутствуют все три источника с исходными метками."""

    result = run_pipeline(
        three_sources, paths=pipeline_paths, make_visualizations=False
    )
    unified = pd.read_parquet(result.unified_parquet)

    assert sorted(unified[SOURCE].unique()) == [
        SOURCE_KPI,
        SOURCE_NAB,
        SOURCE_PROMETHEUS,
    ]
    by_source = unified.groupby(SOURCE)[LABEL].apply(set).to_dict()
    assert by_source[SOURCE_NAB] == {LABEL_NORMAL, LABEL_ANOMALY}
    assert by_source[SOURCE_KPI] == {LABEL_NORMAL, LABEL_ANOMALY}
    assert by_source[SOURCE_PROMETHEUS] == {LABEL_UNKNOWN}


def test_ml_dataset_has_features_and_label(three_sources, pipeline_paths) -> None:
    """ML-набор содержит признаки и метку, без пропусков в признаках."""

    result = run_pipeline(
        three_sources, paths=pipeline_paths, make_visualizations=False
    )
    ml = pd.read_parquet(result.features_parquet)

    assert set(FEATURE_COLUMNS).issubset(ml.columns)
    assert LABEL in ml.columns
    assert not ml[FEATURE_COLUMNS].isna().any().any()


def test_metric_name_is_never_empty(three_sources, pipeline_paths) -> None:
    """Колонка metric_name заполнена у всех строк."""

    result = run_pipeline(
        three_sources, paths=pipeline_paths, make_visualizations=False
    )
    unified = pd.read_parquet(result.unified_parquet)

    assert unified[METRIC_NAME].notna().all()
    assert (unified[METRIC_NAME].str.len() > 0).all()


def test_reports_are_written_only_under_current(
    three_sources, pipeline_paths, tmp_path: Path
) -> None:
    """Графики пишутся в подкаталоги reports/current/, не в корень и не в datasets."""

    result = run_pipeline(
        three_sources, paths=pipeline_paths, make_visualizations=True
    )

    reports_root = pipeline_paths.reports_dir
    written = sorted(reports_root.rglob("*.png"))
    assert written, "ожидались построенные графики"

    for png in written:
        assert png.parent != reports_root, f"PNG в корне current/: {png}"
        assert png.parent.parent == reports_root
    assert not list((tmp_path / "raw").rglob("*.png"))
    assert set(result.report_paths) == {
        SOURCE_NAB,
        SOURCE_KPI,
        SOURCE_PROMETHEUS,
        "combined",
    }
