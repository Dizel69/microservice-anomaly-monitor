"""Обёртки детекторов: ``fit`` только на признаках train, без ``label``.

Признаки — ``value`` + :data:`etl.features.FEATURE_COLUMNS`. Новые колонки
не добавляются. Скейлинг sklearn-моделей — внутри обёртки по train-ряду.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Protocol, Sequence

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from etl.features.feature_engineering import FEATURE_COLUMNS
from etl.schema import LABEL_ANOMALY, LABEL_NORMAL, VALUE

#: Порядок колонок, подаваемых в ``fit`` / ``score`` / ``predict``.
MODEL_FEATURE_COLUMNS: List[str] = [VALUE, *FEATURE_COLUMNS]

#: Выше этого числа точек train One-Class SVM для ряда не запускается.
OCSVM_MAX_TRAIN: int = 10_000


class Detector(Protocol):
    """Детектор без учителя: учится на признаках, метки не принимает."""

    name: str

    def fit(self, X: np.ndarray) -> "Detector":
        ...

    def score(self, X: np.ndarray) -> np.ndarray:
        """Непрерывный скор: больше — более аномально."""

        ...

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Бинарные метки 0/1 (1 — аномалия)."""

        ...


def _as_float_matrix(X: np.ndarray) -> np.ndarray:
    matrix = np.asarray(X, dtype="float64")
    if matrix.ndim != 2:
        raise ValueError("Ожидалась матрица признаков формы (n_samples, n_features)")
    return np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)


def _from_sklearn_predict(raw: np.ndarray) -> np.ndarray:
    """sklearn: ``1`` inlier, ``-1`` outlier → ``0`` / ``1``."""

    return np.where(np.asarray(raw) == -1, LABEL_ANOMALY, LABEL_NORMAL).astype("int64")


class ZScoreDetector:
    """Baseline: |z| по колонке ``value`` (индекс 0) на train-ряде."""

    name = "zscore"

    def __init__(self, threshold: float = 3.0) -> None:
        self.threshold = float(threshold)
        self.mean_: float = 0.0
        self.std_: float = 1.0

    def fit(self, X: np.ndarray) -> "ZScoreDetector":
        values = _as_float_matrix(X)[:, 0]
        self.mean_ = float(np.mean(values)) if values.size else 0.0
        std = float(np.std(values, ddof=0)) if values.size else 0.0
        self.std_ = std if std > 1e-12 else 1.0
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        values = _as_float_matrix(X)[:, 0]
        return np.abs(values - self.mean_) / self.std_

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.score(X) > self.threshold).astype("int64")


class _ScaledSklearnDetector:
    """IsolationForest / LOF / OCSVM со StandardScaler, подогнанным на train."""

    name: str = "sklearn"

    def __init__(self) -> None:
        self._scaler: Optional[StandardScaler] = None
        self._estimator = None

    def _build_estimator(self, n_train: int):
        raise NotImplementedError

    def fit(self, X: np.ndarray) -> "_ScaledSklearnDetector":
        matrix = _as_float_matrix(X)
        self._scaler = StandardScaler()
        scaled = self._scaler.fit_transform(matrix)
        self._estimator = self._build_estimator(scaled.shape[0])
        self._estimator.fit(scaled)
        return self

    def _transform(self, X: np.ndarray) -> np.ndarray:
        if self._scaler is None or self._estimator is None:
            raise RuntimeError("Сначала вызовите fit")
        return self._scaler.transform(_as_float_matrix(X))

    def score(self, X: np.ndarray) -> np.ndarray:
        scaled = self._transform(X)
        return -np.asarray(self._estimator.score_samples(scaled), dtype="float64")

    def predict(self, X: np.ndarray) -> np.ndarray:
        scaled = self._transform(X)
        return _from_sklearn_predict(self._estimator.predict(scaled))


class IsolationForestDetector(_ScaledSklearnDetector):
    name = "iforest"

    def __init__(self, random_state: int = 42, n_estimators: int = 100) -> None:
        super().__init__()
        self.random_state = random_state
        self.n_estimators = n_estimators

    def _build_estimator(self, n_train: int) -> IsolationForest:
        return IsolationForest(
            n_estimators=self.n_estimators,
            contamination="auto",
            random_state=self.random_state,
            n_jobs=1,
        )


class LOFDetector(_ScaledSklearnDetector):
    name = "lof"

    def __init__(self, n_neighbors: int = 20) -> None:
        super().__init__()
        self.n_neighbors = n_neighbors

    def _build_estimator(self, n_train: int) -> LocalOutlierFactor:
        neighbors = max(2, min(self.n_neighbors, max(n_train - 1, 2)))
        return LocalOutlierFactor(
            n_neighbors=neighbors,
            novelty=True,
            contamination="auto",
        )


class OCSVMDetector(_ScaledSklearnDetector):
    name = "ocsvm"

    def __init__(self, nu: float = 0.05) -> None:
        super().__init__()
        self.nu = nu

    def _build_estimator(self, n_train: int) -> OneClassSVM:
        if n_train > OCSVM_MAX_TRAIN:
            raise ValueError(
                f"OCSVM не запускается на train>{OCSVM_MAX_TRAIN} (получено {n_train})"
            )
        return OneClassSVM(kernel="rbf", gamma="scale", nu=self.nu)


def make_detector(name: str) -> Detector:
    """Фабрика по короткому имени модели."""

    catalog: Dict[str, type] = {
        ZScoreDetector.name: ZScoreDetector,
        IsolationForestDetector.name: IsolationForestDetector,
        LOFDetector.name: LOFDetector,
        OCSVMDetector.name: OCSVMDetector,
    }
    if name not in catalog:
        known = ", ".join(sorted(catalog))
        raise ValueError(f"Неизвестная модель '{name}'. Доступны: {known}")
    return catalog[name]()


def default_model_names(*, include_ocsvm: bool = False) -> List[str]:
    """Очередь моделей этапа сравнения. OCSVM — только по явному флагу."""

    names = [ZScoreDetector.name, IsolationForestDetector.name, LOFDetector.name]
    if include_ocsvm:
        names.append(OCSVMDetector.name)
    return names


def build_detectors(
    names: Optional[Sequence[str]] = None,
    *,
    include_ocsvm: bool = False,
) -> List[Detector]:
    """Собрать новые экземпляры детекторов (каждый ряд получит свою копию)."""

    chosen: Iterable[str] = names if names is not None else default_model_names(
        include_ocsvm=include_ocsvm
    )
    return [make_detector(name) for name in chosen]
