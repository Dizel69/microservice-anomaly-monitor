"""Загрузчики источников данных ETL-конвейера."""

from __future__ import annotations

__all__ = [
    "load_nab",
    "load_kpi",
    "load_prometheus",
]

from etl.loaders.kpi_loader import load_kpi
from etl.loaders.nab_loader import load_nab
from etl.loaders.prometheus_loader import load_prometheus
