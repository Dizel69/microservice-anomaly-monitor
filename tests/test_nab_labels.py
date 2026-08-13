"""Разметка NAB по официальным окнам аномалий."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from etl.labels.nab_labels import (
    find_nab_labels_dir,
    label_series_by_windows,
    load_nab_windows,
)
from etl.loaders import load_nab
from etl.schema import LABEL, SOURCE, SOURCE_NAB, TIMESTAMP

#: Границы окна, которое ставит фикстура ``nab_dataset``.
WINDOW_START = "2014-04-10 12:00:00"
WINDOW_END = "2014-04-10 14:00:00"


def test_timestamp_inside_window_gets_label_one(nab_dataset) -> None:
    """Точка внутри окна аномалии получает label=1, вне окна — label=0."""

    csv_path = nab_dataset()
    frame = load_nab(csv_path)

    labels = dict(zip(frame[TIMESTAMP], frame[LABEL]))
    inside = pd.Timestamp("2014-04-10 13:00:00")
    before = pd.Timestamp("2014-04-10 11:00:00")
    after = pd.Timestamp("2014-04-10 15:00:00")

    assert labels[inside] == 1
    assert labels[before] == 0
    assert labels[after] == 0
    assert frame[LABEL].sum() == 3  # включая обе границы окна


def test_window_boundaries_are_inclusive(nab_dataset) -> None:
    """Границы окна считаются аномальными."""

    frame = load_nab(nab_dataset())
    labels = dict(zip(frame[TIMESTAMP], frame[LABEL]))

    assert labels[pd.Timestamp(WINDOW_START)] == 1
    assert labels[pd.Timestamp(WINDOW_END)] == 1


def test_series_without_windows_is_all_zero(nab_dataset) -> None:
    """Ряд с пустым списком окон размечается нулями (это тоже разметка)."""

    csv_path = nab_dataset(
        category="artificialNoAnomaly", name="art_daily_no_noise", windows=[]
    )
    frame = load_nab(csv_path)

    assert frame[LABEL].tolist() == [0] * len(frame)
    assert frame[SOURCE].unique().tolist() == [SOURCE_NAB]


def test_multiple_windows_are_applied(nab_dataset) -> None:
    """Все окна ряда применяются, а не только первое."""

    csv_path = nab_dataset(
        timestamps=[
            "2014-04-10 11:00:00",
            "2014-04-10 13:00:00",
            "2014-04-10 18:00:00",
            "2014-04-10 21:00:00",
        ],
        windows=[
            ["2014-04-10 12:00:00", "2014-04-10 14:00:00"],
            ["2014-04-10 20:00:00", "2014-04-10 22:00:00"],
        ],
    )
    frame = load_nab(csv_path)

    assert frame[LABEL].tolist() == [0, 1, 0, 1]


def test_category_directory_name_may_differ_from_official(nab_dataset) -> None:
    """Окна находятся по имени файла, даже если каталог назван короче."""

    csv_path = nab_dataset(category="realKnownCause", name="nyc_taxi")
    renamed = csv_path.parent.parent / "KnownCause" / csv_path.name
    renamed.parent.mkdir(parents=True, exist_ok=True)
    csv_path.rename(renamed)

    frame = load_nab(renamed)

    assert frame[LABEL].sum() == 3


def test_missing_labels_file_is_reported_not_silently_zero(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Без файла окон загрузчик предупреждает, а не молча ставит нули."""

    csv_path = tmp_path / "orphan" / "nyc_taxi.csv"
    csv_path.parent.mkdir(parents=True)
    pd.DataFrame(
        {"timestamp": ["2014-04-10 13:00:00"], "value": [1.0]}
    ).to_csv(csv_path, index=False)

    with caplog.at_level("WARNING"):
        frame = load_nab(csv_path)

    assert frame[LABEL].tolist() == [0]
    assert any("окна аномалий" in record.message for record in caplog.records)


def test_label_series_by_windows_handles_unparsable_times() -> None:
    """Непарсируемое время не попадает в аномалии и не роняет разметку."""

    stamps = pd.Series(["2014-04-10 13:00:00", "не дата"])
    labels = label_series_by_windows(
        stamps, [(pd.Timestamp(WINDOW_START), pd.Timestamp(WINDOW_END))]
    )

    assert labels.tolist() == [1, 0]


def test_find_labels_dir_walks_up_from_csv(nab_dataset) -> None:
    """Каталог меток ищется вверх по дереву от файла данных."""

    csv_path = nab_dataset()
    labels_dir = find_nab_labels_dir(csv_path)

    assert labels_dir is not None
    assert (labels_dir / "combined_windows.json").is_file()


def test_real_windows_file_covers_official_58_series(
    real_nab_windows_path: Path,
) -> None:
    """Скачанный файл меток описывает полный официальный состав NAB."""

    index = load_nab_windows(real_nab_windows_path)
    payload = json.loads(real_nab_windows_path.read_text(encoding="utf-8"))

    assert len(index) == 58
    assert len(payload) == 58
    assert index.series_with_anomalies > 0
