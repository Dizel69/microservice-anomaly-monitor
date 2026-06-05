"""CLI ETL-конвейера подготовки данных для обнаружения аномалий.

Команды::

    # один файл, несколько файлов или каталог (сканируется рекурсивно)
    python main.py nab [пути ...]
    python main.py kpi [пути ...]
    python main.py prometheus http://185.28.85.183:9090 container_cpu_usage_seconds_total

    # общий запуск сразу по трём источникам -> один большой ML-набор
    python main.py all --prom-url http://185.28.85.183:9090 --prom-query node_cpu_seconds_total

Если для ``nab``/``kpi`` не указать пути, сканируются каталоги по умолчанию
(``datasets/raw/NAB`` и ``datasets/raw/KPI`` соответственно), включая вложенные
папки.

Конвейер реализует три уровня данных (RAW -> PROCESSED -> UNIFIED), формирует
ML-набор признаков, сохраняет результаты в Apache Parquet (+ CSV-экспорт) и
строит графики-отчёты по каждому источнику и общий отчёт в ``datasets/reports``.
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
)
from etl.discovery import collect_csv_files
from etl.loaders import load_kpi, load_nab, load_prometheus
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


def _nab_sources(path_args: Optional[List[str]]) -> List[LoadedSource]:
    """Собрать источники NAB из файлов/каталогов (или каталога по умолчанию)."""

    targets = path_args if path_args else [RAW_NAB_DIR]
    files = collect_csv_files(targets)
    if not files:
        logger.warning("NAB: не найдено CSV-файлов в %s", targets)
    return [LoadedSource(name=f.stem, dataframe=load_nab(f)) for f in files]


def _kpi_sources(path_args: Optional[List[str]]) -> List[LoadedSource]:
    """Собрать источники KPI из файлов/каталогов (или каталога по умолчанию)."""

    targets = path_args if path_args else [RAW_KPI_DIR]
    files = collect_csv_files(targets)
    if not files:
        logger.warning("KPI: не найдено CSV-файлов в %s", targets)
    return [LoadedSource(name=f.stem, dataframe=load_kpi(f)) for f in files]


def _prometheus_sources(
    url: Optional[str],
    queries: Optional[List[str]],
    step_seconds: int,
    range_seconds: int,
) -> List[LoadedSource]:
    """Собрать источники Prometheus по списку PromQL-запросов."""

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
        sources += _prometheus_sources(
            args.prom_url, args.prom_query, args.step, args.range_seconds
        )
        if not args.prom_url or not args.prom_query:
            logger.info("ALL: Prometheus пропущен (не заданы --prom-url/--prom-query)")
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
