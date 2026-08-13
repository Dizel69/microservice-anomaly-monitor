"""Оркестрация ETL-конвейера: RAW -> PROCESSED -> UNIFIED -> признаки -> отчёты.

Конвейер реализует три уровня данных:

* **RAW**       — исходные данные источников без изменений;
* **PROCESSED** — данные после очистки и нормализации;
* **UNIFIED**   — единый набор данных + сформированный ML-набор признаков.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from etl.config import COMBINED_REPORT_KEY, DEFAULT_PATHS, PipelinePaths
from etl.features.feature_engineering import build_ml_dataset
from etl.logging_config import get_logger
from etl.schema import LABEL, LABEL_ANOMALY, SOURCE, UNIFIED_COLUMNS
from etl.storage import save_csv, save_parquet
from etl.transformers.normalize import normalize_dataframe
from etl.visualization.plots import generate_reports

logger = get_logger(__name__)


@dataclass
class LoadedSource:
    """Загруженный источник данных на уровне RAW."""

    name: str
    dataframe: pd.DataFrame


@dataclass
class PipelineResult:
    """Итоги выполнения конвейера."""

    files_processed: int
    total_rows: int
    sources: List[str]
    anomalies: int
    unified_parquet: Path
    unified_csv: Path
    features_parquet: Path
    features_csv: Path
    dataset_size_bytes: int
    # Отчёты сгруппированы по ключам: имя источника (NAB/KPI/PROMETHEUS) и
    # ``combined`` для общих графиков в корне каталога reports.
    report_paths: Dict[str, Dict[str, Path]] = field(default_factory=dict)
    rows_per_source: Dict[str, int] = field(default_factory=dict)

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def dataset_size_mb(self) -> float:
        return self.dataset_size_bytes / (1024 * 1024)


def _slugify(name: str) -> str:
    """Привести имя источника к безопасному имени файла."""

    slug = re.sub(r"[^0-9A-Za-z_.-]+", "_", name.strip())
    return slug.strip("_") or "source"


def _source_label(df: pd.DataFrame) -> str:
    """Определить источник (значение колонки ``source``) у кадра данных."""

    if SOURCE in df.columns and not df.empty:
        value = str(df[SOURCE].iloc[0]).strip()
        if value:
            return value
    return "UNKNOWN"


def run_pipeline(
    sources: List[LoadedSource],
    *,
    paths: PipelinePaths = DEFAULT_PATHS,
    make_visualizations: bool = True,
    files_processed: Optional[int] = None,
) -> PipelineResult:
    """Запустить полный ETL-конвейер.

    Args:
        sources: Список загруженных источников (RAW).
        paths: Конфигурация путей конвейера.
        make_visualizations: Строить ли графики-отчёты.
        files_processed: Количество обработанных входных файлов/запросов.
            Если ``None`` — берётся число источников.

    Returns:
        :class:`PipelineResult` со статистикой и путями к артефактам.

    Raises:
        ValueError: Если список источников пуст или нет валидных данных.
    """

    if not sources:
        raise ValueError("Не передано ни одного источника данных")

    paths.ensure()
    logger.info("=== Запуск ETL-конвейера: %d источник(ов) ===", len(sources))

    raw_frames: List[pd.DataFrame] = []
    processed_frames: List[pd.DataFrame] = []

    for source in sources:
        slug = _slugify(source.name)
        raw_df = source.dataframe
        src_label = _source_label(raw_df)

        # --- RAW: сохраняем как есть (в подкаталоге источника) ---
        raw_path = paths.raw_source_dir(src_label) / f"raw_{slug}.parquet"
        save_parquet(raw_df, raw_path)
        raw_frames.append(raw_df)

        # --- PROCESSED: очистка и нормализация (в подкаталоге источника) ---
        processed_df = normalize_dataframe(raw_df)
        processed_path = paths.processed_dir / src_label / f"processed_{slug}.parquet"
        save_parquet(processed_df, processed_path)
        processed_frames.append(processed_df)

    # Объединяем RAW (только общие колонки единого формата для визуализации).
    raw_combined = _concat_unified(raw_frames)
    processed_combined = (
        pd.concat(processed_frames, ignore_index=True)
        if processed_frames
        else pd.DataFrame(columns=UNIFIED_COLUMNS)
    )

    if processed_combined.empty:
        raise ValueError("После нормализации не осталось данных")

    # --- UNIFIED ---
    unified = processed_combined[UNIFIED_COLUMNS].reset_index(drop=True)
    unified_parquet = save_parquet(unified, paths.unified_parquet)
    unified_csv = save_csv(unified, paths.unified_csv)

    # --- Признаки / ML-набор ---
    ml_dataset = build_ml_dataset(unified)
    features_parquet = save_parquet(ml_dataset, paths.features_parquet)
    features_csv = save_csv(ml_dataset, paths.features_csv)

    # --- Визуализация ---
    report_paths: Dict[str, Dict[str, Path]] = {}
    if make_visualizations:
        report_paths = _generate_all_reports(
            raw_combined, unified, ml_dataset, paths
        )

    anomalies = int((unified[LABEL] == LABEL_ANOMALY).sum())
    rows_per_source = (
        unified[SOURCE].value_counts().sort_index().astype(int).to_dict()
    )
    dataset_size = unified_parquet.stat().st_size + features_parquet.stat().st_size

    result = PipelineResult(
        files_processed=files_processed if files_processed is not None else len(sources),
        total_rows=len(unified),
        sources=sorted(unified[SOURCE].unique().tolist()),
        anomalies=anomalies,
        unified_parquet=unified_parquet,
        unified_csv=unified_csv,
        features_parquet=features_parquet,
        features_csv=features_csv,
        dataset_size_bytes=dataset_size,
        report_paths=report_paths,
        rows_per_source=rows_per_source,
    )
    logger.info("=== ETL-конвейер завершён ===")
    return result


def _generate_all_reports(
    raw_combined: pd.DataFrame,
    unified: pd.DataFrame,
    ml_dataset: pd.DataFrame,
    paths: PipelinePaths,
) -> Dict[str, Dict[str, Path]]:
    """Построить отчёты по каждому источнику и общий (combined) отчёт.

    Для каждого источника графики сохраняются в ``reports/current/<SOURCE>/``,
    общие — в ``reports/current/combined/``. Снимок ``reports/before/``
    конвейер не трогает.
    """

    report_paths: Dict[str, Dict[str, Path]] = {}

    # Отчёты по каждому источнику отдельно.
    for src in sorted(unified[SOURCE].unique()):
        raw_sub = (
            raw_combined[raw_combined[SOURCE] == src]
            if SOURCE in raw_combined.columns
            else raw_combined
        )
        unified_sub = unified[unified[SOURCE] == src]
        ml_sub = ml_dataset[ml_dataset[SOURCE] == src]
        report_paths[src] = generate_reports(
            raw_sub, unified_sub, ml_sub, paths.reports_source_dir(src)
        )

    # Общий отчёт — в reports/current/combined/, не в корне current/.
    report_paths[COMBINED_REPORT_KEY] = generate_reports(
        raw_combined,
        unified,
        ml_dataset,
        paths.reports_source_dir(COMBINED_REPORT_KEY),
    )
    return report_paths


def _concat_unified(frames: List[pd.DataFrame]) -> pd.DataFrame:
    """Объединить кадры по колонкам единого формата (для визуализации RAW)."""

    prepared: List[pd.DataFrame] = []
    for frame in frames:
        cols = [c for c in UNIFIED_COLUMNS if c in frame.columns]
        if cols:
            prepared.append(frame[cols])
    if not prepared:
        return pd.DataFrame(columns=UNIFIED_COLUMNS)
    return pd.concat(prepared, ignore_index=True)
