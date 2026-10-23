"""Графики сравнения детекторов. Только файлы, без ``plt.show()``.

Главная метрика на рисунках — PR-AUC. ROC сохраняется справочно.
Backend matplotlib — ``Agg``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    auc,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_curve,
)

from ml.metrics import labeled_mask  # noqa: E402

#: Цвета моделей на общих графиках.
MODEL_COLORS = {
    "zscore": "#4c78a8",
    "iqr": "#72b7b2",
    "iforest": "#f58518",
    "lof": "#54a24b",
    "ocsvm": "#e45756",
    "knn": "#b279a2",
    "pca": "#ff9da6",
    "hbos": "#9d755d",
    "mahalanobis": "#bab0ac",
    "elliptic": "#499894",
    "gmm": "#d67195",
    "kmeans": "#79706e",
}

Curve = Tuple[str, np.ndarray, np.ndarray]


def labeled_predictions(
    y_true: np.ndarray,
    y_score: np.ndarray,
    y_pred: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Оставить точки с меткой 0/1 — те же, что входят в PR-AUC."""

    mask = labeled_mask(y_true)
    y = pd.to_numeric(pd.Series(np.asarray(y_true)[mask]), errors="coerce").to_numpy(dtype="int64")
    score = np.asarray(y_score, dtype="float64")[mask]
    pred_num = pd.to_numeric(pd.Series(np.asarray(y_pred)[mask]), errors="coerce").fillna(0)
    pred = (pred_num.to_numpy() == 1).astype("int64")
    return y, score, pred


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def _color(model: str, index: int) -> str:
    if model in MODEL_COLORS:
        return MODEL_COLORS[model]
    cycle = plt.rcParams["axes.prop_cycle"].by_key().get("color", ["#333333"])
    return cycle[index % len(cycle)]


def _binary_ready(y_true: np.ndarray) -> bool:
    return y_true.size > 0 and np.unique(y_true).size >= 2


def save_confusion_png(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    path: Path,
    *,
    title: str,
) -> Path:
    """Матрица ошибок по бинарным предсказаниям (0 — норма, 1 — аномалия)."""

    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    ax.set_title(title)
    if y_true.size == 0:
        ax.text(0.5, 0.5, "Нет размеченных точек", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, path)

    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    image = ax.imshow(matrix, cmap="Blues")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks([0, 1], ["норма", "аномалия"])
    ax.set_yticks([0, 1], ["норма", "аномалия"])
    ax.set_xlabel("Предсказание")
    ax.set_ylabel("Факт")
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            value = int(matrix[row, col])
            color = "white" if value > matrix.max() / 2 else "black"
            ax.text(col, row, str(value), ha="center", va="center", color=color)
    return _save(fig, path)


def save_pr_png(
    y_true: np.ndarray,
    y_score: np.ndarray,
    path: Path,
    *,
    title: str,
) -> Path:
    """PR-кривая одной модели. Ось X — полнота, ось Y — точность."""

    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    ax.set_title(title)
    if not _binary_ready(y_true):
        ax.text(0.5, 0.5, "PR-кривая не определена: в тесте один класс", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, path)

    precision, recall, _thresholds = precision_recall_curve(y_true, y_score)
    ap = float(average_precision_score(y_true, y_score))
    ax.plot(recall, precision, color="#3b6d99", lw=2, label=f"PR-AUC = {ap:.3f}")
    baseline = float(np.mean(y_true))
    ax.hlines(
        baseline,
        0.0,
        1.0,
        colors="#888888",
        linestyles="--",
        label=f"доля аномалий = {baseline:.3f}",
    )
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.05)
    ax.set_xlabel("Полнота")
    ax.set_ylabel("Точность")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    return _save(fig, path)


def save_pr_overlay(
    curves: Sequence[Curve],
    path: Path,
    *,
    title: str,
) -> Path:
    """Общие PR-кривые всех моделей одного источника."""

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    ax.set_title(title)
    drawn = 0
    for index, (model, y_true, y_score) in enumerate(curves):
        if not _binary_ready(y_true):
            continue
        precision, recall, _thresholds = precision_recall_curve(y_true, y_score)
        ap = float(average_precision_score(y_true, y_score))
        ax.plot(
            recall,
            precision,
            color=_color(model, index),
            lw=2,
            label=f"{model} (PR-AUC={ap:.3f}, n={y_true.size})",
        )
        drawn += 1
    if drawn == 0:
        ax.text(0.5, 0.5, "Нет PR-кривых: в тесте нет обоих классов", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, path)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.05)
    ax.set_xlabel("Полнота")
    ax.set_ylabel("Точность")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    return _save(fig, path)


def save_roc_overlay(
    curves: Sequence[Curve],
    path: Path,
    *,
    title: str,
) -> Optional[Path]:
    """Один ROC на источник. Справочный график: решение принимаем по PR-AUC."""

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    ax.set_title(title)
    drawn = 0
    for index, (model, y_true, y_score) in enumerate(curves):
        if not _binary_ready(y_true):
            continue
        fpr, tpr, _thresholds = roc_curve(y_true, y_score)
        roc_auc = float(auc(fpr, tpr))
        ax.plot(
            fpr,
            tpr,
            color=_color(model, index),
            lw=2,
            label=f"{model} (ROC-AUC={roc_auc:.3f})",
        )
        drawn += 1
    if drawn == 0:
        ax.text(0.5, 0.5, "ROC не определён: в тесте один класс", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, path)
    ax.plot([0.0, 1.0], [0.0, 1.0], color="#888888", ls="--", label="случайный")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.05)
    ax.set_xlabel("Доля ложных срабатываний")
    ax.set_ylabel("Полнота")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    return _save(fig, path)


def save_pr_auc_bars(
    table: pd.DataFrame,
    path: Path,
    *,
    title: str,
) -> Path:
    """Столбики PR-AUC по моделям одного источника."""

    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.set_title(title)
    plot_df = table.dropna(subset=["PR-AUC"]) if "PR-AUC" in table.columns else table.iloc[0:0]
    if plot_df.empty:
        ax.text(0.5, 0.5, "Нет конечного PR-AUC", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, path)

    labels = plot_df["model"].astype(str).tolist()
    values = plot_df["PR-AUC"].astype(float).tolist()
    colors = [_color(label, index) for index, label in enumerate(labels)]
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("PR-AUC")
    ax.set_ylim(0.0, 1.0)
    ax.grid(True, axis="y", alpha=0.3)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            min(value + 0.03, 0.97),
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    return _save(fig, path)
