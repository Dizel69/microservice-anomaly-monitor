"""CLI ETL-конвейера подготовки данных для обнаружения аномалий.

Команды::

    # один файл, несколько файлов или каталог (сканируется рекурсивно)
    python main.py nab [пути ...]
    python main.py kpi [пути ...]
    python main.py prometheus http://185.28.85.183:9090 container_cpu_usage_seconds_total

    # общий запуск: NAB + KPI + локальные дампы Prometheus (без HTTP)
    python main.py all

Если для ``nab``/``kpi`` не указать пути, сканируются каталоги по умолчанию
(``datasets/raw/NAB`` и ``datasets/raw/KPI`` соответственно), включая вложенные
папки.

Конвейер реализует три уровня данных (RAW -> PROCESSED -> UNIFIED), формирует
ML-набор признаков, сохраняет результаты в Apache Parquet (+ CSV-экспорт) и
строит графики-отчёты в ``reports/current/`` (снимок ``reports/before/`` не перезаписывается).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from etl.config import (
    DEFAULT_PATHS,
    RAW_KPI_DIR,
    RAW_NAB_DIR,
    RAW_PROMETHEUS_DIR,
)
from etl.discovery import collect_csv_files
from etl.labels.nab_labels import (
    NabWindowIndex,
    find_nab_labels_dir,
    load_nab_windows,
)
from etl.loaders import load_kpi, load_nab, load_prometheus, load_prometheus_dump
from etl.logging_config import configure_logging, get_logger
from etl.pipeline import LoadedSource, PipelineResult, run_pipeline

logger = get_logger("etl.main")


def build_parser() -> argparse.ArgumentParser:
    """Сконфигурировать парсер аргументов командной строки."""

    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "ETL-конвейер: загрузка источников (NAB/KPI/Prometheus), нормализация, "
            "инженерия признаков, экспорт (Parquet/CSV) и визуализация."
        ),
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Подробное логирование (DEBUG)."
    )
    parser.add_argument(
        "--no-viz", action="store_true", help="Не строить графики-отчёты."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    nab = subparsers.add_parser(
        "nab", help="Загрузить NAB: файлы/каталоги (по умолчанию datasets/raw/NAB)."
    )
    nab.add_argument(
        "paths", nargs="*", type=str, help="Пути к CSV-файлам или каталогам NAB."
    )

    kpi = subparsers.add_parser(
        "kpi", help="Загрузить KPI: файлы/каталоги (по умолчанию datasets/raw/KPI)."
    )
    kpi.add_argument(
        "paths", nargs="*", type=str, help="Пути к CSV-файлам или каталогам KPI."
    )

    prom = subparsers.add_parser(
        "prometheus", help="Выгрузить временные ряды из Prometheus HTTP API."
    )
    prom.add_argument("url", type=str, help="Базовый URL Prometheus.")
    prom.add_argument(
        "queries", nargs="+", type=str, help="Один или несколько PromQL-запросов."
    )
    _add_prom_options(prom)

    allcmd = subparsers.add_parser(
        "all", help="Общий запуск по трём источникам -> единый ML-набор."
    )
    allcmd.add_argument(
        "--nab", nargs="*", type=str, default=None,
        help="Пути NAB (по умолчанию datasets/raw/NAB).",
    )
    allcmd.add_argument(
        "--kpi", nargs="*", type=str, default=None,
        help="Пути KPI (по умолчанию datasets/raw/KPI).",
    )
    allcmd.add_argument("--prom-url", type=str, default=None, help="URL Prometheus.")
    allcmd.add_argument(
        "--prom-query", nargs="*", type=str, default=None, help="PromQL-запросы."
    )
    _add_prom_options(allcmd)

    return parser


def _add_prom_options(p: argparse.ArgumentParser) -> None:
    """Добавить общие опции Prometheus к субпарсеру."""

    p.add_argument(
        "--step", type=int, default=15,
        help="Шаг дискретизации query_range в секундах (по умолчанию 15).",
    )
    p.add_argument(
        "--range", type=int, default=3600, dest="range_seconds",
        help="Длина временного диапазона в секундах (по умолчанию 3600).",
    )


def _load_nab_window_index(files: List[Path]) -> Optional[NabWindowIndex]:
    """Загрузить индекс окон аномалий NAB один раз на весь прогон.

    Файл ``labels/combined_windows.json`` ищется рядом с данными: сначала в
    каталоге NAB по умолчанию, затем вверх по дереву от первого CSV-файла.
    """

    for candidate in (RAW_NAB_DIR, *(f for f in files[:1])):
        labels_dir = find_nab_labels_dir(candidate)
        if labels_dir is None:
            continue
        try:
            return load_nab_windows(labels_dir)
        except (FileNotFoundError, ValueError) as exc:
            logger.warning("NAB: не удалось загрузить окна аномалий: %s", exc)
            return None

    logger.warning(
        "NAB: файл окон аномалий не найден. Скачайте его командой "
        "'python scripts/fetch_nab.py --labels-only', иначе все точки "
        "получат label=0."
    )
    return None


def _nab_sources(path_args: Optional[List[str]]) -> List[LoadedSource]:
    """Собрать источники NAB из файлов/каталогов (или каталога по умолчанию)."""

    targets = path_args if path_args else [RAW_NAB_DIR]
    files = collect_csv_files(targets)
    if not files:
        logger.warning("NAB: не найдено CSV-файлов в %s", targets)
        return []

    windows = _load_nab_window_index(files)
    return [
        LoadedSource(
            name=f.stem, dataframe=load_nab(f, windows=windows), source_path=f
        )
        for f in files
    ]


def _kpi_sources(path_args: Optional[List[str]]) -> List[LoadedSource]:
    """Собрать источники KPI из файлов/каталогов (или каталога по умолчанию)."""

    targets = path_args if path_args else [RAW_KPI_DIR]
    files = collect_csv_files(targets)
    if not files:
        logger.warning("KPI: не найдено CSV-файлов в %s", targets)
    return [
        LoadedSource(name=f.stem, dataframe=load_kpi(f), source_path=f)
        for f in files
    ]


def _prometheus_dump_files(directory: Path) -> List[Path]:
    """Найти локальные дампы Prometheus (parquet/csv) в каталоге."""

    if not directory.is_dir():
        return []
    files = sorted(
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in {".parquet", ".csv"}
    )
    return files


def _prometheus_local_sources(
    path_args: Optional[List[str]] = None,
) -> List[LoadedSource]:
    """Загрузить ранее скачанные дампы из datasets/raw/PROMETHEUS (без HTTP)."""

    if path_args:
        files: List[Path] = []
        for raw in path_args:
            target = Path(raw)
            if target.is_file():
                files.append(target)
            elif target.is_dir():
                files.extend(_prometheus_dump_files(target))
    else:
        files = _prometheus_dump_files(RAW_PROMETHEUS_DIR)

    if not files:
        logger.warning("PROMETHEUS: локальные дампы не найдены в %s", RAW_PROMETHEUS_DIR)
        return []

    sources: List[LoadedSource] = []
    for file_path in files:
        df = load_prometheus_dump(file_path)
        name = file_path.stem
        if name.startswith("raw_"):
            name = name[len("raw_") :]
        sources.append(
            LoadedSource(name=name, dataframe=df, source_path=file_path)
        )
    logger.info("PROMETHEUS: загружено %d локальных дампов", len(sources))
    return sources


def _prometheus_sources(
    url: Optional[str],
    queries: Optional[List[str]],
    step_seconds: int,
    range_seconds: int,
) -> List[LoadedSource]:
    """Собрать источники Prometheus по списку PromQL-запросов (живой API)."""

    if not url or not queries:
        return []
    sources: List[LoadedSource] = []
    for query in queries:
        df = load_prometheus(
            url, query, step_seconds=step_seconds, range_seconds=range_seconds
        )
        sources.append(LoadedSource(name=f"prometheus_{query}", dataframe=df))
    return sources


def collect_sources(args: argparse.Namespace) -> tuple[List[LoadedSource], int]:
    """Загрузить источники согласно выбранной команде.

    Returns:
        Кортеж ``(список источников, число обработанных входов)``.
    """

    if args.command == "nab":
        sources = _nab_sources(args.paths)
        return sources, len(sources)

    if args.command == "kpi":
        sources = _kpi_sources(args.paths)
        return sources, len(sources)

    if args.command == "prometheus":
        sources = _prometheus_sources(
            args.url, args.queries, args.step, args.range_seconds
        )
        return sources, len(sources)

    if args.command == "all":
        sources: List[LoadedSource] = []
        sources += _nab_sources(args.nab)
        sources += _kpi_sources(args.kpi)
        if args.prom_url and args.prom_query:
            sources += _prometheus_sources(
                args.prom_url, args.prom_query, args.step, args.range_seconds
            )
        else:
            local = _prometheus_local_sources()
            sources += local
            if local:
                logger.info(
                    "ALL: Prometheus из локальных дампов %s (живой API не вызывается)",
                    RAW_PROMETHEUS_DIR,
                )
            else:
                logger.info(
                    "ALL: Prometheus пропущен (нет дампов в %s и не заданы --prom-url/--prom-query)",
                    RAW_PROMETHEUS_DIR,
                )
        return sources, len(sources)

    raise ValueError(f"Неизвестная команда: {args.command}")


def print_summary(result: PipelineResult) -> None:
    """Вывести итоговый отчёт в консоль."""

    lines = [
        "",
        "=" * 60,
        "ИТОГИ ВЫПОЛНЕНИЯ ETL-КОНВЕЙЕРА",
        "=" * 60,
        f"Обработано файлов/запросов : {result.files_processed}",
        f"Количество строк           : {result.total_rows}",
        f"Количество источников      : {result.source_count} "
        f"({', '.join(result.sources)})",
        f"Количество аномалий        : {result.anomalies}",
        f"Размер итогового датасета  : {result.dataset_size_mb:.3f} МБ "
        f"({result.dataset_size_bytes} байт)",
        "",
        "Строк по источникам:",
    ]
    for source, rows in result.rows_per_source.items():
        lines.append(f"  - {source:<12}: {rows}")

    lines.append("")
    lines.append("Артефакты:")
    lines.append(f"  - UNIFIED (parquet) : {result.unified_parquet}")
    lines.append(f"  - UNIFIED (csv)     : {result.unified_csv}")
    lines.append(f"  - ML-набор (parquet): {result.features_parquet}")
    lines.append(f"  - ML-набор (csv)    : {result.features_csv}")

    if result.report_paths:
        lines.append("")
        lines.append("Графики (reports):")
        for group, paths in result.report_paths.items():
            lines.append(f"  [{group}]")
            for key, path in paths.items():
                lines.append(f"    - {key:<10}: {path}")

    lines.append("=" * 60)
    print("\n".join(lines))


def main(argv: Optional[List[str]] = None) -> int:
    """Точка входа CLI.

    Returns:
        Код возврата процесса (0 — успех, 1 — ошибка).
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(logging.DEBUG if args.verbose else logging.INFO)

    try:
        logger.info("Запуск ETL: команда '%s'", args.command)
        sources, files_processed = collect_sources(args)
        if not sources:
            logger.error("Нет данных для обработки. Проверьте пути/аргументы.")
            return 1
        result = run_pipeline(
            sources,
            paths=DEFAULT_PATHS,
            make_visualizations=not args.no_viz,
            files_processed=files_processed,
        )
    except FileNotFoundError as exc:
        logger.error("Файл не найден: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001 - финальный барьер CLI
        logger.error("Ошибка выполнения ETL: %s", exc)
        return 1

    print_summary(result)
    logger.info("Готово.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
