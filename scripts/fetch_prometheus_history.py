"""Выгрузка истории Prometheus кусками (недели/месяцы, не один query_range).

Текущий CLI ``python main.py prometheus --range N`` берёт только последние N
секунд одним запросом. За период с июля это превышает лимит samples у
Prometheus, поэтому история снимается суточными (или короче) окнами.

Сначала смотрит, сколько сервер реально хранит: если retention 15 дней,
данных с июля на сервере уже нет.

Запуск (из корня репозитория, в venv)::

    # что есть на сервере, без скачивания
    python scripts/fetch_prometheus_history.py http://HOST:9090 --inspect

    # метрики приложения (подставь job из --inspect)
    python scripts/fetch_prometheus_history.py http://HOST:9090 \\
        --job myapp --start 2026-07-01 --step 60

Файлы: ``datasets/raw/PROMETHEUS/live/`` (обучение).
В git: ``python scripts/pack_datasets_for_git.py`` → ``datasets/archives/``.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.loaders.prometheus_loader import (  # noqa: E402
    PrometheusError,
    load_prometheus,
)
from etl.storage import save_parquet  # noqa: E402

LIVE_DIR = PROJECT_ROOT / "datasets" / "raw" / "PROMETHEUS" / "live"

#: Служебные префиксы, которые не относятся к «метрикам приложения».
_SKIP_PREFIXES = (
    "prometheus_",
    "promhttp_",
    "go_",
    "process_",
    "python_",
    "scrape_",
    "net_conntrack_",
    "alertmanager_",
    "grafana_",
)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


def _parse_when(text: str) -> datetime:
    """Разобрать дату ``YYYY-MM-DD`` или ``YYYY-MM-DDTHH:MM`` как UTC."""

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"Неверная дата: {text}")


def _api_get(base: str, path: str, params: Optional[Dict[str, Any]] = None, timeout: int = 60) -> Any:
    """GET к Prometheus HTTP API, вернуть поле ``data``."""

    url = f"{base.rstrip('/')}{path}"
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise SystemExit(f"Сеть: {url}: {exc}") from exc
    except ValueError as exc:
        raise SystemExit(f"Не JSON от {url}") from exc
    if payload.get("status") != "success":
        raise SystemExit(f"Prometheus: {payload.get('error', payload)}")
    return payload.get("data")


def inspect_server(base: str) -> None:
    """Напечатать retention, jobs и число имён метрик."""

    print(f"URL: {base}")
    try:
        info = _api_get(base, "/api/v1/status/runtimeinfo")
        if isinstance(info, dict):
            print("retention:", info.get("storageRetention") or info.get("storageRetentionSize") or "?")
            print("uptime / startTime:", info.get("startTime"))
    except SystemExit as exc:
        print("runtimeinfo недоступен:", exc)

    try:
        flags = _api_get(base, "/api/v1/status/flags")
        if isinstance(flags, dict):
            retention = flags.get("storage.tsdb.retention.time") or flags.get("storage.tsdb.retention")
            print("flag storage.tsdb.retention.time:", retention)
    except SystemExit as exc:
        print("flags недоступны:", exc)

    lowest = _api_get(base, "/api/v1/query", {"query": "prometheus_tsdb_lowest_timestamp"})
    result = lowest.get("result") if isinstance(lowest, dict) else None
    if result:
        _, raw = result[0].get("value", [None, None])
        try:
            ts = float(raw)
            if ts > 1e12:
                ts /= 1000.0
            earliest = datetime.fromtimestamp(ts, tz=timezone.utc)
            print("самая старая точка на диске TSDB:", earliest.isoformat())
            print(
                "если это не июль — июля на этом сервере уже нет "
                "(истёк retention или данные в другом хранилище)."
            )
        except (TypeError, ValueError, OSError):
            print("prometheus_tsdb_lowest_timestamp:", raw)

    jobs = _api_get(base, "/api/v1/label/job/values")
    print("jobs:", ", ".join(jobs) if isinstance(jobs, list) else jobs)
    names = _api_get(base, "/api/v1/label/__name__/values")
    if isinstance(names, list):
        app_names = [n for n in names if not n.startswith(_SKIP_PREFIXES)]
        print(f"имён метрик всего: {len(names)}, без служебных префиксов: {len(app_names)}")
        print("примеры:", ", ".join(app_names[:20]))
    print("\nДальше: --job <имя из списка jobs> --start 2026-07-01")


def _metric_names(base: str, matcher: str, start: datetime, end: datetime) -> List[str]:
    """Имена рядов, у которых были точки в диапазоне."""

    params = {
        "match[]": matcher,
        "start": start.timestamp(),
        "end": end.timestamp(),
    }
    names = _api_get(base, "/api/v1/label/__name__/values", params)
    if not isinstance(names, list):
        return []
    return sorted(names)


def _chunks(start: datetime, end: datetime, hours: int) -> Iterable[tuple[datetime, datetime]]:
    """Нарезать [start, end] окнами по ``hours`` часов."""

    delta = timedelta(hours=hours)
    cursor = start
    while cursor < end:
        nxt = min(cursor + delta, end)
        yield cursor, nxt
        cursor = nxt


def _safe_filename(metric: str) -> str:
    """Имя файла без запрещённых символов."""

    return _SAFE_NAME.sub("_", metric)[:120]


def _build_query(metric: str, job: Optional[str], extra: Optional[str]) -> str:
    """PromQL: имя метрики + необязательные селекторы."""

    parts: List[str] = []
    if job:
        parts.append(f'job="{job}"')
    if extra:
        parts.append(extra.strip().lstrip("{").rstrip("}"))
    if not parts:
        return metric
    return f"{metric}{{{','.join(parts)}}}"


def fetch_metric(
    base: str,
    query: str,
    start: datetime,
    end: datetime,
    *,
    step: int,
    chunk_hours: int,
    timeout: int,
) -> pd.DataFrame:
    """Скачать один PromQL кусками и склеить."""

    frames: List[pd.DataFrame] = []
    for chunk_start, chunk_end in _chunks(start, end, chunk_hours):
        try:
            frame = load_prometheus(
                base,
                query,
                start=chunk_start.timestamp(),
                end=chunk_end.timestamp(),
                step_seconds=step,
                timeout=timeout,
            )
        except PrometheusError as exc:
            print(f"  пропуск {chunk_start.date()} {query}: {exc}")
            continue
        if not frame.empty:
            frames.append(frame)
        time.sleep(0.05)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates()
    return out.sort_values("timestamp") if "timestamp" in out.columns else out


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Точка входа."""

    parser = argparse.ArgumentParser(description="Выгрузка истории Prometheus в live/")
    parser.add_argument("url", help="Базовый URL, например http://127.0.0.1:9090")
    parser.add_argument("--inspect", action="store_true", help="Только диагностика, без скачивания")
    parser.add_argument("--job", help="Метка job приложения (рекомендуется)")
    parser.add_argument("--match", dest="extra", help="Доп. селектор, напр. namespace=\"prod\"")
    parser.add_argument("--start", type=_parse_when, default=_parse_when("2026-07-01"))
    parser.add_argument("--end", type=_parse_when, default=datetime.now(timezone.utc))
    parser.add_argument("--step", type=int, default=60, help="Шаг query_range, секунды (по умолчанию 60)")
    parser.add_argument("--chunk-hours", type=int, default=24, help="Длина одного запроса")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--include-internal", action="store_true", help="Не отбрасывать prometheus_/go_/...")
    parser.add_argument("--limit", type=int, default=0, help="Скачать только первые N имён (проба)")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--out", type=Path, default=LIVE_DIR)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("etl.loaders.prometheus_loader").setLevel(logging.WARNING)

    base = args.url.rstrip("/")
    if args.inspect:
        inspect_server(base)
        return 0

    if not args.job and not args.extra:
        print("Укажи --job (имя из --inspect) или --match. Иначе скачается весь сервер.")
        inspect_server(base)
        return 2

    matcher = "{" + ",".join(
        p for p in (
            f'job="{args.job}"' if args.job else "",
            args.extra.strip().lstrip("{").rstrip("}") if args.extra else "",
        ) if p
    ) + "}"
    print(f"селектор: {matcher}")
    print(f"диапазон: {args.start.isoformat()} → {args.end.isoformat()}, step={args.step}s")

    names = _metric_names(base, matcher, args.start, args.end)
    skip = _SKIP_PREFIXES if not args.include_internal else ("process_", "python_")
    names = [
        n
        for n in names
        if not n.startswith(skip)
        and not n.endswith(("_bucket", "_created"))
    ]
    if args.limit:
        names = names[: args.limit]
    print(f"метрик к выгрузке: {len(names)}")
    if not names:
        print("Пусто. Проверь job и что retention покрывает --start (смотри --inspect).")
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    written = 0
    for metric in names:
        prefix = f"{_safe_filename(args.job)}__" if args.job else ""
        dest = args.out / f"{prefix}{_safe_filename(metric)}.parquet"
        if dest.exists() and not args.overwrite:
            print(f"есть, пропуск: {dest.name}")
            continue
        query = _build_query(metric, args.job, args.extra)
        print(f"качаю {query} → {dest.name}")
        frame = fetch_metric(
            base,
            query,
            args.start,
            args.end,
            step=args.step,
            chunk_hours=args.chunk_hours,
            timeout=args.timeout,
        )
        if frame.empty:
            print("  пусто")
            continue
        save_parquet(frame, dest)
        print(f"  {len(frame)} точек")
        written += 1

    print(f"готово, новых файлов: {written} в {args.out}")
    print("Потом: python scripts/pack_datasets_for_git.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
