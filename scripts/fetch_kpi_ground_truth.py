"""Догрузка тестовой части набора KPI с эталонной разметкой.

Соревнование KPI Anomaly Detection (NetManAIOps) публикует тестовую выборку
с ответами в виде HDF-архива ``Finals_dataset/phase2_ground_truth.hdf.zip``.
Скрипт скачивает архив, распаковывает его во временный каталог и сохраняет
данные как ``datasets/raw/KPI/phase2_ground_truth.csv.gz``.

Формат сохраняемого CSV совпадает с ``phase2_train.csv``
(``timestamp,value,label,KPI ID``), поэтому файл подхватывается обычным
загрузчиком KPI и попадает в общий конвейер как ``source = KPI``.
Сжатый CSV (~16 МБ) укладывается в лимит GitHub на размер файла, тогда как
исходный HDF (~100 МБ) — нет.

Запуск::

    python scripts/fetch_kpi_ground_truth.py
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.config import RAW_KPI_DIR  # noqa: E402
from etl.logging_config import configure_logging, get_logger  # noqa: E402

logger = get_logger("etl.scripts.fetch_kpi_ground_truth")

GROUND_TRUTH_URL = (
    "https://raw.githubusercontent.com/NetManAIOps/KPI-Anomaly-Detection"
    "/master/Finals_dataset/phase2_ground_truth.hdf.zip"
)
GROUND_TRUTH_CSV = "phase2_ground_truth.csv.gz"
HTTP_TIMEOUT = 600

#: Порядок колонок как в phase2_train.csv.
_COLUMNS: List[str] = ["timestamp", "value", "label", "KPI ID"]


def fetch_ground_truth(kpi_dir: Path = RAW_KPI_DIR) -> Path:
    """Скачать и сохранить тестовую выборку KPI с метками.

    Returns:
        Путь к сохранённому ``phase2_ground_truth.csv.gz``.

    Raises:
        RuntimeError: При ошибке скачивания или распаковки.
    """

    kpi_dir.mkdir(parents=True, exist_ok=True)
    destination = kpi_dir / GROUND_TRUTH_CSV

    with tempfile.TemporaryDirectory(prefix="kpi_gt_") as tmp_name:
        tmp_dir = Path(tmp_name)
        archive = tmp_dir / "phase2_ground_truth.hdf.zip"

        logger.info("Скачивание %s", GROUND_TRUTH_URL)
        try:
            with urllib.request.urlopen(GROUND_TRUTH_URL, timeout=HTTP_TIMEOUT) as resp:
                with archive.open("wb") as handle:
                    shutil.copyfileobj(resp, handle)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Не удалось скачать {GROUND_TRUTH_URL}: {exc}") from exc

        logger.info("Распаковка %s", archive)
        try:
            with zipfile.ZipFile(archive) as zf:
                members = [n for n in zf.namelist() if n.lower().endswith(".hdf")]
                if not members:
                    raise RuntimeError("В архиве нет HDF-файла с разметкой")
                zf.extract(members[0], tmp_dir)
                hdf_path = tmp_dir / members[0]
        except zipfile.BadZipFile as exc:
            raise RuntimeError(f"Повреждённый архив {archive}: {exc}") from exc

        logger.info("Чтение %s", hdf_path)
        try:
            frame = pd.read_hdf(hdf_path)
        except ImportError as exc:
            raise RuntimeError(
                "Для чтения HDF нужен пакет 'tables': pip install tables"
            ) from exc

    if not isinstance(frame, pd.DataFrame):
        raise RuntimeError(f"Ожидался DataFrame, получено {type(frame)!r}")

    missing = [col for col in _COLUMNS if col not in frame.columns]
    if missing:
        raise RuntimeError(f"В эталонной разметке нет колонок {missing}")

    frame = frame[_COLUMNS].sort_values(["KPI ID", "timestamp"]).reset_index(drop=True)
    frame.to_csv(destination, index=False, compression="gzip")

    size_mb = destination.stat().st_size / (1024 * 1024)
    logger.info(
        "Сохранено %s: %d строк, %d рядов, аномалий %d (%.1f МБ)",
        destination,
        len(frame),
        frame["KPI ID"].nunique(),
        int((frame["label"] == 1).sum()),
        size_mb,
    )
    return destination


def main() -> int:
    configure_logging()
    try:
        fetch_ground_truth()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
