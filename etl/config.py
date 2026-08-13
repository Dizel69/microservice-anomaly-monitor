"""Конфигурация путей ETL-конвейера.

Описывает три уровня данных (RAW / PROCESSED / UNIFIED) и каталог отчётов.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from etl.schema import SOURCE_KPI, SOURCE_NAB, SOURCE_PROMETHEUS

#: Корень проекта (каталог, содержащий пакет ``etl``).
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

DATASETS_DIR: Path = PROJECT_ROOT / "datasets"
RAW_DIR: Path = DATASETS_DIR / "raw"
PROCESSED_DIR: Path = DATASETS_DIR / "processed"
UNIFIED_DIR: Path = DATASETS_DIR / "unified"

#: Графики вынесены в корень репозитория (не внутрь datasets/).
#: ``before`` — снимок для выступления, конвейер его не перезаписывает.
#: ``current`` — актуальные графики после новых прогонов ETL.
REPORTS_ROOT: Path = PROJECT_ROOT / "reports"
REPORTS_BEFORE_DIR: Path = REPORTS_ROOT / "before"
REPORTS_DIR: Path = REPORTS_ROOT / "current"

#: Подкаталоги исходных данных по источникам. Сюда пользователь складывает
#: готовые датасеты (файлы и/или вложенные папки сканируются рекурсивно).
RAW_NAB_DIR: Path = RAW_DIR / SOURCE_NAB
RAW_KPI_DIR: Path = RAW_DIR / SOURCE_KPI
RAW_PROMETHEUS_DIR: Path = RAW_DIR / SOURCE_PROMETHEUS

#: Соответствие «источник -> каталог исходных данных».
RAW_SOURCE_DIRS: Dict[str, Path] = {
    SOURCE_NAB: RAW_NAB_DIR,
    SOURCE_KPI: RAW_KPI_DIR,
    SOURCE_PROMETHEUS: RAW_PROMETHEUS_DIR,
}

#: Базовые имена итоговых артефактов.
UNIFIED_BASENAME: str = "unified_dataset"
FEATURES_BASENAME: str = "ml_dataset"

#: Ключ корневого («общего») набора отчётов.
COMBINED_REPORT_KEY: str = "combined"


@dataclass(frozen=True)
class PipelinePaths:
    """Набор путей, используемых конвейером."""

    raw_dir: Path = RAW_DIR
    processed_dir: Path = PROCESSED_DIR
    unified_dir: Path = UNIFIED_DIR
    reports_dir: Path = REPORTS_DIR
    extra_dirs: tuple[Path, ...] = field(default_factory=tuple)

    def ensure(self) -> None:
        """Создать все необходимые каталоги, если они отсутствуют."""

        source_dirs = (
            self.raw_dir / SOURCE_NAB,
            self.raw_dir / SOURCE_KPI,
            self.raw_dir / SOURCE_PROMETHEUS,
        )
        for directory in (
            self.raw_dir,
            *source_dirs,
            self.processed_dir,
            self.unified_dir,
            self.reports_dir,
            self.reports_dir / COMBINED_REPORT_KEY,
            *self.extra_dirs,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def raw_source_dir(self, source: str) -> Path:
        """Каталог исходных данных конкретного источника (``NAB``/``KPI``/...)."""

        return self.raw_dir / source

    def reports_source_dir(self, source: str) -> Path:
        """Каталог отчётов конкретного источника (``NAB`` / ``KPI`` / ``combined``)."""

        return self.reports_dir / source

    @property
    def unified_parquet(self) -> Path:
        return self.unified_dir / f"{UNIFIED_BASENAME}.parquet"

    @property
    def unified_csv(self) -> Path:
        return self.unified_dir / f"{UNIFIED_BASENAME}.csv"

    @property
    def features_parquet(self) -> Path:
        return self.unified_dir / f"{FEATURES_BASENAME}.parquet"

    @property
    def features_csv(self) -> Path:
        return self.unified_dir / f"{FEATURES_BASENAME}.csv"


DEFAULT_PATHS = PipelinePaths()
