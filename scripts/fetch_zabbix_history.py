"""Выгрузка истории Zabbix кусками — тот же сценарий, что у Prometheus.

Официальный JSON-RPC, свой токен администратора тестового контура.
Числовые item'ы (float/uint). Сырая history нарезается по суткам;
если housekeeping уже стёр точки — добираем часовые trends.

    export ZABBIX_TOKEN='...'          # User → API tokens, не в git
    python scripts/fetch_zabbix_history.py https://zabbix.example/api_jsonrpc.php --inspect

    python scripts/fetch_zabbix_history.py https://zabbix.example/api_jsonrpc.php \
        --start 2026-01-01

Файлы: ``datasets/raw/ZABBIX/live/`` (обучение). В git — через
``python scripts/pack_datasets_for_git.py``.
"""

from __future__ import annotations

import argparse
import json
import os
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

from etl.schema import (  # noqa: E402
    LABEL,
    LABEL_UNKNOWN,
    LABELS,
    METRIC_NAME,
    SERVICE,
    SOURCE,
    SOURCE_ZABBIX,
    TIMESTAMP,
    VALUE,
)
from etl.storage import save_parquet  # noqa: E402

LIVE_DIR = PROJECT_ROOT / "datasets" / "raw" / "ZABBIX" / "live"
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")
HISTORY_LIMIT = 5000
VALUE_FLOAT = 0
VALUE_UINT = 3


def _parse_when(text: str) -> datetime:
    """Разобрать дату ``YYYY-MM-DD`` как UTC."""

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"Неверная дата: {text}")


def _api_url(url: str) -> str:
    """Добавить ``/api_jsonrpc.php``, если передан только хост."""

    cleaned = url.rstrip("/")
    if cleaned.endswith("api_jsonrpc.php"):
        return cleaned
    return f"{cleaned}/api_jsonrpc.php"


def rpc(
    url: str,
    token: Optional[str],
    method: str,
    params: Any,
    *,
    timeout: int,
    verify: bool = True,
) -> Any:
    """Вызвать JSON-RPC. Токен — Bearer, при отказе — поле ``auth``."""

    payload: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params if params is not None else [],
        "id": 1,
    }
    headers = {"Content-Type": "application/json-rpc"}
    if token and method != "apiinfo.version":
        headers["Authorization"] = f"Bearer {token}"
    response = requests.post(
        url, json=payload, headers=headers, timeout=timeout, verify=verify
    )
    response.raise_for_status()
    body = response.json()
    if "error" in body and token and method != "apiinfo.version":
        payload["auth"] = token
        headers.pop("Authorization", None)
        response = requests.post(
            url, json=payload, headers=headers, timeout=timeout, verify=verify
        )
        response.raise_for_status()
        body = response.json()
    if "error" in body:
        err = body["error"]
        raise RuntimeError(f"{method}: {err.get('message')} {err.get('data', '')}".strip())
    return body.get("result")


def _chunks(start: datetime, end: datetime, hours: int) -> Iterable[tuple[datetime, datetime]]:
    """Нарезать диапазон окнами."""

    delta = timedelta(hours=hours)
    cursor = start
    while cursor < end:
        nxt = min(cursor + delta, end)
        yield cursor, nxt
        cursor = nxt


def _safe_filename(text: str) -> str:
    """Имя parquet без запрещённых символов."""

    return _SAFE_NAME.sub("_", text)[:120]


def inspect_server(url: str, token: Optional[str], timeout: int, verify: bool) -> None:
    """Версия, группы, хосты, числовые item'ы."""

    try:
        version = rpc(url, None, "apiinfo.version", [], timeout=timeout, verify=verify)
    except Exception as exc:  # noqa: BLE001 — диагностика
        version = f"не удалось без токена ({exc})"
        if token:
            try:
                version = rpc(
                    url, token, "apiinfo.version", [], timeout=timeout, verify=verify
                )
            except Exception as exc2:  # noqa: BLE001
                version = f"ошибка: {exc2}"
    print(f"URL: {url}")
    print(f"версия API: {version}")
    if not token:
        print("Без токена дальше не пойдём. Задай ZABBIX_TOKEN и повтори --inspect.")
        return
    groups = rpc(
        url, token, "hostgroup.get", {"output": ["groupid", "name"]},
        timeout=timeout, verify=verify,
    )
    print("host groups:")
    for group in groups or []:
        print(f"  {group.get('groupid')}\t{group.get('name')}")
    hosts = rpc(
        url,
        token,
        "host.get",
        {"output": ["hostid", "host", "name"], "monitored_hosts": True},
        timeout=timeout,
        verify=verify,
    )
    print(f"мониторимых хостов: {len(hosts or [])}")
    for host in (hosts or [])[:15]:
        print(f"  {host.get('host')} ({host.get('name')})")
    if hosts and len(hosts) > 15:
        print(f"  ... ещё {len(hosts) - 15}")
    items = rpc(
        url,
        token,
        "item.get",
        {
            "filter": {"value_type": [VALUE_FLOAT, VALUE_UINT]},
            "monitored": True,
            "countOutput": True,
        },
        timeout=timeout,
        verify=verify,
    )
    print(f"числовых item'ов (float+uint): {items}")
    print("\nДальше: --start ГГГГ-ММ-ДД  и при необходимости --group-id")
    print("Токен только в ZABBIX_TOKEN, не в репозиторий.")


def _load_items(
    url: str,
    token: str,
    *,
    group_id: Optional[str],
    timeout: int,
    verify: bool,
) -> List[Dict[str, Any]]:
    """Числовые включённые item'ы, опционально одна host group."""

    params: Dict[str, Any] = {
        "output": ["itemid", "name", "key_", "hostid", "value_type", "units"],
        "selectHosts": ["host", "name"],
        "filter": {"value_type": [VALUE_FLOAT, VALUE_UINT]},
        "monitored": True,
    }
    if group_id:
        params["groupids"] = group_id
    items = rpc(url, token, "item.get", params, timeout=timeout, verify=verify) or []
    return items


def _history_page(
    url: str,
    token: str,
    item: Dict[str, Any],
    start: int,
    end: int,
    timeout: int,
    verify: bool,
) -> List[Dict[str, Any]]:
    """Одна страница history.get."""

    history_type = VALUE_FLOAT if int(item["value_type"]) == VALUE_FLOAT else VALUE_UINT
    return (
        rpc(
            url,
            token,
            "history.get",
            {
                "output": "extend",
                "history": history_type,
                "itemids": item["itemid"],
                "time_from": start,
                "time_till": end,
                "sortfield": "clock",
                "sortorder": "ASC",
                "limit": HISTORY_LIMIT,
            },
            timeout=timeout,
            verify=verify,
        )
        or []
    )


def _history_range(
    url: str,
    token: str,
    item: Dict[str, Any],
    start: int,
    end: int,
    timeout: int,
    verify: bool,
) -> List[Dict[str, Any]]:
    """history.get; если упёрлись в limit — режем окно пополам."""

    if start >= end:
        return []
    page = _history_page(url, token, item, start, end, timeout, verify)
    if len(page) < HISTORY_LIMIT:
        return page
    mid = start + (end - start) // 2
    if mid <= start or mid >= end:
        return page
    return _history_range(url, token, item, start, mid, timeout, verify) + _history_range(
        url, token, item, mid, end, timeout, verify
    )


def _trends_range(
    url: str,
    token: str,
    item: Dict[str, Any],
    start: int,
    end: int,
    timeout: int,
    verify: bool,
) -> List[Dict[str, Any]]:
    """Часовые агрегаты, если сырой history уже нет."""

    rows = (
        rpc(
            url,
            token,
            "trend.get",
            {
                "itemids": item["itemid"],
                "time_from": start,
                "time_till": end,
                "output": ["itemid", "clock", "num", "value_min", "value_avg", "value_max"],
            },
            timeout=timeout,
            verify=verify,
        )
        or []
    )
    out = []
    for row in rows:
        out.append({"clock": row.get("clock"), "value": row.get("value_avg"), "ns": 0, "trend": True})
    return out


def _host_name(item: Dict[str, Any]) -> str:
    """Имя хоста из selectHosts."""

    hosts = item.get("hosts") or []
    if not hosts:
        return str(item.get("hostid", "zabbix"))
    return str(hosts[0].get("host") or hosts[0].get("name") or item.get("hostid"))


def _records(item: Dict[str, Any], points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Точки Zabbix → единая схема."""

    service = _host_name(item)
    metric = str(item.get("key_") or item.get("name") or item["itemid"])
    labels = json.dumps(
        {
            "itemid": item.get("itemid"),
            "name": item.get("name"),
            "key_": item.get("key_"),
            "units": item.get("units"),
            "hostid": item.get("hostid"),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    rows = []
    for point in points:
        clock = point.get("clock")
        if clock is None:
            continue
        rows.append(
            {
                TIMESTAMP: pd.to_datetime(int(clock), unit="s", utc=True),
                SERVICE: service,
                METRIC_NAME: metric,
                VALUE: point.get("value"),
                LABEL: LABEL_UNKNOWN,
                SOURCE: SOURCE_ZABBIX,
                LABELS: labels,
            }
        )
    return rows


def fetch_item(
    url: str,
    token: str,
    item: Dict[str, Any],
    start: datetime,
    end: datetime,
    *,
    chunk_hours: int,
    mode: str,
    timeout: int,
) -> pd.DataFrame:
    """Скачать один item кусками."""

    frames: List[pd.DataFrame] = []
    for chunk_start, chunk_end in _chunks(start, end, chunk_hours):
        t0, t1 = int(chunk_start.timestamp()), int(chunk_end.timestamp())
        points: List[Dict[str, Any]] = []
        if mode in {"history", "auto"}:
            points = _history_range(url, token, item, t0, t1, timeout)
        if mode == "trends" or (mode == "auto" and not points):
            points = _trends_range(url, token, item, t0, t1, timeout)
        if points:
            recs = _records(item, points)
            if recs:
                frames.append(pd.DataFrame.from_records(recs))
        time.sleep(0.02)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=[TIMESTAMP, SERVICE, METRIC_NAME])
    return out.sort_values(TIMESTAMP)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Точка входа."""

    parser = argparse.ArgumentParser(description="Выгрузка истории Zabbix в live/")
    parser.add_argument("url", help="URL API, например https://zabbix.example/api_jsonrpc.php")
    parser.add_argument("--token", default=os.environ.get("ZABBIX_TOKEN"), help="или env ZABBIX_TOKEN")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--group-id", help="Только эта host group (из --inspect)")
    parser.add_argument("--start", type=_parse_when, default=_parse_when("2026-01-01"))
    parser.add_argument("--end", type=_parse_when, default=datetime.now(timezone.utc))
    parser.add_argument("--chunk-hours", type=int, default=24)
    parser.add_argument("--mode", choices=["auto", "history", "trends"], default="auto")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--limit", type=int, default=0, help="Первые N item'ов (проба)")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--out", type=Path, default=LIVE_DIR)
    args = parser.parse_args(argv)

    url = _api_url(args.url)
    if not args.token:
        print("Задай ZABBIX_TOKEN или --token (API token из UI).")
        return 2
    try:
        if args.inspect:
            inspect_server(url, args.token, args.timeout)
            return 0
        items = _load_items(url, args.token, group_id=args.group_id, timeout=args.timeout)
        if args.limit:
            items = items[: args.limit]
        print(f"item'ов: {len(items)}, {args.start.date()} → {args.end.date()}, mode={args.mode}")
        if not items:
            print("Пусто. Смотри --inspect и --group-id.")
            return 1
        args.out.mkdir(parents=True, exist_ok=True)
        written = 0
        for item in items:
            host = _host_name(item)
            dest = args.out / f"{_safe_filename(host)}__{_safe_filename(str(item.get('key_') or item['itemid']))}.parquet"
            if dest.exists() and not args.overwrite:
                print(f"есть, пропуск: {dest.name}")
                continue
            print(f"качаю {host} {item.get('key_')} → {dest.name}")
            frame = fetch_item(
                url,
                args.token,
                item,
                args.start,
                args.end,
                chunk_hours=args.chunk_hours,
                mode=args.mode,
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
    except (requests.RequestException, RuntimeError) as exc:
        print(f"ошибка: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
