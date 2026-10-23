"""CLI: ``python -m ml smoke-nab`` и ``python -m ml compare``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from etl.logging_config import configure_logging
from ml.compare import KPI_IDS_NAME, SUMMARY_NAME, run_compare
from ml.runner import ML_REPORTS_DIR, SMOKE_NAB_FILES, run_nab_smoke


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ml",
        description=(
            "Сравнение детекторов аномалий без учителя. "
            "fit не видит label; Prometheus/Zabbix в PR-AUC не входят."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    smoke = sub.add_parser(
        "smoke-nab",
        help="1–3 коротких ряда NAB → reports/ml/smoke_nab.csv (не unified, не KPI 6M)",
    )
    smoke.add_argument(
        "--output",
        default=str(ML_REPORTS_DIR / "smoke_nab.csv"),
        help="Путь к CSV или Parquet отчёта",
    )
    smoke.add_argument(
        "--no-ocsvm",
        action="store_true",
        help="Не включать One-Class SVM",
    )
    smoke.add_argument(
        "--no-plot",
        action="store_true",
        help="Не писать PNG с PR-AUC",
    )
    smoke.add_argument(
        "files",
        nargs="*",
        default=list(SMOKE_NAB_FILES),
        help="Относительные пути CSV внутри datasets/raw/NAB/",
    )

    compare = sub.add_parser(
        "compare",
        help=(
            "Все ряды NAB и срез KPI: 12 детекторов без учителя "
            "→ reports/ml/compare_summary.csv и PNG"
        ),
    )
    scope = compare.add_mutually_exclusive_group()
    scope.add_argument(
        "--nab-only",
        action="store_true",
        help="Только NAB, без KPI",
    )
    scope.add_argument(
        "--kpi-only",
        action="store_true",
        help="Только срез KPI, без NAB",
    )
    compare.add_argument(
        "--kpi-series",
        type=int,
        default=8,
        help="Сколько общих KPI ID взять (сортировка id, по умолчанию 8)",
    )
    compare.add_argument(
        "--output-dir",
        default=str(ML_REPORTS_DIR),
        help="Каталог CSV и PNG (по умолчанию reports/ml)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging()

    if args.command == "smoke-nab":
        table = run_nab_smoke(
            files=args.files or None,
            output=args.output,
            include_ocsvm=not args.no_ocsvm,
            plot=not args.no_plot,
        )
        if table.empty:
            print("Пустой отчёт: нет размеченных тестовых точек.", file=sys.stderr)
            return 1
        print(table.to_string(index=False))
        print(f"\nЗаписано: {args.output}")
        return 0

    if args.command == "compare":
        output_dir = Path(args.output_dir)
        table = run_compare(
            nab=not args.kpi_only,
            kpi=not args.nab_only,
            kpi_series=args.kpi_series,
            output_dir=output_dir,
        )
        if table.empty:
            print("Пустой отчёт: нет размеченных тестовых точек.", file=sys.stderr)
            return 1
        print(table.to_string(index=False))
        print(f"\nСводка: {output_dir / SUMMARY_NAME}")
        if not args.nab_only:
            print(f"KPI ID: {output_dir / KPI_IDS_NAME}")
        print(f"Графики: {output_dir}")
        return 0

    parser.error(f"Неизвестная команда {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
