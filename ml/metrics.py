"""Метрики качества на размеченном тесте. ``label=-1`` в знаменатель не входит.

PR-AUC, precision и recall считаются только по точкам с ``label`` 0 или 1.
Источники ``PROMETHEUS`` и ``ZABBIX`` пропускаются целиком: у них нет
эталонной разметки.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    precision_score,
    recall_score,
)

from etl.schema import (
    LABEL,
    LABEL_ANOMALY,
    LABEL_NORMAL,
    SOURCE,
    SOURCE_PROMETHEUS,
    SOURCE_ZABBIX,
)

#: Источники без эталонных меток — не считаем PR-AUC / P / R.
UNSCORED_SOURCES = frozenset({SOURCE_PROMETHEUS, SOURCE_ZABBIX})

REPORT_COLUMNS = (
    "model",
    "source",
    "PR-AUC",
    "P",
    "R",
    "n_train",
    "n_test",
)


@dataclass(frozen=True)
class BinaryScores:
    """Результат оценки на точках с label 0/1."""

    pr_auc: float
    precision: float
    recall: float
    n_scored: int
    skipped: bool = False

    def as_report_fields(self) -> Mapping[str, float]:
        return {
            "PR-AUC": self.pr_auc,
            "P": self.precision,
            "R": self.recall,
        }


def is_scored_source(source: object) -> bool:
    """Можно ли считать PR-AUC для этого ``source``."""

    return str(source) not in UNSCORED_SOURCES


def labeled_mask(y_true: np.ndarray) -> np.ndarray:
    """Маска точек с эталонной меткой 0 или 1 (``-1`` отбрасывается)."""

    y = np.asarray(y_true)
    numeric = pd.to_numeric(pd.Series(y), errors="coerce").to_numpy()
    return (numeric == LABEL_NORMAL) | (numeric == LABEL_ANOMALY)


def evaluate_binary(
    y_true: np.ndarray,
    scores: np.ndarray,
    y_pred: np.ndarray,
) -> BinaryScores:
    """PR-AUC по непрерывным скорам, P/R по бинарным предсказаниям.

    Точки с ``label=-1`` и NaN-метками выкидываются. Если после фильтра
    не осталось размеченных точек — ``skipped=True`` и метрики NaN.
    PR-AUC также NaN, если в тесте нет ни одной аномалии (класс 1).
    """

    y = np.asarray(y_true)
    score = np.asarray(scores, dtype="float64")
    pred = np.asarray(y_pred)
    mask = labeled_mask(y)
    if score.shape[0] != y.shape[0] or pred.shape[0] != y.shape[0]:
        raise ValueError("y_true, scores и y_pred должны быть одной длины")

    y_bin = pd.to_numeric(pd.Series(y[mask]), errors="coerce").to_numpy(dtype="int64")
    score = score[mask]
    pred_num = pd.to_numeric(pd.Series(pred[mask]), errors="coerce").fillna(0)
    pred_bin = (pred_num.to_numpy() == LABEL_ANOMALY).astype("int64")

    if y_bin.size == 0:
        return BinaryScores(
            pr_auc=float("nan"),
            precision=float("nan"),
            recall=float("nan"),
            n_scored=0,
            skipped=True,
        )

    if int(np.sum(y_bin == LABEL_ANOMALY)) == 0:
        pr_auc = float("nan")
    else:
        pr_auc = float(average_precision_score(y_bin, score))

    precision = float(precision_score(y_bin, pred_bin, zero_division=0))
    recall = float(recall_score(y_bin, pred_bin, zero_division=0))
    return BinaryScores(
        pr_auc=pr_auc,
        precision=precision,
        recall=recall,
        n_scored=int(y_bin.size),
        skipped=False,
    )


def empty_report() -> pd.DataFrame:
    """Пустая таблица отчёта с фиксированными колонками."""

    return pd.DataFrame(columns=list(REPORT_COLUMNS))


def report_row(
    *,
    model: str,
    source: str,
    scores: BinaryScores,
    n_train: int,
    n_test: int,
) -> dict:
    """Одна строка сводной таблицы runner."""

    return {
        "model": model,
        "source": source,
        "PR-AUC": scores.pr_auc,
        "P": scores.precision,
        "R": scores.recall,
        "n_train": int(n_train),
        "n_test": int(n_test),
    }
