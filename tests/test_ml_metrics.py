"""PR-AUC / P / R: label=-1 и источники PROMETHEUS/ZABBIX не входят в оценку."""

from __future__ import annotations

import numpy as np
import pandas as pd

from etl.schema import (
    LABEL,
    METRIC_NAME,
    SERVICE,
    SOURCE,
    SOURCE_NAB,
    SOURCE_PROMETHEUS,
    SOURCE_ZABBIX,
    TIMESTAMP,
    VALUE,
)
from ml.metrics import evaluate_binary, is_scored_source
from ml.models import ZScoreDetector
from ml.runner import run_on_frame


def test_label_minus_one_excluded_from_pr_auc() -> None:
    """Точки label=-1 выкидываются из знаменателя; остаётся оценка по 0/1."""

    y_true = np.array([0, 1, -1, -1, 0, 1])
    scores = np.array([0.1, 0.9, 0.99, 0.95, 0.2, 0.8])
    pred = np.array([0, 1, 1, 1, 0, 1])
    result = evaluate_binary(y_true, scores, pred)

    assert result.skipped is False
    assert result.n_scored == 4
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.pr_auc > 0.5


def test_all_unknown_labels_are_skipped() -> None:
    """Если после фильтра не осталось 0/1 — пустая оценка, не PR-AUC по -1."""

    result = evaluate_binary(
        np.array([-1, -1, -1]),
        np.array([0.1, 0.9, 0.2]),
        np.array([0, 1, 0]),
    )
    assert result.skipped is True
    assert result.n_scored == 0
    assert np.isnan(result.pr_auc)
    assert np.isnan(result.precision)
    assert np.isnan(result.recall)


def test_prometheus_and_zabbix_are_not_scored_sources() -> None:
    """По source, а не только по значению label."""

    assert is_scored_source(SOURCE_NAB) is True
    assert is_scored_source(SOURCE_PROMETHEUS) is False
    assert is_scored_source(SOURCE_ZABBIX) is False


def _unlabeled_frame(source: str, service: str, n: int = 40) -> pd.DataFrame:
    return pd.DataFrame(
        {
            TIMESTAMP: pd.date_range("2024-01-01", periods=n, freq="1min"),
            SERVICE: service,
            METRIC_NAME: "cpu_usage",
            VALUE: np.linspace(0.0, 1.0, n),
            LABEL: [-1] * n,
            SOURCE: source,
        }
    )


def test_runner_skips_prometheus_and_zabbix_in_report() -> None:
    """Кадр PROMETHEUS/ZABBIX не даёт строк PR-AUC в таблице runner."""

    mixed = pd.concat(
        [
            _unlabeled_frame(SOURCE_PROMETHEUS, "node-exporter"),
            _unlabeled_frame(SOURCE_ZABBIX, "zbx-host"),
        ],
        ignore_index=True,
    )
    table = run_on_frame(mixed, models=[ZScoreDetector()], include_ocsvm=False)

    assert table.empty or SOURCE_PROMETHEUS not in set(table["source"])
    assert table.empty or SOURCE_ZABBIX not in set(table["source"])
    assert list(table["source"]) == []
