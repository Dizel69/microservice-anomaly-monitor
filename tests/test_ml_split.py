"""Временной сплит: без shuffle, KPI по файлам, NAB по правилу окон/70%."""

from __future__ import annotations

import pandas as pd
import pytest

from etl.features.feature_engineering import add_features
from etl.schema import (
    LABEL,
    METRIC_NAME,
    SERVICE,
    SOURCE,
    SOURCE_KPI,
    SOURCE_NAB,
    TIMESTAMP,
    VALUE,
)
from ml.split import (
    NAB_TRAIN_TIME_FRACTION,
    assert_temporal_split,
    nab_cut_timestamp,
    split_by_time,
    split_kpi,
)


def _series(
    *,
    source: str,
    service: str,
    n: int,
    anomaly_at: int | None,
    metric: str = "cpu_usage",
    start: str = "2024-01-01",
) -> pd.DataFrame:
    stamps = pd.date_range(start, periods=n, freq="1min")
    labels = [0] * n
    if anomaly_at is not None:
        for idx in range(anomaly_at, n):
            if idx < anomaly_at + 5:
                labels[idx] = 1
    values = [float(i) for i in range(n)]
    if anomaly_at is not None:
        values[anomaly_at] = 10_000.0
    return pd.DataFrame(
        {
            TIMESTAMP: stamps,
            SERVICE: service,
            METRIC_NAME: metric,
            VALUE: values,
            LABEL: labels,
            SOURCE: source,
        }
    )


def test_nab_split_is_temporal_not_shuffled() -> None:
    """Внутри ряда test начинается строго после train; порядок времени сохранён."""

    frame = _series(source=SOURCE_NAB, service="ec2_a", n=80, anomaly_at=50)
    train, test = split_by_time(frame)

    assert not train.empty and not test.empty
    assert_temporal_split(train, test)
    assert train[TIMESTAMP].max() < test[TIMESTAMP].min()
    assert list(train[TIMESTAMP]) == sorted(train[TIMESTAMP])
    assert list(test[TIMESTAMP]) == sorted(test[TIMESTAMP])
    # Первая аномалия — граница: в train нет label=1.
    assert int(train[LABEL].sum()) == 0
    assert int(test[LABEL].sum()) >= 1


def test_nab_fallback_is_seventy_percent_of_time_range() -> None:
    """Без окон аномалий отсечка — 70% временного диапазона ряда."""

    frame = _series(source=SOURCE_NAB, service="flat", n=101, anomaly_at=None)
    cut = nab_cut_timestamp(frame)
    tmin, tmax = frame[TIMESTAMP].min(), frame[TIMESTAMP].max()
    expected = tmin + NAB_TRAIN_TIME_FRACTION * (tmax - tmin)
    assert cut == expected

    train, test = split_by_time(frame)
    assert train[TIMESTAMP].max() < cut
    assert test[TIMESTAMP].min() >= cut


def test_kpi_split_uses_separate_train_and_ground_truth_files() -> None:
    """Один KPI ID, два кадра: train-файл и ground_truth; будущее не в fit."""

    kpi_id = "da10a69f-d836-3baa-ad40-3e548ecf1fbd"
    train_df = _series(
        source=SOURCE_KPI, service=kpi_id, n=40, anomaly_at=None, metric="kpi_value"
    )
    test_df = _series(
        source=SOURCE_KPI,
        service=kpi_id,
        n=20,
        anomaly_at=10,
        metric="kpi_value",
        start="2024-01-01 01:00:00",
    )
    # Намеренно подмешали одну «будущую» точку в train — она должна выпасть.
    leak = test_df.iloc[[0]].copy()
    leak[VALUE] = 999.0
    train_with_leak = pd.concat([train_df, leak], ignore_index=True)

    train, test = split_kpi(train_with_leak, test_df)

    assert train[SERVICE].unique().tolist() == [kpi_id]
    assert test[SERVICE].unique().tolist() == [kpi_id]
    assert_temporal_split(train, test)
    assert 999.0 not in set(train[VALUE].tolist())
    assert len(test) == 20


def test_split_does_not_call_shuffle(monkeypatch: pytest.MonkeyPatch) -> None:
    """pandas sample/shuffle не используются при сплите."""

    def _boom(*_args, **_kwargs):
        raise AssertionError("shuffle/sample не должен вызываться")

    monkeypatch.setattr(pd.DataFrame, "sample", _boom)
    frame = _series(source=SOURCE_NAB, service="s", n=30, anomaly_at=20)
    split_by_time(add_features(frame))
    split_kpi(frame.iloc[:15], frame.iloc[15:])


def test_two_series_are_split_independently() -> None:
    """У каждого ряда своя отсечка, глобальной перемешки нет."""

    a = _series(source=SOURCE_NAB, service="a", n=40, anomaly_at=28)
    b = _series(source=SOURCE_NAB, service="b", n=40, anomaly_at=10, start="2020-01-01")
    train, test = split_by_time(pd.concat([a, b], ignore_index=True))
    assert_temporal_split(train, test)
    assert set(train[SERVICE]) == {"a", "b"}
    assert set(test[SERVICE]) == {"a", "b"}
