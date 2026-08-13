"""Работа с официальными метками аномалий внешних наборов данных."""

from __future__ import annotations

__all__ = [
    "COMBINED_LABELS_FILE",
    "COMBINED_WINDOWS_FILE",
    "LABELS_DIRNAME",
    "NabWindowIndex",
    "find_nab_labels_dir",
    "label_series_by_windows",
    "load_nab_windows",
]

from etl.labels.nab_labels import (
    COMBINED_LABELS_FILE,
    COMBINED_WINDOWS_FILE,
    LABELS_DIRNAME,
    NabWindowIndex,
    find_nab_labels_dir,
    label_series_by_windows,
    load_nab_windows,
)
