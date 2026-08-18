"""Модель графа ETL-конвейера для демонстрационного GUI.

Модуль описывает узлы конвейера (входы, шаги обработки, артефакты), связи между
ними и геометрию SVG-схемы. Обработки данных здесь нет: указаны только пути к
артефактам, метаданные которых GUI читает через ``os.stat``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from etl.config import (
    DEFAULT_PATHS,
    PROCESSED_DIR,
    RAW_KPI_DIR,
    RAW_NAB_DIR,
    RAW_PROMETHEUS_DIR,
)
from etl.schema import SOURCE_KPI, SOURCE_NAB, SOURCE_PROMETHEUS

#: Идентификатор узла Prometheus (у него на схеме есть переключатель режима).
PROMETHEUS_NODE_ID: str = "prometheus"


@dataclass(frozen=True)
class FileGroup:
    """Группа файлов, показываемая в карточке узла.

    Если ``pattern`` не задан, ``root`` трактуется как конкретный файл.
    Иначе ``root`` — каталог, который сканируется по маске (``**`` разрешён).
    """

    label: str
    root: Path
    pattern: Optional[str] = None
    limit: int = 10


@dataclass(frozen=True)
class Box:
    """Прямоугольник узла в системе координат SVG."""

    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    @property
    def cx(self) -> int:
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        return self.y + self.h // 2


@dataclass(frozen=True)
class Node:
    """Узел схемы конвейера."""

    id: str
    title: str
    subtitle: str
    #: ``input`` — источник, ``stage`` — шаг обработки, ``output`` — артефакт.
    kind: str
    purpose: str
    box: Box
    #: Дополнительные строки подписи внутри блока.
    lines: Tuple[str, ...] = ()
    inputs: Tuple[FileGroup, ...] = ()
    outputs: Tuple[FileGroup, ...] = ()
    #: Для узлов графиков: ``current`` или ``before`` — какой снимок показывать.
    gallery: Optional[str] = None


#: Геометрия схемы: три колонки (источники / обработка / артефакты).
CANVAS_WIDTH: int = 1240
CANVAS_HEIGHT: int = 560

_LEFT_X, _LEFT_W = 30, 250
_MID_X, _MID_W = 370, 230
_RIGHT_X, _RIGHT_W = 700, 500

COLUMN_TITLES: Tuple[Tuple[int, str], ...] = (
    (_LEFT_X, "ИСТОЧНИКИ ДАННЫХ"),
    (_MID_X, "ОБРАБОТКА"),
    (_RIGHT_X, "АРТЕФАКТЫ"),
)

_NAB_CSV = FileGroup("CSV временных рядов (рекурсивно)", RAW_NAB_DIR, "**/*.csv")
_KPI_CSV = FileGroup("Выгрузки KPI (csv / csv.gz)", RAW_KPI_DIR, "*.csv*")
_PROM_DUMPS = FileGroup("Локальные дампы Prometheus", RAW_PROMETHEUS_DIR, "*.parquet")

_RAW_NAB = FileGroup("RAW: NAB", RAW_NAB_DIR, "raw_*.parquet", limit=6)
_RAW_KPI = FileGroup("RAW: KPI", RAW_KPI_DIR, "raw_*.parquet", limit=6)
_RAW_PROM = FileGroup("RAW: PROMETHEUS", RAW_PROMETHEUS_DIR, "raw_*.parquet", limit=6)

_PROCESSED_NAB = FileGroup(
    "PROCESSED: NAB", PROCESSED_DIR / SOURCE_NAB, "processed_*.parquet", limit=6
)
_PROCESSED_KPI = FileGroup(
    "PROCESSED: KPI", PROCESSED_DIR / SOURCE_KPI, "processed_*.parquet", limit=6
)
_PROCESSED_PROM = FileGroup(
    "PROCESSED: PROMETHEUS",
    PROCESSED_DIR / SOURCE_PROMETHEUS,
    "processed_*.parquet",
    limit=6,
)

_UNIFIED_PARQUET = FileGroup("Единый набор (Parquet)", DEFAULT_PATHS.unified_parquet)
_UNIFIED_CSV = FileGroup("Единый набор (CSV-экспорт)", DEFAULT_PATHS.unified_csv)
_ML_PARQUET = FileGroup("ML-набор (Parquet)", DEFAULT_PATHS.features_parquet)
_ML_CSV = FileGroup("ML-набор (CSV-экспорт)", DEFAULT_PATHS.features_csv)


NODES: Tuple[Node, ...] = (
    Node(
        id="nab",
        title="NAB",
        subtitle="datasets/raw/NAB",
        kind="input",
        purpose=(
            "Входной источник NAB (Numenta Anomaly Benchmark): набор реальных и "
            "синтетических временных рядов в CSV — загрузка процессора EC2, объём "
            "твитов, трафик, показатели рекламных площадок. Разметка аномалий лежит "
            "отдельно, в файле labels/combined_windows.json: точка получает label=1, "
            "если её время попадает в одно из окон аномалии, иначе label=0. Без этого "
            "файла весь источник считался бы нормой — именно эта ошибка видна на "
            "снимке графиков «до»."
        ),
        box=Box(_LEFT_X, 60, _LEFT_W, 90),
        lines=("58 рядов + окна аномалий",),
        inputs=(
            _NAB_CSV,
            FileGroup("Окна аномалий", RAW_NAB_DIR / "labels" / "combined_windows.json"),
            FileGroup("Метки точек (справочно)", RAW_NAB_DIR / "labels" / "combined_labels.json"),
        ),
        outputs=(_RAW_NAB,),
    ),
    Node(
        id="kpi",
        title="KPI",
        subtitle="datasets/raw/KPI",
        kind="input",
        purpose=(
            "Входной источник KPI (AIOps Challenge): сжатые CSV с колонками "
            "KPI ID / timestamp / value / label. Метка аномалии приходит уже готовой "
            "в колонке label, поэтому источник служит эталонной разметкой для обучения. "
            "В репозитории хранится сжатый phase2_train.csv.gz — несжатый файл (176 МБ) "
            "в git не кладётся из-за лимита GitHub."
        ),
        box=Box(_LEFT_X, 185, _LEFT_W, 90),
        lines=("готовая разметка 0/1",),
        inputs=(_KPI_CSV,),
        outputs=(_RAW_KPI,),
    ),
    Node(
        id=PROMETHEUS_NODE_ID,
        title="Prometheus",
        subtitle="datasets/raw/PROMETHEUS",
        kind="input",
        purpose=(
            "Входной источник Prometheus — метрики живой инфраструктуры. Возможны два "
            "режима. LOCAL: конвейер читает ранее сохранённые дампы parquet из "
            "datasets/raw/PROMETHEUS, сеть не нужна — этот режим используется на защите. "
            "URL: конвейер обращается к HTTP API сервера (/api/v1/query_range, при "
            "неудаче /api/v1/query) с указанным PromQL-запросом, шагом и диапазоном. "
            "Разметки аномалий у этого источника нет, поэтому всем точкам "
            "присваивается label=-1 (неизвестно). Сам GUI в сеть не ходит: он только "
            "запоминает выбор и показывает, с чем будет запущен конвейер."
        ),
        box=Box(_LEFT_X, 310, _LEFT_W, 125),
        inputs=(_PROM_DUMPS,),
        outputs=(_RAW_PROM,),
    ),
    Node(
        id="loaders",
        title="loaders",
        subtitle="etl/loaders/",
        kind="stage",
        purpose=(
            "Слой загрузчиков: по одному модулю на источник (nab_loader, kpi_loader, "
            "prometheus_loader). Каждый читает свой формат, определяет имя сервиса и тип "
            "метрики и приводит данные к единой схеме из шести колонок: timestamp, "
            "service, metric_name, value, label, source. Загрузчики также защищены от "
            "путаницы источников: файл KPI, поданный как NAB, будет отклонён. Результат "
            "уровня RAW сохраняется рядом с исходниками в виде raw_<имя>.parquet."
        ),
        box=Box(_MID_X, 95, _MID_W, 90),
        lines=("единая схема 6 колонок",),
        inputs=(_NAB_CSV, _KPI_CSV, _PROM_DUMPS),
        outputs=(_RAW_NAB, _RAW_KPI, _RAW_PROM),
    ),
    Node(
        id="normalize",
        title="normalize",
        subtitle="etl/transformers/",
        kind="stage",
        purpose=(
            "Нормализация и очистка: приведение времени к единому формату, удаление "
            "дублей и пустых значений, приведение типов, сортировка по времени, "
            "унификация имён метрик. Очищенные данные складываются на уровень "
            "PROCESSED по источникам, после чего склеиваются в единый набор UNIFIED."
        ),
        box=Box(_MID_X, 225, _MID_W, 90),
        lines=("очистка, типы, время",),
        inputs=(_RAW_NAB, _RAW_KPI, _RAW_PROM),
        outputs=(_PROCESSED_NAB, _PROCESSED_KPI, _PROCESSED_PROM, _UNIFIED_PARQUET),
    ),
    Node(
        id="features",
        title="features",
        subtitle="etl/features/",
        kind="stage",
        purpose=(
            "Инженерия признаков: для каждого ряда (service + metric_name) считаются "
            "скользящее среднее и скользящее стандартное отклонение, приращение "
            "значения (delta) и относительное изменение (percent_change). На выходе — "
            "ML-набор, готовый для алгоритмов обнаружения аномалий. Обучение моделей "
            "в этот конвейер не входит."
        ),
        box=Box(_MID_X, 355, _MID_W, 90),
        lines=("rolling, delta, %",),
        inputs=(_UNIFIED_PARQUET,),
        outputs=(_ML_PARQUET, _ML_CSV),
    ),
    Node(
        id="unified",
        title="UNIFIED",
        subtitle="datasets/unified/unified_dataset.parquet",
        kind="output",
        purpose=(
            "Единый набор данных: все три источника, приведённые к одной схеме и "
            "склеенные в один файл. Основной формат — Apache Parquet (колоночное "
            "сжатие, быстрое чтение), CSV — экспорт для просмотра сторонними "
            "инструментами. Каталог datasets/unified не хранится в git: он "
            "пересобирается конвейером, поэтому у свежего клона этих файлов нет."
        ),
        box=Box(_RIGHT_X, 55, _RIGHT_W, 88),
        lines=("timestamp, service, metric_name, value, label, source",),
        inputs=(_PROCESSED_NAB, _PROCESSED_KPI, _PROCESSED_PROM),
        outputs=(_UNIFIED_PARQUET, _UNIFIED_CSV),
    ),
    Node(
        id="ml",
        title="ML-набор",
        subtitle="datasets/unified/ml_dataset.parquet",
        kind="output",
        purpose=(
            "Конечный артефакт конвейера: единый набор плюс рассчитанные признаки. "
            "Это вход для алгоритмов обнаружения аномалий. Как и UNIFIED, в git не "
            "хранится и пересобирается командой конвейера."
        ),
        box=Box(_RIGHT_X, 175, _RIGHT_W, 88),
        lines=("UNIFIED + признаки",),
        inputs=(_UNIFIED_PARQUET,),
        outputs=(_ML_PARQUET, _ML_CSV),
    ),
    Node(
        id="reports-current",
        title="Графики current",
        subtitle="reports/current/",
        kind="output",
        purpose=(
            "Графики текущего состояния данных: перестраиваются при каждом прогоне "
            "конвейера. Для каждого источника (NAB, KPI, PROMETHEUS) и для "
            "объединённого набора (combined) строится пять графиков: сырые данные, "
            "обработанные данные, признаки, распределение метрик аномалий и сводка по "
            "набору."
        ),
        box=Box(_RIGHT_X, 295, _RIGHT_W, 88),
        lines=("NAB · KPI · PROMETHEUS · combined",),
        inputs=(_UNIFIED_PARQUET, _ML_PARQUET),
        gallery="current",
    ),
    Node(
        id="reports-before",
        title="Графики before",
        subtitle="reports/before/",
        kind="output",
        purpose=(
            "Снимок графиков «как было» до исправления данных. Конвейер никогда не "
            "пишет в этот каталог, поэтому снимок можно сравнивать с current и "
            "показывать, что именно изменилось: появилась разметка аномалий NAB и "
            "исчезли метрики с именем unknown_metric."
        ),
        box=Box(_RIGHT_X, 415, _RIGHT_W, 110),
        lines=(
            "снимок для выступления, не перезаписывается",
            "конвейер сюда не пишет — только читаем",
        ),
        gallery="before",
    ),
)

NODES_BY_ID: Dict[str, Node] = {node.id: node for node in NODES}


@dataclass(frozen=True)
class Edge:
    """Связь между узлами схемы."""

    src: str
    dst: str
    dashed: bool = False
    label: str = ""


EDGES: Tuple[Edge, ...] = (
    Edge("nab", "loaders"),
    Edge("kpi", "loaders"),
    Edge(PROMETHEUS_NODE_ID, "loaders"),
    Edge("loaders", "normalize"),
    Edge("normalize", "features"),
    Edge("normalize", "unified"),
    Edge("features", "ml"),
    Edge("features", "reports-current"),
    Edge("reports-current", "reports-before", dashed=True, label="сравнение"),
)


def _anchors(src: Box, dst: Box) -> Tuple[int, int, int, int]:
    """Подобрать точки выхода и входа стрелки для пары прямоугольников."""

    if dst.x >= src.right:
        return src.right, src.cy, dst.x, dst.cy
    if dst.y >= src.bottom:
        return src.cx, src.bottom, dst.cx, dst.y
    return src.x, src.cy, dst.right, dst.cy


def edge_lines() -> List[Dict[str, object]]:
    """Посчитать координаты стрелок схемы для шаблона."""

    lines: List[Dict[str, object]] = []
    for edge in EDGES:
        src = NODES_BY_ID[edge.src].box
        dst = NODES_BY_ID[edge.dst].box
        x1, y1, x2, y2 = _anchors(src, dst)
        lines.append(
            {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "dashed": edge.dashed,
                "label": edge.label,
                "label_x": (x1 + x2) // 2,
                "label_y": (y1 + y2) // 2 - 8,
            }
        )
    return lines
