"""Сравнение без учителя детекторов аномалий на унифицированных рядах.

Ряд идентифицируется тройкой ``(source, service, metric_name)``.
``fit`` не видит ``label``; метки NAB/KPI используются только при оценке.
Prometheus и Zabbix (``label=-1``) в PR-AUC / precision / recall не входят.
"""

from __future__ import annotations

from ml.metrics import evaluate_binary
from ml.models import MODEL_FEATURE_COLUMNS
from ml.runner import run_comparison
from ml.split import NAB_TRAIN_TIME_FRACTION, split_by_time, split_kpi

__all__ = [
    "MODEL_FEATURE_COLUMNS",
    "NAB_TRAIN_TIME_FRACTION",
    "evaluate_binary",
    "run_comparison",
    "split_by_time",
    "split_kpi",
]
