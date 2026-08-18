#!/usr/bin/env python3
"""Демонстрационный веб-интерфейс ETL-конвейера подготовки данных.

Интерфейс только ЧИТАЕТ уже собранные артефакты: файлы датасетов (через
``os.stat``, без чтения содержимого), PNG-отчёты и логи прогонов. Конвейер
отсюда не запускается, модели не обучаются, каталог ``reports/before``
не перезаписывается.

Запуск::

    python gui/app.py     # http://127.0.0.1:5000
"""

from __future__ import annotations

import json
import sys
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

#: Корень репозитория должен быть импортируемым при запуске ``python gui/app.py``.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, abort, redirect, render_template, request, send_file, url_for
from werkzeug.utils import safe_join

from etl.config import COMBINED_REPORT_KEY, REPORTS_BEFORE_DIR, REPORTS_DIR
from etl.schema import SOURCE_KPI, SOURCE_NAB, SOURCE_PROMETHEUS
from gui.nodes import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    COLUMN_TITLES,
    NODES,
    NODES_BY_ID,
    PROMETHEUS_NODE_ID,
    FileGroup,
    Node,
    edge_lines,
)

GUI_DIR = Path(__file__).resolve().parent

#: Файл с выбором режима Prometheus (создаётся при первом сохранении формы).
DEFAULT_STATE_PATH = GUI_DIR / "state.json"

#: Каталоги, где ищется лог прогона конвейера (берётся самый свежий ``*.log``).
LOG_DIRS = (GUI_DIR / "logs", PROJECT_ROOT / "logs")
LOG_TAIL_LINES = 80

#: Снимки отчётов: ``current`` перестраивается конвейером, ``before`` — нет.
REPORT_SNAPSHOTS: Dict[str, Path] = {
    "current": REPORTS_DIR,
    "before": REPORTS_BEFORE_DIR,
}

#: Порядок источников в галереях отчётов.
SOURCE_ORDER = (SOURCE_NAB, SOURCE_KPI, SOURCE_PROMETHEUS, COMBINED_REPORT_KEY)

MODE_LOCAL = "local"
MODE_HTTP = "http"

DEFAULT_STATE: Dict[str, str] = {
    "mode": MODE_LOCAL,
    "url": "",
    "query": "",
    "step": "15",
    "range": "3600",
}

MISSING_LABEL = "нет (ещё не собрано)"

KIND_LABELS = {
    "input": "источник данных",
    "stage": "шаг обработки",
    "output": "артефакт",
}

CHART_TITLES = {
    "raw_data": "Сырые данные (RAW)",
    "processed_data": "Обработанные данные (PROCESSED)",
    "features_data": "Признаки (ML)",
    "anomaly_distribution": "Распределение аномалий",
    "dataset_summary": "Сводка по набору",
}


# --------------------------------------------------------------------------- #
# Метаданные файлов на диске
# --------------------------------------------------------------------------- #
def _human_size(size: int) -> str:
    """Человекочитаемый размер файла."""

    value = float(size)
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if value < 1024 or unit == "ГБ":
            return f"{int(value)} {unit}" if unit == "Б" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} ГБ"


def _human_time(timestamp: float) -> str:
    """Дата и время изменения файла в привычном формате."""

    return datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M")


def _relative(path: Path) -> str:
    """Путь относительно корня репозитория (если возможно)."""

    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def describe_file(path: Path) -> Dict[str, Any]:
    """Собрать метаданные файла, не читая его содержимое."""

    try:
        stat_result = path.stat()
    except OSError:
        return {
            "name": path.name,
            "path": _relative(path),
            "exists": False,
            "size": MISSING_LABEL,
            "modified": "—",
        }
    return {
        "name": path.name,
        "path": _relative(path),
        "exists": True,
        "size": _human_size(stat_result.st_size),
        "modified": _human_time(stat_result.st_mtime),
    }


def describe_group(group: FileGroup) -> Dict[str, Any]:
    """Развернуть группу файлов узла в данные для таблицы шаблона."""

    if group.pattern is None:
        item = describe_file(group.root)
        return {
            "label": group.label,
            "location": _relative(group.root.parent),
            "files": [item],
            "total": 1 if item["exists"] else 0,
            "hidden": 0,
            "note": None if item["exists"] else MISSING_LABEL,
        }

    if not group.root.is_dir():
        return {
            "label": group.label,
            "location": _relative(group.root),
            "files": [],
            "total": 0,
            "hidden": 0,
            "note": f"каталога нет — {MISSING_LABEL}",
        }

    matches = sorted(
        (path for path in group.root.glob(group.pattern) if path.is_file()),
        key=lambda path: path.name.lower(),
    )
    return {
        "label": group.label,
        "location": _relative(group.root),
        "files": [describe_file(path) for path in matches[: group.limit]],
        "total": len(matches),
        "hidden": max(0, len(matches) - group.limit),
        "note": MISSING_LABEL if not matches else None,
    }


# --------------------------------------------------------------------------- #
# Сохранённый выбор источника Prometheus
# --------------------------------------------------------------------------- #
def load_state(path: Path) -> Dict[str, str]:
    """Прочитать выбор режима Prometheus; при любой проблеме — значения по умолчанию."""

    state = dict(DEFAULT_STATE)
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return state

    if isinstance(stored, dict):
        for key in DEFAULT_STATE:
            value = stored.get(key)
            if isinstance(value, str) and value.strip():
                state[key] = value.strip()

    if state["mode"] not in (MODE_LOCAL, MODE_HTTP):
        state["mode"] = MODE_LOCAL
    return state


def save_state(path: Path, state: Dict[str, str]) -> None:
    """Сохранить выбор режима Prometheus в JSON-файл."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def prometheus_badge(state: Dict[str, str]) -> str:
    """Короткая пометка режима для схемы: ``LOCAL`` или ``URL``."""

    return "URL" if state["mode"] == MODE_HTTP else "LOCAL"


def prometheus_summary(state: Dict[str, str]) -> str:
    """Пояснение к выбранному режиму Prometheus."""

    if state["mode"] == MODE_HTTP:
        return f"HTTP API: {state['url'] or 'адрес не задан'}"
    return "локальные дампы parquet с диска, сеть не используется"


def prometheus_graph_note(state: Dict[str, str]) -> str:
    """Короткая подпись режима внутри блока схемы (ширина блока ограничена)."""

    if state["mode"] != MODE_HTTP:
        return "дампы parquet с диска"
    url = state["url"] or "адрес не задан"
    return url if len(url) <= 28 else url[:27] + "…"


def prometheus_command(state: Dict[str, str]) -> str:
    """Команда конвейера, соответствующая сохранённому выбору."""

    if state["mode"] != MODE_HTTP:
        return "python main.py all"
    url = state["url"] or "<url>"
    query = state["query"] or "<promql>"
    return (
        f"python main.py prometheus {url} '{query}' "
        f"--step {state['step']} --range {state['range']}"
    )


# --------------------------------------------------------------------------- #
# Логи и галереи отчётов
# --------------------------------------------------------------------------- #
def find_log_file(log_dirs: Iterable[Path] = LOG_DIRS) -> Optional[Path]:
    """Найти самый свежий лог прогона конвейера (если он вообще есть)."""

    candidates: List[Path] = []
    for directory in log_dirs:
        if directory.is_dir():
            candidates.extend(path for path in directory.glob("*.log") if path.is_file())
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def tail_log(path: Path, limit: int = LOG_TAIL_LINES) -> List[str]:
    """Прочитать последние ``limit`` строк лога, не загружая файл целиком."""

    try:
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            return [line.rstrip("\n") for line in deque(stream, maxlen=limit)]
    except OSError:
        return []


def _source_sort_key(name: str) -> tuple[int, str]:
    """Порядок источников: NAB, KPI, PROMETHEUS, combined, затем остальные."""

    if name in SOURCE_ORDER:
        return SOURCE_ORDER.index(name), name
    return len(SOURCE_ORDER), name


def report_gallery(snapshot: str) -> List[Dict[str, Any]]:
    """Собрать галерею PNG-отчётов снимка (``current`` / ``before``)."""

    root = REPORT_SNAPSHOTS[snapshot]
    if not root.is_dir():
        return []

    groups: List[Dict[str, Any]] = []
    directories = sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: _source_sort_key(path.name),
    )
    for source_dir in directories:
        images = []
        for image in sorted(source_dir.glob("*.png")):
            info = describe_file(image)
            info["title"] = CHART_TITLES.get(image.stem, image.stem)
            info["url"] = url_for(
                "report_image",
                snapshot=snapshot,
                source=source_dir.name,
                filename=image.name,
            )
            images.append(info)
        groups.append({"source": source_dir.name, "images": images})
    return groups


# --------------------------------------------------------------------------- #
# Приложение
# --------------------------------------------------------------------------- #
def create_app(
    state_path: Optional[Path] = None,
    log_dirs: Optional[Sequence[Path]] = None,
) -> Flask:
    """Создать Flask-приложение GUI.

    Args:
        state_path: Путь к файлу с выбором режима Prometheus. По умолчанию —
            ``gui/state.json``; в тестах удобно подставить временный файл.
        log_dirs: Каталоги поиска логов прогона. По умолчанию — ``gui/logs``
            и ``logs`` в корне репозитория.
    """

    app = Flask(__name__)
    app.config["GUI_STATE_PATH"] = Path(state_path) if state_path else DEFAULT_STATE_PATH
    app.config["GUI_LOG_DIRS"] = tuple(log_dirs) if log_dirs else LOG_DIRS

    def _state() -> Dict[str, str]:
        return load_state(app.config["GUI_STATE_PATH"])

    def _graph_context(state: Dict[str, str], selected_id: Optional[str]) -> Dict[str, Any]:
        return {
            "nodes": NODES,
            "edges": edge_lines(),
            "column_titles": COLUMN_TITLES,
            "canvas_width": CANVAS_WIDTH,
            "canvas_height": CANVAS_HEIGHT,
            "prometheus_node_id": PROMETHEUS_NODE_ID,
            "prometheus_badge": prometheus_badge(state),
            "prometheus_summary": prometheus_summary(state),
            "prometheus_graph_note": prometheus_graph_note(state),
            "selected_id": selected_id,
        }

    @app.get("/")
    def pipeline():
        """Главная страница: схема конвейера и форма выбора источника Prometheus."""

        state = _state()
        return render_template(
            "pipeline.html",
            state=state,
            command=prometheus_command(state),
            **_graph_context(state, None),
        )

    @app.get("/node/<node_id>")
    def node_detail(node_id: str):
        """Детали шага конвейера: назначение, файлы, лог, графики."""

        node: Optional[Node] = NODES_BY_ID.get(node_id)
        if node is None:
            abort(404)

        state = _state()
        log_dirs = app.config["GUI_LOG_DIRS"]
        log_path = find_log_file(log_dirs)
        return render_template(
            "node.html",
            node=node,
            kind_label=KIND_LABELS.get(node.kind, node.kind),
            inputs=[describe_group(group) for group in node.inputs],
            outputs=[describe_group(group) for group in node.outputs],
            log_path=_relative(log_path) if log_path else None,
            log_lines=tail_log(log_path) if log_path else [],
            log_hint_dir=_relative(log_dirs[0]),
            gallery=report_gallery(node.gallery) if node.gallery else None,
            state=state,
            command=prometheus_command(state),
            **_graph_context(state, node.id),
        )

    @app.post("/prometheus")
    def prometheus_mode():
        """Сохранить выбор источника Prometheus и вернуться на схему."""

        state = _state()
        state["mode"] = (
            MODE_HTTP if request.form.get("mode") == MODE_HTTP else MODE_LOCAL
        )
        for field in ("url", "query"):
            state[field] = (request.form.get(field) or "").strip()
        for field in ("step", "range"):
            value = (request.form.get(field) or "").strip()
            state[field] = value if value.isdigit() else DEFAULT_STATE[field]

        save_state(app.config["GUI_STATE_PATH"], state)
        return redirect(url_for("pipeline", _anchor="prometheus"))

    @app.get("/reports/<snapshot>/<source>/<filename>")
    def report_image(snapshot: str, source: str, filename: str):
        """Отдать PNG-отчёт прямо с диска (без копирования в static/)."""

        root = REPORT_SNAPSHOTS.get(snapshot)
        if root is None or not filename.lower().endswith(".png"):
            abort(404)

        target = safe_join(str(root), source, filename)
        if target is None:
            abort(404)

        path = Path(target)
        if not path.is_file():
            abort(404)
        return send_file(path, mimetype="image/png")

    return app


def main() -> int:
    """Запустить сервер разработки Flask."""

    create_app().run(host="127.0.0.1", port=5000, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
