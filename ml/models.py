"""Обёртки детекторов: ``fit`` только на признаках train, без ``label``.

Признаки — ``value`` + :data:`etl.features.FEATURE_COLUMNS`. Новые колонки
не добавляются. Скейлинг sklearn-моделей — внутри обёртки по train-ряду.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Protocol, Sequence

import numpy as np
from sklearn.cluster import KMeans
from sklearn.covariance import EllipticEnvelope
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import LocalOutlierFactor, NearestNeighbors
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from etl.features.feature_engineering import FEATURE_COLUMNS
from etl.schema import LABEL_ANOMALY, LABEL_NORMAL, VALUE

#: Порядок колонок, подаваемых в ``fit`` / ``score`` / ``predict``.
MODEL_FEATURE_COLUMNS: List[str] = [VALUE, *FEATURE_COLUMNS]

#: Выше этого числа точек train One-Class SVM для ряда не запускается.
OCSVM_MAX_TRAIN: int = 10_000

#: kNN на полном ряде KPI (сотни тысяч точек) не считается.
KNN_MAX_TRAIN: int = 20_000

#: Робастная ковариация Elliptic Envelope оценивается не больше чем на стольких точках.
ELLIPTIC_MAX_FIT: int = 8_000

#: Модели, которые пропускают ряд, если train длиннее порога.
TRAIN_ROW_CAPS: Dict[str, int] = {
    "ocsvm": OCSVM_MAX_TRAIN,
    "knn": KNN_MAX_TRAIN,
}


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


def _high_score_threshold(scores: np.ndarray, percentile: float = 97.5) -> float:
    """Порог бинарного решения: верхний хвост скоров на train."""

    if scores.size == 0:
        return 0.0
    return float(np.percentile(scores, percentile))


class _ScaledScoreDetector:
    """Общий каркас: StandardScaler на train, скор «больше — аномальнее»."""

    name: str = "scaled"

    def __init__(self) -> None:
        self._scaler: Optional[StandardScaler] = None
        self.threshold_: float = 0.0

    def fit(self, X: np.ndarray) -> "_ScaledScoreDetector":
        matrix = _as_float_matrix(X)
        self._scaler = StandardScaler()
        scaled = self._scaler.fit_transform(matrix)
        self._fit_scaled(scaled)
        self.threshold_ = _high_score_threshold(self._score_scaled(scaled))
        return self

    def _fit_scaled(self, scaled: np.ndarray) -> None:
        raise NotImplementedError

    def _score_scaled(self, scaled: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def _transform(self, X: np.ndarray) -> np.ndarray:
        if self._scaler is None:
            raise RuntimeError("Сначала вызовите fit")
        return self._scaler.transform(_as_float_matrix(X))

    def score(self, X: np.ndarray) -> np.ndarray:
        return self._score_scaled(self._transform(X))

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.score(X) > self.threshold_).astype("int64")


class IqrDetector:
    """Baseline Тьюки по колонке ``value``: выход за 1.5·IQR."""

    name = "iqr"

    def __init__(self, fence: float = 1.5) -> None:
        self.fence = float(fence)
        self.q1_: float = 0.0
        self.q3_: float = 0.0
        self.iqr_: float = 1.0

    def fit(self, X: np.ndarray) -> "IqrDetector":
        values = _as_float_matrix(X)[:, 0]
        if values.size == 0:
            return self
        self.q1_, self.q3_ = (float(v) for v in np.percentile(values, [25, 75]))
        width = self.q3_ - self.q1_
        self.iqr_ = width if width > 1e-12 else 1.0
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        values = _as_float_matrix(X)[:, 0]
        below = (self.q1_ - values) / self.iqr_
        above = (values - self.q3_) / self.iqr_
        return np.maximum(below, above)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.score(X) > self.fence).astype("int64")


class MahalanobisDetector(_ScaledScoreDetector):
    """Расстояние Махаланобиса по эмпирической ковариации train-ряда."""

    name = "mahalanobis"

    def __init__(self) -> None:
        super().__init__()
        self.mean_: Optional[np.ndarray] = None
        self.inv_: Optional[np.ndarray] = None

    def _fit_scaled(self, scaled: np.ndarray) -> None:
        self.mean_ = scaled.mean(axis=0)
        cov = np.cov(scaled, rowvar=False)
        if np.ndim(cov) == 0:
            cov = np.array([[float(cov)]], dtype="float64")
        cov = np.atleast_2d(cov) + np.eye(scaled.shape[1]) * 1e-6
        self.inv_ = np.linalg.pinv(cov)

    def _score_scaled(self, scaled: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.inv_ is None:
            raise RuntimeError("Сначала вызовите fit")
        delta = scaled - self.mean_
        quad = np.einsum("ij,jk,ik->i", delta, self.inv_, delta)
        return np.sqrt(np.maximum(quad, 0.0))


class PcaDetector(_ScaledScoreDetector):
    """Ошибка восстановления PCA (компоненты, держащие ~90% дисперсии)."""

    name = "pca"

    def __init__(self) -> None:
        super().__init__()
        self._pca: Optional[PCA] = None

    def _fit_scaled(self, scaled: np.ndarray) -> None:
        n_comp = min(scaled.shape[0], scaled.shape[1], 3)
        n_comp = max(n_comp, 1)
        self._pca = PCA(n_components=n_comp, random_state=42)
        self._pca.fit(scaled)

    def _score_scaled(self, scaled: np.ndarray) -> np.ndarray:
        if self._pca is None:
            raise RuntimeError("Сначала вызовите fit")
        restored = self._pca.inverse_transform(self._pca.transform(scaled))
        error = scaled - restored
        return np.sqrt(np.sum(error * error, axis=1))


class HbosDetector(_ScaledScoreDetector):
    """Histogram-based Outlier Score: редкость по каждой координате."""

    name = "hbos"

    def __init__(self, n_bins: int = 10) -> None:
        super().__init__()
        self.n_bins = n_bins
        self._edges: List[np.ndarray] = []
        self._log_density: List[np.ndarray] = []

    def _fit_scaled(self, scaled: np.ndarray) -> None:
        self._edges = []
        self._log_density = []
        bins = max(2, min(self.n_bins, max(scaled.shape[0] // 2, 2)))
        for col in range(scaled.shape[1]):
            column = scaled[:, col]
            hist, edges = np.histogram(column, bins=bins)
            width = np.diff(edges)
            width = np.where(width > 1e-12, width, 1.0)
            density = hist.astype("float64") / max(hist.sum(), 1) / width
            self._edges.append(edges)
            self._log_density.append(np.log(density + 1e-12))

    def _score_scaled(self, scaled: np.ndarray) -> np.ndarray:
        total = np.zeros(scaled.shape[0], dtype="float64")
        for col, (edges, log_density) in enumerate(zip(self._edges, self._log_density)):
            index = np.digitize(scaled[:, col], edges[1:-1], right=False)
            index = np.clip(index, 0, log_density.size - 1)
            total -= log_density[index]
        return total


class KnnDetector(_ScaledScoreDetector):
    """Расстояние до k-го соседа на train. Ряды длиннее KNN_MAX_TRAIN пропускает runner."""

    name = "knn"

    def __init__(self, n_neighbors: int = 5) -> None:
        super().__init__()
        self.n_neighbors = n_neighbors
        self._neighbors: Optional[NearestNeighbors] = None
        self._k: int = 1

    def _fit_scaled(self, scaled: np.ndarray) -> None:
        if scaled.shape[0] > KNN_MAX_TRAIN:
            raise ValueError(
                f"kNN не запускается на train>{KNN_MAX_TRAIN} (получено {scaled.shape[0]})"
            )
        self._k = max(1, min(self.n_neighbors, scaled.shape[0] - 1))
        self._neighbors = NearestNeighbors(n_neighbors=self._k, algorithm="auto")
        self._neighbors.fit(scaled)

    def _score_scaled(self, scaled: np.ndarray) -> np.ndarray:
        if self._neighbors is None:
            raise RuntimeError("Сначала вызовите fit")
        distances, _ = self._neighbors.kneighbors(scaled)
        return distances[:, -1]


class EllipticDetector(_ScaledScoreDetector):
    """Робастный эллипсоид (MinCovDet). На длинном ряде fit берёт не больше ELLIPTIC_MAX_FIT точек."""

    name = "elliptic"

    def __init__(self) -> None:
        super().__init__()
        self._estimator = None
        self._fallback: Optional[MahalanobisDetector] = None

    def _fit_scaled(self, scaled: np.ndarray) -> None:
        self._fallback = None
        fit_x = scaled
        if scaled.shape[0] > ELLIPTIC_MAX_FIT:
            rng = np.random.RandomState(42)
            picked = rng.choice(scaled.shape[0], ELLIPTIC_MAX_FIT, replace=False)
            fit_x = scaled[picked]
        if fit_x.shape[0] <= fit_x.shape[1] + 1:
            self._use_fallback(fit_x)
            return
        estimator = EllipticEnvelope(
            contamination=0.05,
            random_state=42,
            support_fraction=0.8,
        )
        try:
            estimator.fit(fit_x)
        except ValueError:
            self._use_fallback(fit_x)
            return
        self._estimator = estimator

    def _use_fallback(self, scaled: np.ndarray) -> None:
        self._estimator = None
        fallback = MahalanobisDetector()
        fallback._fit_scaled(scaled)
        self._fallback = fallback

    def _score_scaled(self, scaled: np.ndarray) -> np.ndarray:
        if self._fallback is not None:
            return self._fallback._score_scaled(scaled)
        if self._estimator is None:
            raise RuntimeError("Сначала вызовите fit")
        return -np.asarray(self._estimator.score_samples(scaled), dtype="float64")


class GmmDetector(_ScaledScoreDetector):
    """Одна гауссиана на ряд: скор — минус логарифм плотности."""

    name = "gmm"

    def __init__(self) -> None:
        super().__init__()
        self._gmm: Optional[GaussianMixture] = None

    def _fit_scaled(self, scaled: np.ndarray) -> None:
        self._gmm = GaussianMixture(
            n_components=1,
            covariance_type="full",
            random_state=42,
            reg_covar=1e-6,
        )
        self._gmm.fit(scaled)

    def _score_scaled(self, scaled: np.ndarray) -> np.ndarray:
        if self._gmm is None:
            raise RuntimeError("Сначала вызовите fit")
        return -np.asarray(self._gmm.score_samples(scaled), dtype="float64")


class KMeansDetector(_ScaledScoreDetector):
    """Расстояние до ближайшего центра k-means, обученного на нормальном train."""

    name = "kmeans"

    def __init__(self, n_clusters: int = 4) -> None:
        super().__init__()
        self.n_clusters = n_clusters
        self._centers: Optional[np.ndarray] = None

    def _fit_scaled(self, scaled: np.ndarray) -> None:
        clusters = max(1, min(self.n_clusters, scaled.shape[0]))
        model = KMeans(n_clusters=clusters, random_state=42, n_init=10)
        model.fit(scaled)
        self._centers = np.asarray(model.cluster_centers_, dtype="float64")

    def _score_scaled(self, scaled: np.ndarray) -> np.ndarray:
        if self._centers is None:
            raise RuntimeError("Сначала вызовите fit")
        delta = scaled[:, None, :] - self._centers[None, :, :]
        distances = np.sqrt(np.sum(delta * delta, axis=2))
        return distances.min(axis=1)


def make_detector(name: str) -> Detector:
    """Фабрика по короткому имени модели."""

    catalog: Dict[str, type] = {
        ZScoreDetector.name: ZScoreDetector,
        IqrDetector.name: IqrDetector,
        IsolationForestDetector.name: IsolationForestDetector,
        LOFDetector.name: LOFDetector,
        OCSVMDetector.name: OCSVMDetector,
        KnnDetector.name: KnnDetector,
        PcaDetector.name: PcaDetector,
        HbosDetector.name: HbosDetector,
        MahalanobisDetector.name: MahalanobisDetector,
        EllipticDetector.name: EllipticDetector,
        GmmDetector.name: GmmDetector,
        KMeansDetector.name: KMeansDetector,
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
