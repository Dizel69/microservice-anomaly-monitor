"""Восстановить pg_dump Zabbix (-Fc) во временный Postgres и выгрузить parquet.

Дампы ``datasets/raw/ZABBIX/live/zabbix_*.dump`` pandas не читает. Скрипт:

1. поднимает одноразовый контейнер ``postgres:15`` (или использует локальный
   ``psql``/``pg_restore``, если задан ``--dsn``);
2. создаёт таблицы без FK/триггеров Zabbix;
3. заливает TABLE DATA из двух дампов;
4. JOIN history/trends с items+hosts;
5. пишет parquet в ``datasets/raw/ZABBIX/`` (не в git).

History и trends **не смешиваются** в один ряд:
history → ``metric_name = items.key_``;
trends  → ``metric_name = items.key_ + '{grain="trend_avg"}'``, ``value = value_avg``.

Если Docker недоступен и нет локального pg_restore/psql — явный код выхода 2,
не «тихий пропуск».
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.schema import (  # noqa: E402
    LABEL,
    LABELS,
    LABEL_UNKNOWN,
    METRIC_NAME,
    METRIC_UNKNOWN,
    SERVICE,
    SOURCE,
    SOURCE_ZABBIX,
    TIMESTAMP,
    UNIFIED_COLUMNS,
    VALUE,
)
from etl.storage import save_parquet  # noqa: E402

LIVE_DIR = PROJECT_ROOT / "datasets" / "raw" / "ZABBIX" / "live"
OUT_DIR = PROJECT_ROOT / "datasets" / "raw" / "ZABBIX"
DOCKER_IMAGE = "postgres:15"
TREND_GRAIN_SUFFIX = '{grain="trend_avg"}'

#: Схема как в дампах (pg_restore -s), без FK, триггеров и функций Zabbix.
SCHEMA_SQL = """
CREATE TABLE public.hosts (
    hostid bigint NOT NULL,
    proxy_hostid bigint,
    host character varying(128) DEFAULT ''::character varying NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    ipmi_authtype integer DEFAULT '-1'::integer NOT NULL,
    ipmi_privilege integer DEFAULT 2 NOT NULL,
    ipmi_username character varying(16) DEFAULT ''::character varying NOT NULL,
    ipmi_password character varying(20) DEFAULT ''::character varying NOT NULL,
    maintenanceid bigint,
    maintenance_status integer DEFAULT 0 NOT NULL,
    maintenance_type integer DEFAULT 0 NOT NULL,
    maintenance_from integer DEFAULT 0 NOT NULL,
    name character varying(128) DEFAULT ''::character varying NOT NULL,
    flags integer DEFAULT 0 NOT NULL,
    templateid bigint,
    description text DEFAULT ''::text NOT NULL,
    tls_connect integer DEFAULT 1 NOT NULL,
    tls_accept integer DEFAULT 1 NOT NULL,
    tls_issuer character varying(1024) DEFAULT ''::character varying NOT NULL,
    tls_subject character varying(1024) DEFAULT ''::character varying NOT NULL,
    tls_psk_identity character varying(128) DEFAULT ''::character varying NOT NULL,
    tls_psk character varying(512) DEFAULT ''::character varying NOT NULL,
    proxy_address character varying(255) DEFAULT ''::character varying NOT NULL,
    auto_compress integer DEFAULT 1 NOT NULL,
    discover integer DEFAULT 0 NOT NULL,
    custom_interfaces integer DEFAULT 0 NOT NULL,
    uuid character varying(32) DEFAULT ''::character varying NOT NULL,
    name_upper character varying(128) DEFAULT ''::character varying NOT NULL,
    vendor_name character varying(64) DEFAULT ''::character varying NOT NULL,
    vendor_version character varying(32) DEFAULT ''::character varying NOT NULL
);
CREATE TABLE public.items (
    itemid bigint NOT NULL,
    type integer DEFAULT 0 NOT NULL,
    snmp_oid character varying(512) DEFAULT ''::character varying NOT NULL,
    hostid bigint NOT NULL,
    name character varying(255) DEFAULT ''::character varying NOT NULL,
    key_ character varying(2048) DEFAULT ''::character varying NOT NULL,
    delay character varying(1024) DEFAULT '0'::character varying NOT NULL,
    history character varying(255) DEFAULT '90d'::character varying NOT NULL,
    trends character varying(255) DEFAULT '365d'::character varying NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    value_type integer DEFAULT 0 NOT NULL,
    trapper_hosts character varying(255) DEFAULT ''::character varying NOT NULL,
    units character varying(255) DEFAULT ''::character varying NOT NULL,
    formula character varying(255) DEFAULT ''::character varying NOT NULL,
    logtimefmt character varying(64) DEFAULT ''::character varying NOT NULL,
    templateid bigint,
    valuemapid bigint,
    params text DEFAULT ''::text NOT NULL,
    ipmi_sensor character varying(128) DEFAULT ''::character varying NOT NULL,
    authtype integer DEFAULT 0 NOT NULL,
    username character varying(64) DEFAULT ''::character varying NOT NULL,
    password character varying(64) DEFAULT ''::character varying NOT NULL,
    publickey character varying(64) DEFAULT ''::character varying NOT NULL,
    privatekey character varying(64) DEFAULT ''::character varying NOT NULL,
    flags integer DEFAULT 0 NOT NULL,
    interfaceid bigint,
    description text DEFAULT ''::text NOT NULL,
    inventory_link integer DEFAULT 0 NOT NULL,
    lifetime character varying(255) DEFAULT '30d'::character varying NOT NULL,
    evaltype integer DEFAULT 0 NOT NULL,
    jmx_endpoint character varying(255) DEFAULT ''::character varying NOT NULL,
    master_itemid bigint,
    timeout character varying(255) DEFAULT '3s'::character varying NOT NULL,
    url character varying(2048) DEFAULT ''::character varying NOT NULL,
    query_fields character varying(2048) DEFAULT ''::character varying NOT NULL,
    posts text DEFAULT ''::text NOT NULL,
    status_codes character varying(255) DEFAULT '200'::character varying NOT NULL,
    follow_redirects integer DEFAULT 1 NOT NULL,
    post_type integer DEFAULT 0 NOT NULL,
    http_proxy character varying(255) DEFAULT ''::character varying NOT NULL,
    headers text DEFAULT ''::text NOT NULL,
    retrieve_mode integer DEFAULT 0 NOT NULL,
    request_method integer DEFAULT 0 NOT NULL,
    output_format integer DEFAULT 0 NOT NULL,
    ssl_cert_file character varying(255) DEFAULT ''::character varying NOT NULL,
    ssl_key_file character varying(255) DEFAULT ''::character varying NOT NULL,
    ssl_key_password character varying(64) DEFAULT ''::character varying NOT NULL,
    verify_peer integer DEFAULT 0 NOT NULL,
    verify_host integer DEFAULT 0 NOT NULL,
    allow_traps integer DEFAULT 0 NOT NULL,
    discover integer DEFAULT 0 NOT NULL,
    uuid character varying(32) DEFAULT ''::character varying NOT NULL,
    name_upper character varying(255) DEFAULT ''::character varying NOT NULL
);
CREATE TABLE public.trends (
    itemid bigint NOT NULL,
    clock integer DEFAULT 0 NOT NULL,
    num integer DEFAULT 0 NOT NULL,
    value_min double precision DEFAULT '0'::double precision NOT NULL,
    value_avg double precision DEFAULT '0'::double precision NOT NULL,
    value_max double precision DEFAULT '0'::double precision NOT NULL
);
CREATE TABLE public.trends_uint (
    itemid bigint NOT NULL,
    clock integer DEFAULT 0 NOT NULL,
    num integer DEFAULT 0 NOT NULL,
    value_min numeric(20,0) DEFAULT '0'::numeric NOT NULL,
    value_avg numeric(20,0) DEFAULT '0'::numeric NOT NULL,
    value_max numeric(20,0) DEFAULT '0'::numeric NOT NULL
);
CREATE TABLE public.history (
    itemid bigint NOT NULL,
    clock integer DEFAULT 0 NOT NULL,
    value double precision DEFAULT '0'::double precision NOT NULL,
    ns integer DEFAULT 0 NOT NULL
);
CREATE TABLE public.history_uint (
    itemid bigint NOT NULL,
    clock integer DEFAULT 0 NOT NULL,
    value numeric(20,0) DEFAULT '0'::numeric NOT NULL,
    ns integer DEFAULT 0 NOT NULL
);
"""

INDEX_SQL = """
CREATE INDEX history_itemid_idx ON public.history (itemid);
CREATE INDEX history_uint_itemid_idx ON public.history_uint (itemid);
CREATE INDEX trends_itemid_idx ON public.trends (itemid);
CREATE INDEX trends_uint_itemid_idx ON public.trends_uint (itemid);
CREATE INDEX items_itemid_idx ON public.items (itemid);
CREATE INDEX items_hostid_idx ON public.items (hostid);
CREATE INDEX hosts_hostid_idx ON public.hosts (hostid);
"""

HISTORY_SELECT_SQL = """
SELECT
    to_timestamp(h.clock) AT TIME ZONE 'UTC' AS timestamp,
    hosts.host AS service,
    items.key_ AS metric_name,
    h.value::double precision AS value,
    -1 AS label,
    'ZABBIX' AS source,
    json_build_object(
        'itemid', items.itemid,
        'key_', items.key_,
        'host', hosts.host,
        'units', items.units,
        'grain', 'history'
    )::text AS labels
FROM (
    SELECT itemid, clock, value FROM public.history
    UNION ALL
    SELECT itemid, clock, value::double precision FROM public.history_uint
) AS h
JOIN public.items ON items.itemid = h.itemid
JOIN public.hosts ON hosts.hostid = items.hostid
"""

TRENDS_SELECT_SQL = f"""
SELECT
    to_timestamp(t.clock) AT TIME ZONE 'UTC' AS timestamp,
    hosts.host AS service,
    items.key_ || '{TREND_GRAIN_SUFFIX}' AS metric_name,
    t.value_avg::double precision AS value,
    -1 AS label,
    'ZABBIX' AS source,
    json_build_object(
        'itemid', items.itemid,
        'key_', items.key_,
        'host', hosts.host,
        'units', items.units,
        'grain', 'trend_avg'
    )::text AS labels
FROM (
    SELECT itemid, clock, value_avg FROM public.trends
    UNION ALL
    SELECT itemid, clock, value_avg::double precision FROM public.trends_uint
) AS t
JOIN public.items ON items.itemid = t.itemid
JOIN public.hosts ON hosts.hostid = items.hostid
"""


class RestoreError(RuntimeError):
    """Восстановление дампов Zabbix не удалось."""


def docker_available() -> bool:
    """Проверить, что Docker установлен и демон отвечает."""

    if not shutil.which("docker"):
        return False
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def local_pg_tools_available() -> bool:
    """Есть ли на хосте pg_restore и psql."""

    return bool(shutil.which("pg_restore") and shutil.which("psql"))


def _run(cmd: List[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Запустить команду и вернуть результат с текстом stdout/stderr."""

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RestoreError(f"команда {' '.join(cmd)} завершилась с кодом {proc.returncode}: {detail}")
    return proc


def _wait_pg_ready(container: str, timeout: int = 60) -> None:
    """Дождаться pg_isready внутри контейнера."""

    deadline = time.time() + timeout
    while time.time() < deadline:
        proc = subprocess.run(
            ["docker", "exec", container, "pg_isready", "-U", "zabbix", "-d", "zabbix"],
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            return
        time.sleep(1)
    raise RestoreError(f"Postgres в контейнере {container} не стал готов за {timeout}с")


def _psql_docker(container: str, sql: str) -> None:
    """Выполнить SQL в контейнере."""

    proc = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-U", "zabbix", "-d", "zabbix", "-v", "ON_ERROR_STOP=1"],
        input=sql,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RestoreError(f"psql: {(proc.stderr or proc.stdout).strip()}")


def _one_line_sql(sql: str) -> str:
    """Сжать SQL в одну строку (нужно для COPY/\\copy)."""

    return " ".join(sql.split())


def _copy_query_docker(container: str, select_sql: str, dest: Path) -> None:
    """COPY (query) → CSV на смонтированный том."""

    dest.parent.mkdir(parents=True, exist_ok=True)
    inner = _one_line_sql(select_sql)
    sql = (
        f"COPY ({inner}) TO '/out/{dest.name}' "
        "WITH (FORMAT csv, HEADER true);"
    )
    _psql_docker(container, sql)


def _pg_restore_docker(container: str, dump_path: str, tables: Sequence[str]) -> None:
    """Залить TABLE DATA выбранных таблиц."""

    cmd = [
        "docker",
        "exec",
        container,
        "pg_restore",
        "--data-only",
        "--disable-triggers",
        "--no-owner",
        "--no-privileges",
        "-U",
        "zabbix",
        "-d",
        "zabbix",
    ]
    for table in tables:
        cmd.extend(["-t", table])
    cmd.append(dump_path)
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    # pg_restore пишет предупреждения в stderr даже при успехе.
    if proc.returncode != 0:
        raise RestoreError(
            f"pg_restore {dump_path} таблицы {list(tables)}: {(proc.stderr or proc.stdout).strip()}"
        )


def _frame_from_csv(csv_path: Path) -> pd.DataFrame:
    """Прочитать CSV выгрузки и привести типы единой схемы."""

    if not csv_path.is_file() or csv_path.stat().st_size == 0:
        return pd.DataFrame(columns=[*UNIFIED_COLUMNS, LABELS])
    frame = pd.read_csv(csv_path)
    if frame.empty:
        return pd.DataFrame(columns=[*UNIFIED_COLUMNS, LABELS])
    frame[TIMESTAMP] = pd.to_datetime(frame[TIMESTAMP], utc=True, errors="coerce")
    frame[VALUE] = pd.to_numeric(frame[VALUE], errors="coerce")
    frame[LABEL] = LABEL_UNKNOWN
    frame[SOURCE] = SOURCE_ZABBIX
    frame[SERVICE] = frame[SERVICE].astype(str)
    frame[METRIC_NAME] = frame[METRIC_NAME].astype(str)
    if LABELS in frame.columns:
        frame[LABELS] = frame[LABELS].astype(str)
        return frame[[*UNIFIED_COLUMNS, LABELS]]
    return frame[UNIFIED_COLUMNS]


def print_parquet_stats(path: Path, frame: pd.DataFrame) -> Dict[str, object]:
    """Напечатать сводку по выгруженному parquet и вернуть её словарём."""

    unknown = int((frame[METRIC_NAME] == METRIC_UNKNOWN).sum()) if not frame.empty else 0
    if frame.empty:
        ts_min = ts_max = None
        n_series = 0
    else:
        ts_min = frame[TIMESTAMP].min()
        ts_max = frame[TIMESTAMP].max()
        n_series = int(frame.groupby([SERVICE, METRIC_NAME], sort=False).ngroups)
    stats: Dict[str, object] = {
        "path": str(path),
        "rows": int(len(frame)),
        "ts_min": ts_min,
        "ts_max": ts_max,
        "series": n_series,
        "unknown_metric": unknown,
    }
    print(f"файл: {path}")
    print(f"  строк: {stats['rows']}")
    print(f"  timestamp min/max: {ts_min} / {ts_max}")
    print(f"  уникальных (service, metric_name): {n_series}")
    print(f"  unknown_metric: {unknown}")
    return stats


def restore_with_docker(
    history_dump: Path,
    trends_dump: Path,
    out_dir: Path,
) -> Dict[str, pd.DataFrame]:
    """Поднять postgres:15, восстановить дампы, вернуть кадры history/trends."""

    out_dir.mkdir(parents=True, exist_ok=True)
    staging = out_dir / ".restore_staging"
    staging.mkdir(parents=True, exist_ok=True)
    staging.chmod(0o777)
    container = f"mam-zabbix-restore-{os.getpid()}"
    try:
        print(f"Docker: контейнер {container} ({DOCKER_IMAGE})")
        _run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container,
                "-e",
                "POSTGRES_USER=zabbix",
                "-e",
                "POSTGRES_PASSWORD=zabbix",
                "-e",
                "POSTGRES_DB=zabbix",
                "-v",
                f"{history_dump.parent.resolve()}:/dumps:ro",
                "-v",
                f"{staging.resolve()}:/out",
                DOCKER_IMAGE,
            ]
        )
        _wait_pg_ready(container)
        print("схема таблиц без FK/триггеров")
        _psql_docker(container, SCHEMA_SQL)
        print(f"pg_restore {trends_dump.name} (hosts, items, trends, trends_uint)")
        _pg_restore_docker(
            container,
            f"/dumps/{trends_dump.name}",
            ("hosts", "items", "trends", "trends_uint"),
        )
        print(f"pg_restore {history_dump.name} (history, history_uint)")
        _pg_restore_docker(
            container,
            f"/dumps/{history_dump.name}",
            ("history", "history_uint"),
        )
        print("индексы для JOIN")
        _psql_docker(container, INDEX_SQL)
        history_csv = staging / "history.csv"
        trends_csv = staging / "trends.csv"
        print("COPY history JOIN items+hosts")
        _copy_query_docker(container, HISTORY_SELECT_SQL, history_csv)
        print("COPY trends JOIN items+hosts")
        _copy_query_docker(container, TRENDS_SELECT_SQL, trends_csv)
        history = _frame_from_csv(history_csv)
        trends = _frame_from_csv(trends_csv)
        return {"history": history, "trends": trends}
    finally:
        subprocess.run(["docker", "rm", "-f", container], capture_output=True, check=False)
        shutil.rmtree(staging, ignore_errors=True)


def restore_with_local_psql(
    history_dump: Path,
    trends_dump: Path,
    dsn: str,
) -> Dict[str, pd.DataFrame]:
    """Восстановить дампы в уже существующую БД через локальный pg_restore."""

    _run(["psql", dsn, "-v", "ON_ERROR_STOP=1", "-c", SCHEMA_SQL])
    restore_base = [
        "pg_restore",
        "--data-only",
        "--disable-triggers",
        "--no-owner",
        "--no-privileges",
        "-d",
        dsn,
    ]
    _run(
        restore_base
        + ["-t", "hosts", "-t", "items", "-t", "trends", "-t", "trends_uint", str(trends_dump)]
    )
    _run(restore_base + ["-t", "history", "-t", "history_uint", str(history_dump)])
    _run(["psql", dsn, "-v", "ON_ERROR_STOP=1", "-c", INDEX_SQL])

    staging = history_dump.parent / ".restore_staging_local"
    staging.mkdir(parents=True, exist_ok=True)
    try:
        for name, sql in (("history", HISTORY_SELECT_SQL), ("trends", TRENDS_SELECT_SQL)):
            dest = staging / f"{name}.csv"
            copy_sql = f"\\copy ({sql}) TO '{dest}' WITH (FORMAT csv, HEADER true)"
            _run(["psql", dsn, "-v", "ON_ERROR_STOP=1", "-c", copy_sql])
        return {
            "history": _frame_from_csv(staging / "history.csv"),
            "trends": _frame_from_csv(staging / "trends.csv"),
        }
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _validate_labels_json(frame: pd.DataFrame, grain: str) -> None:
    """Проверить, что RAW labels содержат ожидаемые ключи (выборка)."""

    if frame.empty or LABELS not in frame.columns:
        return
    sample = json.loads(str(frame[LABELS].iloc[0]))
    for key in ("itemid", "key_", "host", "units", "grain"):
        if key not in sample:
            raise RestoreError(f"в labels нет ключа {key}: {sample}")
    if sample.get("grain") != grain:
        raise RestoreError(f"ожидался grain={grain}, получено {sample.get('grain')}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Точка входа."""

    parser = argparse.ArgumentParser(
        description="pg_restore дампов Zabbix → parquet единой схемы"
    )
    parser.add_argument(
        "--history-dump",
        type=Path,
        default=LIVE_DIR / "zabbix_history.dump",
    )
    parser.add_argument(
        "--trends-dump",
        type=Path,
        default=LIVE_DIR / "zabbix_trends.dump",
    )
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument(
        "--dsn",
        default=os.environ.get("ZABBIX_PG_DSN"),
        help="Локальный Postgres (psql/pg_restore). Иначе — Docker postgres:15.",
    )
    args = parser.parse_args(argv)

    history_dump = args.history_dump.resolve()
    trends_dump = args.trends_dump.resolve()
    for dump in (history_dump, trends_dump):
        if not dump.is_file():
            print(f"Нет файла дампа: {dump}", file=sys.stderr)
            return 1

    try:
        if docker_available():
            frames = restore_with_docker(history_dump, trends_dump, args.out)
        elif args.dsn and local_pg_tools_available():
            print(f"Docker недоступен, используем локальный psql ({args.dsn})")
            frames = restore_with_local_psql(history_dump, trends_dump, args.dsn)
        else:
            print(
                "BLOCKER: Docker недоступен, локальный pg_restore/psql не найден "
                "(или не задан --dsn / ZABBIX_PG_DSN). "
                "Не могу восстановить zabbix_*.dump. Установите Docker "
                "(образ postgres:15) либо postgresql-client и повторите.",
                file=sys.stderr,
            )
            return 2

        history = frames["history"]
        trends = frames["trends"]
        _validate_labels_json(history, "history")
        _validate_labels_json(trends, "trend_avg")

        history_path = args.out / "zabbix_history.parquet"
        trends_path = args.out / "zabbix_trends.parquet"
        args.out.mkdir(parents=True, exist_ok=True)
        save_parquet(history, history_path)
        save_parquet(trends, trends_path)

        print("=== Zabbix restore ===")
        print_parquet_stats(history_path, history)
        print_parquet_stats(trends_path, trends)
        if int((history[METRIC_NAME] == METRIC_UNKNOWN).sum() if not history.empty else 0) or int(
            (trends[METRIC_NAME] == METRIC_UNKNOWN).sum() if not trends.empty else 0
        ):
            print("предупреждение: есть unknown_metric — для Zabbix ожидался key_ как имя")
        return 0
    except RestoreError as exc:
        print(f"ошибка restore: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
