"""Общие фикстуры тестов ETL-конвейера."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, List

import pandas as pd
import pytest

from etl.config import RAW_KPI_DIR, RAW_NAB_DIR, RAW_PROMETHEUS_DIR
from etl.labels.nab_labels import COMBINED_WINDOWS_FILE, LABELS_DIRNAME

#: Окно аномалии, используемое синтетическими фикстурами NAB.
WINDOW_START = "2014-04-10 12:00:00"
WINDOW_END = "2014-04-10 14:00:00"


@pytest.fixture
def nab_dataset(tmp_path: Path) -> Callable[..., Path]:
    """Фабрика мини-набора NAB: CSV-ряд + ``labels/combined_windows.json``.

    Возвращает функцию ``make(category, name, timestamps, windows)``,
    создающую файл данных и файл меток и отдающую путь к CSV-ряду.
    """

    def make(
        category: str = "realKnownCause",
        name: str = "nyc_taxi",
        timestamps: List[str] | None = None,
        windows: List[List[str]] | None = None,
    ) -> Path:
        stamps = timestamps or [
            "2014-04-10 11:00:00",  # до окна
            "2014-04-10 12:00:00",  # граница окна (включительно)
            "2014-04-10 13:00:00",  # внутри окна
            "2014-04-10 14:00:00",  # граница окна (включительно)
            "2014-04-10 15:00:00",  # после окна
        ]
        csv_path = tmp_path / "data" / category / f"{name}.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            {"timestamp": stamps, "value": [float(i) for i in range(len(stamps))]}
        ).to_csv(csv_path, index=False)

        labels_path = tmp_path / "data" / LABELS_DIRNAME / COMBINED_WINDOWS_FILE
        labels_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            f"{category}/{name}.csv": (
                windows if windows is not None else [[WINDOW_START, WINDOW_END]]
            )
        }
        labels_path.write_text(json.dumps(payload), encoding="utf-8")
        return csv_path

    return make


@pytest.fixture
def kpi_csv(tmp_path: Path) -> Callable[..., Path]:
    """Фабрика мини-файла KPI (``timestamp,value,label,KPI ID``)."""

    def make(name: str = "phase2_train.csv", rows: int = 6) -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(
            {
                "timestamp": [1476460800 + 60 * i for i in range(rows)],
                "value": [0.1 * i for i in range(rows)],
                "label": [0] * (rows - 1) + [1],
                "KPI ID": ["da10a69f-d836-3baa-ad40-3e548ecf1fbd"] * rows,
            }
        )
        compression = "gzip" if name.endswith(".gz") else None
        frame.to_csv(path, index=False, compression=compression)
        return path

    return make


def _first_existing(paths: List[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


@pytest.fixture(scope="session")
def real_nab_windows_path() -> Path:
    """Путь к скачанному ``combined_windows.json`` (иначе тест пропускается)."""

    path = RAW_NAB_DIR / LABELS_DIRNAME / COMBINED_WINDOWS_FILE
    if not path.is_file():
        pytest.skip(
            "Нет файла меток NAB: запустите 'python scripts/fetch_nab.py --labels-only'"
        )
    return path


@pytest.fixture(scope="session")
def real_prometheus_dump() -> Path:
    """Путь к локальному дампу Prometheus (иначе тест пропускается)."""

    dumps = sorted(RAW_PROMETHEUS_DIR.glob("*.parquet"))
    if not dumps:
        pytest.skip("Нет локальных дампов Prometheus в datasets/raw/PROMETHEUS")
    return dumps[0]


@pytest.fixture(scope="session")
def real_kpi_file() -> Path:
    """Путь к реальному файлу KPI (иначе тест пропускается)."""

    path = _first_existing(
        [
            RAW_KPI_DIR / "phase2_train.csv.gz",
            RAW_KPI_DIR / "phase2_train.csv",
            RAW_KPI_DIR / "phase2_ground_truth.csv.gz",
        ]
    )
    if path is None:
        pytest.skip("Нет файлов KPI в datasets/raw/KPI")
    return path
