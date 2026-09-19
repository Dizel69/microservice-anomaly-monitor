"""CLI ETL-конвейера подготовки данных для обнаружения аномалий.

Команды::

    # один файл, несколько файлов или каталог (сканируется рекурсивно)
    python main.py nab [пути ...]
    python main.py kpi [пути ...]
    python main.py zabbix [пути ...]

    # Prometheus: локальные дампы (включая live/**/*.parquet) без HTTP
    python main.py prometheus
    python main.py prometheus datasets/raw/PROMETHEUS/live/app_events.parquet

    # Prometheus: живой HTTP API (только если явно указан URL)
    python main.py prometheus http://185.28.85.183:9090 container_cpu_usage_seconds_total

    # общий запуск: NAB + KPI + локальные дампы Prometheus/Zabbix (без HTTP)
    python main.py all

Если для ``nab``/``kpi``/``zabbix`` не указать пути, сканируются каталоги
по умолчанию (``datasets/raw/NAB``, ``KPI``, ``ZABBIX``), включая вложенные
папки. Для ``prometheus`` без URL — ``datasets/raw/PROMETHEUS`` рекурсивно
(live/ тоже). Все parquet одного источника склеиваются в один кадр, чтобы
не строить сотни отдельных отчётов.

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

import pandas as pd

from etl.config import (
    DEFAULT_PATHS,
    RAW_KPI_DIR,
    RAW_NAB_DIR,
    RAW_PROMETHEUS_DIR,
    RAW_ZABBIX_DIR,
)
from etl.discovery import collect_csv_files, collect_dump_files
from etl.labels.nab_labels import (
    NabWindowIndex,
    find_nab_labels_dir,
    load_nab_windows,
)
from etl.loaders import (
    load_kpi,
    load_nab,
    load_prometheus,
    load_prometheus_dump,
    load_zabbix_dump,
)
from etl.logging_config import configure_logging, get_logger
from etl.pipeline import LoadedSource, PipelineResult, run_pipeline

logger = get_logger("etl.main")


def build_parser() -> argparse.ArgumentParser:
    """Сконфигурировать парсер аргументов командной строки."""

    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "ETL-конвейер: загрузка источников (NAB/KPI/Prometheus/Zabbix), нормализация, "
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

    zabbix = subparsers.add_parser(
        "zabbix",
        help="Загрузить Zabbix: parquet/csv (по умолчанию datasets/raw/ZABBIX).",
    )
    zabbix.add_argument(
        "paths",
        nargs="*",
        type=str,
        help="Пути к parquet/csv или каталогам (файлы .dump пропускаются).",
    )

    prom = subparsers.add_parser(
        "prometheus",
        help=(
            "Локальные дампы Prometheus (без аргументов) либо HTTP: "
            "URL и PromQL-запросы."
        ),
    )
    prom.add_argument(
        "targets",
        nargs="*",
        type=str,
        help=(
            "Пути к parquet/csv (локальный режим) либо URL Prometheus и "
            "один или несколько PromQL-запросов."
        ),
    )
    _add_prom_options(prom)

    allcmd = subparsers.add_parser(
        "all", help="Общий запуск по источникам -> единый ML-набор."
    )
    allcmd.add_argument(
        "--nab", nargs="*", type=str, default=None,
        help="Пути NAB (по умолчанию datasets/raw/NAB).",
    )
    allcmd.add_argument(
        "--kpi", nargs="*", type=str, default=None,
        help="Пути KPI (по умолчанию datasets/raw/KPI).",
    )
    allcmd.add_argument(
        "--zabbix", nargs="*", type=str, default=None,
        help="Пути Zabbix parquet (по умолчанию datasets/raw/ZABBIX).",
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


def _looks_like_url(text: str) -> bool:
    """Отличить живой URL Prometheus от пути к локальному дампу."""

    lowered = text.strip().lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _concat_loaded_dumps(frames: List[pd.DataFrame]) -> pd.DataFrame:
    """Склеить загруженные дампы в один кадр (один source → один отчёт)."""

    nonempty = [frame for frame in frames if frame is not None and not frame.empty]
    if not nonempty:
        return pd.DataFrame()
    return pd.concat(nonempty, ignore_index=True)


def _prometheus_dump_files(directory: Path) -> List[Path]:
    """Найти локальные дампы Prometheus (parquet/csv) рекурсивно, без *_bucket/_created."""

    if not directory.exists():
        return []
    return collect_dump_files([directory], skip_histogram_remnants=True)


def _prometheus_local_sources(
    path_args: Optional[List[str]] = None,
) -> List[LoadedSource]:
    """Загрузить дампы из datasets/raw/PROMETHEUS (включая live/) без HTTP.

    Все найденные файлы читаются по одному (qualify_metric_names — внутри файла,
    префикс ``job__`` в имени файла не трогает колонки) и склеиваются в один
    LoadedSource, чтобы конвейер не строил сотни графиков.
    """

    if path_args:
        files = collect_dump_files(path_args, skip_histogram_remnants=True)
    else:
        files = _prometheus_dump_files(RAW_PROMETHEUS_DIR)

    if not files:
        logger.warning("PROMETHEUS: локальные дампы не найдены в %s", RAW_PROMETHEUS_DIR)
        return []

    frames: List[pd.DataFrame] = []
    for file_path in files:
        frames.append(load_prometheus_dump(file_path))
    combined = _concat_loaded_dumps(frames)
    if combined.empty:
        logger.warning("PROMETHEUS: дампы прочитаны, но строк нет")
        return []

    logger.info(
        "PROMETHEUS: склеено %d точек из %d дампов в один источник",
        len(combined),
        len(files),
    )
    return [
        LoadedSource(
            name="prometheus",
            dataframe=combined,
            persist_raw=False,
        )
    ]


def _zabbix_sources(path_args: Optional[List[str]] = None) -> List[LoadedSource]:
    """Собрать parquet/csv Zabbix (не .dump) в один источник."""

    targets = path_args if path_args else [RAW_ZABBIX_DIR]
    files = collect_dump_files(targets, skip_histogram_remnants=False)
    if not files:
        logger.warning("ZABBIX: не найдено parquet/csv в %s", targets)
        return []

    frames: List[pd.DataFrame] = []
    for file_path in files:
        frames.append(load_zabbix_dump(file_path))
    combined = _concat_loaded_dumps(frames)
    if combined.empty:
        logger.warning("ZABBIX: дампы прочитаны, но строк нет")
        return []

    logger.info(
        "ZABBIX: склеено %d точек из %d дампов в один источник",
        len(combined),
        len(files),
    )
    return [
        LoadedSource(
            name="zabbix",
            dataframe=combined,
            persist_raw=False,
        )
    ]


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
        targets = list(args.targets or [])
        if targets and _looks_like_url(targets[0]):
            queries = targets[1:]
            if not queries:
                logger.error("Для HTTP-режима Prometheus укажите хотя бы один PromQL-запрос")
                return [], 0
            sources = _prometheus_sources(
                targets[0], queries, args.step, args.range_seconds
            )
            return sources, len(sources)
        local = _prometheus_local_sources(targets or None)
        return local, len(local)

    if args.command == "zabbix":
        sources = _zabbix_sources(args.paths)
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
        sources += _zabbix_sources(args.zabbix)
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
