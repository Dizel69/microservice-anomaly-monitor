"""Тесты демонстрационного GUI (Flask test client, без обращений к сети).

Проверяется, что интерфейс открывается, показывает схему конвейера, отдаёт
страницы узлов и запоминает выбранный режим источника Prometheus. Файл состояния
подменяется на временный, чтобы тесты не трогали ``gui/state.json`` разработчика.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from etl.config import REPORTS_BEFORE_DIR
from gui.app import LOG_TAIL_LINES, create_app
from gui.nodes import NODES


@pytest.fixture
def client(tmp_path: Path):
    """Тестовый клиент Flask с временным файлом состояния и пустым каталогом логов."""

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    app = create_app(state_path=tmp_path / "state.json", log_dirs=(log_dir,))
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_index_shows_pipeline_graph(client) -> None:
    """Главная страница открывается и содержит все три источника данных."""

    response = client.get("/")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    for expected in ("NAB", "KPI", "Prometheus", "loaders", "normalize", "features"):
        assert expected in html
    assert "<svg" in html


@pytest.mark.parametrize("node_id", [node.id for node in NODES])
def test_every_node_page_opens(client, node_id: str) -> None:
    """Страница каждого узла схемы отдаётся без ошибок."""

    response = client.get(f"/node/{node_id}")
    assert response.status_code == 200


def test_unknown_node_returns_404(client) -> None:
    """Несуществующий узел даёт 404, а не падение приложения."""

    assert client.get("/node/no-such-node").status_code == 404


def test_prometheus_local_mode_is_saved_and_shown(client, tmp_path: Path) -> None:
    """POST выбора «локальные данные» редиректит на схему, где виден режим LOCAL."""

    response = client.post("/prometheus", data={"mode": "local"})
    assert response.status_code == 302

    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["mode"] == "local"

    html = client.get("/").get_data(as_text=True)
    assert "LOCAL" in html


def test_prometheus_http_mode_keeps_url(client) -> None:
    """POST выбора HTTP API сохраняет адрес и показывает режим URL на схеме."""

    response = client.post(
        "/prometheus",
        data={
            "mode": "http",
            "url": "http://127.0.0.1:9090",
            "query": "node_cpu_seconds_total",
            "step": "30",
            "range": "7200",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "URL" in html
    assert "http://127.0.0.1:9090" in html
    assert "node_cpu_seconds_total" in html


def test_node_page_says_when_log_is_missing(client) -> None:
    """Без лога страница честно сообщает об этом и подсказывает команду."""

    html = client.get("/node/loaders").get_data(as_text=True)
    assert "Прогон ещё не логировался в GUI" in html
    assert "python main.py all" in html


def test_node_page_shows_log_tail(tmp_path: Path) -> None:
    """Если лог есть, показывается его хвост (не более LOG_TAIL_LINES строк)."""

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    lines = [f"строка лога {number}" for number in range(200)]
    (log_dir / "etl.log").write_text("\n".join(lines) + "\n", encoding="utf-8")

    app = create_app(state_path=tmp_path / "state.json", log_dirs=(log_dir,))
    html = app.test_client().get("/node/loaders").get_data(as_text=True)

    assert "строка лога 199" in html
    assert "строка лога 120" in html
    assert "строка лога 5" not in html
    assert f"последние {LOG_TAIL_LINES} строк" in html


def test_report_image_is_served_from_disk(client) -> None:
    """PNG-отчёт отдаётся прямо с диска, без копирования в static/."""

    images = sorted(REPORTS_BEFORE_DIR.glob("*/*.png"))
    if not images:
        pytest.skip("Нет PNG-отчётов в reports/before")

    image = images[0]
    response = client.get(f"/reports/before/{image.parent.name}/{image.name}")
    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_report_route_rejects_path_traversal(client) -> None:
    """Выход за пределы каталога отчётов невозможен."""

    assert client.get("/reports/before/NAB/../../../README.md").status_code == 404
    assert client.get("/reports/nowhere/NAB/raw_data.png").status_code == 404


def test_gui_does_not_write_into_reports_before(client) -> None:
    """Просмотр страниц GUI не меняет снимок reports/before."""

    if not REPORTS_BEFORE_DIR.is_dir():
        pytest.skip("Каталога reports/before нет")

    before = {
        path: path.stat().st_mtime for path in sorted(REPORTS_BEFORE_DIR.rglob("*"))
    }

    client.get("/")
    client.get("/node/reports-before")
    client.get("/node/reports-current")

    after = {
        path: path.stat().st_mtime for path in sorted(REPORTS_BEFORE_DIR.rglob("*"))
    }
    assert before == after
