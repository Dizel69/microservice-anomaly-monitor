"""Временной сплит по ряду. Shuffle не используется.

Ряд = ``(source, service, metric_name)``. Train — прошлое, test — будущее.

Правило NAB (зафиксировано): train — точки строго до первой метки ``label=1``
(начало первого окна ``combined_windows.json``); если окон нет или до окна
не остаётся ни одной точки — отсечка на 70% временного диапазона ряда.
Test — хвост от отсечки включительно.

KPI: train и test уже разные файлы (``phase2_train`` / ``phase2_ground_truth``);
из train дополнительно выбрасываются точки с временем не раньше первой
точки того же ряда в test, чтобы будущее не попало в ``fit``.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import pandas as pd

from etl.schema import (
    LABEL,
    LABEL_ANOMALY,
    METRIC_NAME,
    SERVICE,
    SOURCE,
    SOURCE_NAB,
    TIMESTAMP,
)

#: Доля временного диапазона ряда, которая идёт в train при fallback NAB
#: и для источников без окон разметки.
NAB_TRAIN_TIME_FRACTION: float = 0.70

SERIES_KEYS: List[str] = [SOURCE, SERVICE, METRIC_NAME]


def _require_columns(df: pd.DataFrame, columns: Sequence[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Нет колонок для сплита: {missing}")


def time_fraction_cut(
    timestamps: pd.Series,
    fraction: float = NAB_TRAIN_TIME_FRACTION,
) -> pd.Timestamp:
    """Отсечка на ``fraction`` длины временного диапазона (не по числу точек)."""

    times = pd.to_datetime(timestamps, errors="coerce")
    tmin = times.min()
    tmax = times.max()
    if pd.isna(tmin) or pd.isna(tmax) or tmin == tmax:
        return tmin
    return tmin + fraction * (tmax - tmin)


def nab_cut_timestamp(series_df: pd.DataFrame) -> pd.Timestamp:
    """Граница train/test для одного ряда NAB.

    Сначала пробуем начало первого окна аномалии (минимальный timestamp с
    ``label=1``). Если такого окна нет или все точки ряда лежат не раньше
    этой границы — 70% временного диапазона.
    """

    _require_columns(series_df, (TIMESTAMP, LABEL))
    times = pd.to_datetime(series_df[TIMESTAMP], errors="coerce")
    fallback = time_fraction_cut(times, NAB_TRAIN_TIME_FRACTION)

    anomaly_times = times[pd.to_numeric(series_df[LABEL], errors="coerce") == LABEL_ANOMALY]
    if anomaly_times.empty:
        return fallback

    window_start = anomaly_times.min()
    if (times < window_start).any():
        return window_start
    return fallback


def _cut_for_group(group: pd.DataFrame) -> pd.Timestamp:
    source = str(group[SOURCE].iloc[0]) if SOURCE in group.columns else ""
    if source == SOURCE_NAB:
        return nab_cut_timestamp(group)
    return time_fraction_cut(group[TIMESTAMP], NAB_TRAIN_TIME_FRACTION)


def groups_map(df: pd.DataFrame, keys: Sequence[str]) -> dict:
    """Словарь групп. ``dict(groupby)`` нельзя: у GroupBy ``.keys`` — не метод."""

    cols = list(keys)
    by: str | List[str] = cols[0] if len(cols) == 1 else cols
    return {key: grp for key, grp in df.groupby(by, dropna=False, sort=False)}


def _concat(parts: Iterable[pd.DataFrame]) -> pd.DataFrame:
    frames = [part for part in parts if part is not None and not part.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def split_by_time(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Разбить кадр по времени внутри каждого ряда. Без shuffle.

    Returns:
        ``(train, test)``: train — timestamps строго меньше отсечки,
        test — отсечка и хвост.
    """

    _require_columns(df, (TIMESTAMP, *SERIES_KEYS))
    if df.empty:
        empty = df.copy()
        return empty, empty

    trains: List[pd.DataFrame] = []
    tests: List[pd.DataFrame] = []
    grouped = df.groupby(SERIES_KEYS, dropna=False, sort=False)
    for _, group in grouped:
        ordered = group.sort_values(TIMESTAMP, kind="mergesort")
        cut = _cut_for_group(ordered)
        times = pd.to_datetime(ordered[TIMESTAMP], errors="coerce")
        trains.append(ordered.loc[times < cut])
        tests.append(ordered.loc[times >= cut])
    return _concat(trains), _concat(tests)


def split_kpi(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Сплит KPI по файлам train / ground_truth с защитой от утечки будущего.

    Args:
        train_df: Кадр из ``phase2_train`` (уже в единой схеме).
        test_df: Кадр из ``phase2_ground_truth``.

    Returns:
        Train без точек, время которых не раньше первой test-точки того же
        ряда; test — ряды, для которых остался непустой train.
    """

    _require_columns(train_df, (TIMESTAMP, *SERIES_KEYS))
    _require_columns(test_df, (TIMESTAMP, *SERIES_KEYS))

    if train_df.empty or test_df.empty:
        return train_df.copy(), test_df.iloc[0:0].copy()

    trains: List[pd.DataFrame] = []
    tests: List[pd.DataFrame] = []
    train_groups = {
        key: grp.sort_values(TIMESTAMP, kind="mergesort")
        for key, grp in train_df.groupby(SERIES_KEYS, dropna=False, sort=False)
    }

    for key, test_group in test_df.groupby(SERIES_KEYS, dropna=False, sort=False):
        train_group = train_groups.get(key)
        if train_group is None or train_group.empty:
            continue
        test_ordered = test_group.sort_values(TIMESTAMP, kind="mergesort")
        test_start = pd.to_datetime(test_ordered[TIMESTAMP], errors="coerce").min()
        train_times = pd.to_datetime(train_group[TIMESTAMP], errors="coerce")
        train_clean = train_group.loc[train_times < test_start]
        if train_clean.empty:
            continue
        trains.append(train_clean)
        tests.append(test_ordered)

    return _concat(trains), _concat(tests)


def assert_temporal_split(train: pd.DataFrame, test: pd.DataFrame) -> None:
    """Проверить, что внутри каждого ряда test начинается после train.

    Raises:
        AssertionError: Если найден ряд с ``max(train.time) >= min(test.time)``
            или кадры перемешаны по времени внутри себя.
    """

    if train.empty or test.empty:
        return
    for frame, name in ((train, "train"), (test, "test")):
        for key, group in frame.groupby(SERIES_KEYS, dropna=False, sort=False):
            times = pd.to_datetime(group[TIMESTAMP], errors="coerce")
            if not times.is_monotonic_increasing:
                raise AssertionError(f"{name} ряда {key} не отсортирован по времени")

    train_groups = groups_map(train, SERIES_KEYS)
    test_groups = groups_map(test, SERIES_KEYS)
    for key, test_group in test_groups.items():
        train_group = train_groups.get(key)
        if train_group is None or train_group.empty:
            continue
        train_max = pd.to_datetime(train_group[TIMESTAMP], errors="coerce").max()
        test_min = pd.to_datetime(test_group[TIMESTAMP], errors="coerce").min()
        if not (test_min > train_max):
            raise AssertionError(
                f"Ряд {key}: min(test)={test_min} не строго позже max(train)={train_max}"
            )
