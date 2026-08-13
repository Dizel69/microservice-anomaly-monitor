"""Построение графиков по результатам ETL-конвейера.

Создаёт пять отчётов в каталоге ``reports/current/<источник>/``:

1. ``raw_data.png``            — исходные данные;
2. ``processed_data.png``      — данные после очистки/нормализации;
3. ``features_data.png``       — сформированные признаки;
4. ``anomaly_distribution.png``— распределение меток аномалий;
5. ``dataset_summary.png``     — сводный отчёт по набору данных.

Используется неинтерактивный backend ``Agg`` (графики сохраняются в файлы).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import logging

import matplotlib

matplotlib.use("Agg")  # noqa: E402 - backend нужно выбрать до импорта pyplot

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

# Подавляем подробные служебные сообщения matplotlib.
logging.getLogger("matplotlib").setLevel(logging.WARNING)

from etl.features.feature_engineering import FEATURE_COLUMNS  # noqa: E402
from etl.logging_config import get_logger  # noqa: E402
from etl.schema import (  # noqa: E402
    LABEL,
    METRIC_NAME,
    SERVICE,
    SOURCE,
    TIMESTAMP,
    VALUE,
)

logger = get_logger(__name__)

REPORT_FILES: Dict[str, str] = {
    "raw": "raw_data.png",
    "processed": "processed_data.png",
    "features": "features_data.png",
    "anomaly": "anomaly_distribution.png",
    "summary": "dataset_summary.png",
}

_GROUP_KEYS = [SOURCE, SERVICE, METRIC_NAME]
_MAX_SERIES = 4  # сколько временных рядов рисовать на графиках динамики


def _pick_series(df: pd.DataFrame, limit: int = _MAX_SERIES) -> list[tuple]:
    """Выбрать наиболее «насыщенные» временные ряды для отрисовки."""

    if df.empty:
        return []
    sizes = df.groupby(_GROUP_KEYS, dropna=False).size().sort_values(ascending=False)
    return list(sizes.head(limit).index)


def _series_label(key: tuple) -> str:
    source, service, metric = key
    return f"{source}/{service}/{metric}"


def _coerce_time(df: pd.DataFrame) -> pd.DataFrame:
    """Привести ``timestamp`` к datetime (RAW NAB хранит время строкой).

    Это исключает конфликт конвертеров осей matplotlib при отрисовке рядов
    из разных источников (строки + datetime) на одном графике.
    """

    if TIMESTAMP not in df.columns:
        return df
    out = df.copy()
    out[TIMESTAMP] = pd.to_datetime(out[TIMESTAMP], errors="coerce")
    return out


def _save(fig: "plt.Figure", path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    logger.info("Сохранён график: %s", path)
    return path


def plot_timeseries(df: pd.DataFrame, path: Path, title: str) -> Path:
    """Построить график динамики значения по нескольким рядам."""

    fig, ax = plt.subplots(figsize=(11, 5))
    df = _coerce_time(df)
    keys = _pick_series(df)

    if not keys:
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center")
    else:
        for key in keys:
            mask = (
                (df[SOURCE] == key[0])
                & (df[SERVICE] == key[1])
                & (df[METRIC_NAME] == key[2])
            )
            series = df.loc[mask].sort_values(TIMESTAMP)
            ax.plot(
                series[TIMESTAMP],
                series[VALUE],
                label=_series_label(key),
                linewidth=1.0,
            )
        ax.legend(loc="upper right", fontsize=8)

    ax.set_title(title)
    ax.set_xlabel("Время")
    ax.set_ylabel("Значение метрики")
    ax.grid(True, alpha=0.3)
    return _save(fig, path)


def plot_features(df: pd.DataFrame, path: Path) -> Path:
    """Построить график значения и скользящих статистик для одного ряда."""

    fig, ax = plt.subplots(figsize=(11, 5))
    df = _coerce_time(df)
    keys = _pick_series(df, limit=1)

    if not keys:
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center")
    else:
        key = keys[0]
        mask = (
            (df[SOURCE] == key[0])
            & (df[SERVICE] == key[1])
            & (df[METRIC_NAME] == key[2])
        )
        series = df.loc[mask].sort_values(TIMESTAMP)
        ax.plot(series[TIMESTAMP], series[VALUE], label="value", linewidth=1.0)
        for feature in ("rolling_mean_5", "rolling_mean_15"):
            if feature in series.columns:
                ax.plot(
                    series[TIMESTAMP], series[feature], label=feature, linewidth=1.0
                )
        if "rolling_std_5" in series.columns:
            ax.fill_between(
                series[TIMESTAMP],
                series["rolling_mean_5"] - series["rolling_std_5"],
                series["rolling_mean_5"] + series["rolling_std_5"],
                alpha=0.15,
                label="±std_5",
            )
        ax.set_title(f"Признаки временного ряда: {_series_label(key)}")
        ax.legend(loc="upper right", fontsize=8)

    ax.set_xlabel("Время")
    ax.set_ylabel("Значение")
    ax.grid(True, alpha=0.3)
    return _save(fig, path)


def plot_anomaly_distribution(df: pd.DataFrame, path: Path) -> Path:
    """Построить распределение меток аномалий."""

    fig, ax = plt.subplots(figsize=(8, 5))

    label_names = {0: "норма (0)", 1: "аномалия (1)", -1: "неизвестно (-1)"}
    if df.empty or LABEL not in df.columns:
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center")
    else:
        counts = df[LABEL].value_counts().sort_index()
        labels = [label_names.get(int(idx), str(idx)) for idx in counts.index]
        colors = ["#4caf50", "#e53935", "#9e9e9e"][: len(counts)]
        bars = ax.bar(labels, counts.values, color=colors)
        for rect, count in zip(bars, counts.values):
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                rect.get_height(),
                f"{int(count)}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    ax.set_title("Распределение меток аномалий")
    ax.set_ylabel("Количество точек")
    ax.grid(True, axis="y", alpha=0.3)
    return _save(fig, path)


def plot_summary(df: pd.DataFrame, path: Path) -> Path:
    """Построить сводный отчёт: строки по источникам и метрикам."""

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    if df.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "Нет данных", ha="center", va="center")
    else:
        by_source = df[SOURCE].value_counts()
        axes[0].bar(by_source.index, by_source.values, color="#1976d2")
        axes[0].set_title("Строк по источникам")
        axes[0].set_ylabel("Количество строк")
        axes[0].grid(True, axis="y", alpha=0.3)

        by_metric = df[METRIC_NAME].value_counts().head(10)
        axes[1].barh(by_metric.index[::-1], by_metric.values[::-1], color="#7b1fa2")
        axes[1].set_title("Топ метрик (metric_name)")
        axes[1].set_xlabel("Количество строк")
        axes[1].grid(True, axis="x", alpha=0.3)

    fig.suptitle("Сводный отчёт по итоговому набору данных")
    return _save(fig, path)


def generate_reports(
    raw_df: pd.DataFrame,
    processed_df: pd.DataFrame,
    features_df: pd.DataFrame,
    reports_dir: Path,
) -> Dict[str, Path]:
    """Построить все отчёты и вернуть пути к ним.

    Args:
        raw_df: Исходные данные (RAW).
        processed_df: Данные после нормализации (PROCESSED).
        features_df: Данные с признаками (ML-набор).
        reports_dir: Каталог для сохранения графиков.

    Returns:
        Словарь ``{ключ: путь}`` с путями к созданным графикам.
    """

    reports_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Построение отчётов в %s", reports_dir)

    paths: Dict[str, Path] = {}
    paths["raw"] = plot_timeseries(
        raw_df, reports_dir / REPORT_FILES["raw"], "Исходные данные (RAW)"
    )
    paths["processed"] = plot_timeseries(
        processed_df,
        reports_dir / REPORT_FILES["processed"],
        "Данные после очистки (PROCESSED)",
    )
    paths["features"] = plot_features(
        features_df, reports_dir / REPORT_FILES["features"]
    )
    paths["anomaly"] = plot_anomaly_distribution(
        features_df, reports_dir / REPORT_FILES["anomaly"]
    )
    paths["summary"] = plot_summary(
        features_df, reports_dir / REPORT_FILES["summary"]
    )
    return paths
