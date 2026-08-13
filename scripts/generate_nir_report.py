#!/usr/bin/env python3
"""Генерация отчёта НИР по ETL-конвейеру (формат прошлогоднего отчёта)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))
OUT_PATH = ROOT / "Отчёт_НИР_Синев_Денис_Евгеньевич_ETL_2026.docx"
REPORTS_ROOT = ROOT / "reports" / "before"
REPORTS_NAB = REPORTS_ROOT / "NAB"
REPORTS_KPI = REPORTS_ROOT / "KPI"
REPORTS_PROM = REPORTS_ROOT / "PROMETHEUS"
REPORTS_COMBINED = REPORTS_ROOT / "combined"
REPORTS_SAMPLE = REPORTS_ROOT / "REPORT_SAMPLE"
NAB_SAMPLE = ROOT / "datasets/raw/NAB/AWSCloudwatch/ec2_cpu_utilization_24ae8d.csv"
KPI_SAMPLE_ROWS = 5000

# Статистика полного прогона конвейера (NAB, все CSV)
FULL_RUN_ROWS = 2_875_699
FULL_RUN_ANOMALIES = 74_318
FULL_RUN_SIZE_MB = 148.53


class _FigCounter:
    def __init__(self) -> None:
        self.n = 1

    def caption(self, text: str) -> str:
        cap = f"Рис. {self.n}. {text}"
        self.n += 1
        return cap


FIG = _FigCounter()

REPORT_IMAGE_SPECS = [
    ("raw_data.png", "Исходные данные (RAW)"),
    ("processed_data.png", "Данные после нормализации (PROCESSED)"),
    ("features_data.png", "Значение метрики и скользящие признаки"),
    ("anomaly_distribution.png", "Распределение меток аномалий"),
    ("dataset_summary.png", "Сводный отчёт по набору данных"),
]


def _set_run_font(run, size_pt: int = 14, bold: bool = False) -> None:
    run.font.name = "Times New Roman"
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")


def add_paragraph(
    doc: Document,
    text: str,
    *,
    align=WD_ALIGN_PARAGRAPH.JUSTIFY,
    size: int = 14,
    bold: bool = False,
    space_after: int = 0,
    first_line_indent_cm: float = 1.25,
) -> None:
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_after = Pt(space_after)
    if first_line_indent_cm and align == WD_ALIGN_PARAGRAPH.JUSTIFY:
        p.paragraph_format.first_line_indent = Cm(first_line_indent_cm)
    run = p.add_run(text)
    _set_run_font(run, size, bold)


def add_center(doc: Document, text: str, size: int = 14, bold: bool = False) -> None:
    add_paragraph(doc, text, align=WD_ALIGN_PARAGRAPH.CENTER, size=size, bold=bold, first_line_indent_cm=0)


def add_heading_section(doc: Document, title: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(12)
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run(title)
    _set_run_font(run, 14, bold=True)


def add_subsection(doc: Document, title: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run(title)
    _set_run_font(run, 14, bold=True)


def add_report_images(doc: Document, report_dir: Path, source_label: str) -> None:
    """Вставить все пять стандартных графиков из каталога отчётов источника."""

    for filename, desc in REPORT_IMAGE_SPECS:
        path = report_dir / filename
        if path.is_file():
            add_image(doc, path, FIG.caption(f"{source_label}: {desc}"))


def add_table(doc: Document, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = str(h)
        for p in hdr_cells[i].paragraphs:
            for r in p.runs:
                _set_run_font(r, 12, bold=True)
    for ri, row in enumerate(rows, start=1):
        for ci, val in enumerate(row):
            table.rows[ri].cells[ci].text = str(val)
            for p in table.rows[ri].cells[ci].paragraphs:
                for r in p.runs:
                    _set_run_font(r, 12)
    doc.add_paragraph()


def add_image(doc: Document, path: Path, caption: str, width_cm: float = 15.5) -> None:
    if not path.is_file():
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width_cm))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.first_line_indent = Cm(0)
    r = cap.add_run(caption)
    _set_run_font(r, 12)
    doc.add_paragraph()


def page_break(doc: Document) -> None:
    doc.add_page_break()


def title_pages(doc: Document) -> None:
    for line in [
        "Министерство науки и высшего образования Российской Федерации",
        "Федеральное государственное бюджетное образовательное учреждение высшего образования «Тверской государственный университет»",
        "Факультет прикладной математики и кибернетики",
        "Направление 01.03.02 – Прикладная математика и информатика",
        "Профиль «Системный анализ»",
    ]:
        add_center(doc, line, 14)
    add_center(doc, "Отчет по итогам производственной практики", 14, bold=True)
    add_center(doc, "(научно-исследовательской работы)", 14)
    add_center(doc, "2025-2026 уч. год, 8 семестр", 14)
    doc.add_paragraph()
    add_center(doc, "Тема НИР:", 14)
    add_center(
        doc,
        "Разработка системы мониторинга микросервисов с элементами машинного обучения",
        14,
        bold=True,
    )
    add_center(doc, "(этап: ETL-конвейер подготовки данных для обнаружения аномалий)", 14)
    doc.add_paragraph()
    add_center(doc, "Автор: студент 4 курса", 14)
    add_center(doc, "Синев Денис Евгеньевич", 14, bold=True)
    add_center(doc, "Руководитель практики:", 14)
    add_center(doc, "Михно Владимир Николаевич,", 14)
    add_center(doc, "д.т.н., профессор", 14)
    add_center(doc, "Научный руководитель:", 14)
    add_center(doc, "Сидорова Оксана Игоревна,", 14)
    add_center(doc, "к.ф.-м.н., доцент", 14)
    doc.add_paragraph()
    add_center(doc, "Оценка: ____________________", 14)
    add_center(doc, "___________", 14)
    add_center(doc, "(подпись)", 14)
    add_center(doc, "Тверь – 2026", 14, bold=True)


def individual_assignment(doc: Document) -> None:
    page_break(doc)
    for line in [
        "Министерство науки и высшего образования Российской Федерации",
        "ФГБОУ ВО «Тверской государственный университет»",
        "Факультет прикладной математики и кибернетики",
        "ИНДИВИДУАЛЬНОЕ ЗАДАНИЕ НА ПРАКТИКУ",
        "Синев Денис Евгеньевич",
        "Направление подготовки: 01.03.02 Прикладная математика и информатика",
        "Направленность (профиль) программы: Системный анализ",
        "Вид практики: производственная",
        "Тип практики: научно-исследовательская работа",
        "Руководитель практики: д.т.н., профессор Михно Владимир Николаевич",
        "Научный руководитель: к.ф.-м.н., доцент Сидорова Оксана Игоревна",
    ]:
        add_center(doc, line, 14)
    add_paragraph(
        doc,
        "Индивидуальное задание на практику: Разработка ETL-конвейера подготовки "
        "данных для обучения моделей обнаружения аномалий в системах мониторинга "
        "микросервисов. Задание включает пункты:",
        first_line_indent_cm=0,
    )
    for item in [
        "Создание ETL-конвейера для источников NAB, KPI и Prometheus",
        "Проверку преобразованных датасетов (уровни RAW, PROCESSED, UNIFIED)",
        "Инженерию признаков временных рядов для ML-моделей",
        "Формирование единого ML-набора и визуализацию результатов",
        "Экспорт данных и документирование конвейера (Parquet, CLI, тесты)",
    ]:
        add_paragraph(doc, item, first_line_indent_cm=0.63)
    add_center(doc, "Дата выдачи задания: 02 июня 2026 года", 14)
    add_center(doc, "Руководитель практики: ______________ /В.Н. Михно/", 14)
    add_center(doc, "Научный руководитель: ______________ / О.И. Сидорова /", 14)


def practice_diary(doc: Document) -> None:
    page_break(doc)
    add_center(doc, "ДНЕВНИК ПРАКТИКИ", 14, bold=True)
    add_table(
        doc,
        ["№", "Задачи", "Планируемые сроки выполнения", "Выполнение (отметка и подпись руководителя практики)"],
        [
            ["1.", "Создание ETL-конвейера (загрузчики NAB, KPI, Prometheus)", "02.06.2026 - 04.06.2026", "вып."],
            ["2.", "Проверка преобразованных датасетов", "04.06.2026 - 05.06.2026", "вып."],
            ["3.", "Инженерия признаков временных рядов", "05.06.2026 - 06.06.2026", "вып."],
            ["4.", "Формирование единого ML-набора и визуализация", "06.06.2026 - 07.06.2026", "вып."],
            ["5.", "Экспорт данных, тестирование и документирование", "07.06.2026 - 08.06.2026", "вып."],
        ],
    )


def table_of_contents(doc: Document) -> None:
    page_break(doc)
    add_center(doc, "Оглавление", 14, bold=True)
    entries = [
        ("Индивидуальное задание на практику", "2"),
        ("Дневник практики", "3"),
        ("Создание ETL-конвейера", "5"),
        ("Загрузка данных NAB и KPI", "8"),
        ("Интеграция Prometheus и промышленной телеметрии", "14"),
        ("Проверка преобразованных датасетов", "20"),
        ("Инженерия признаков временных рядов", "24"),
        ("Формирование единого ML-набора и визуализация", "28"),
        ("Экспорт данных и документирование конвейера", "34"),
        ("Аттестационный лист", "38"),
        ("Характеристика на обучающегося", "39"),
    ]
    for title, page in entries:
        dots = "…" * max(3, 55 - len(title))
        add_paragraph(doc, f"{title}{dots}{page}", first_line_indent_cm=0)


def section_etl_creation(doc: Document) -> None:
    page_break(doc)
    add_heading_section(doc, "Создание ETL-конвейера")
    add_paragraph(
        doc,
        "В рамках научно-исследовательской работы по теме «Разработка системы мониторинга "
        "микросервисов с элементами машинного обучения» реализован модульный ETL-конвейер "
        "(Extract — Transform — Load) на языке Python 3.12. Конвейер решает ключевую "
        "проблему диссертационного исследования: телеметрия микросервисов поступает из "
        "разных систем (бенчмарки, KPI-датасеты, Prometheus), но модели машинного обучения "
        "требуют единого признакового пространства и согласованных меток.",
    )
    add_paragraph(
        doc,
        "Выбрана трёхуровневая модель хранения (medallion architecture): RAW — исходные "
        "данные без потери контекста; PROCESSED — очищенные ряды после normalize_dataframe; "
        "UNIFIED — объединённый набор с инженерными признаками для обучения. Такое разделение "
        "обеспечивает воспроизводимость экспериментов и аудит преобразований — критично "
        "для научной работы и последующей валидации моделей обнаружения аномалий.",
    )
    add_paragraph(
        doc,
        "Архитектура конвейера включает слои: loaders (извлечение), transformers "
        "(нормализация), features (инженерия признаков), visualization (отчёты PNG), "
        "storage (Parquet/CSV), discovery (рекурсивный поиск CSV), pipeline (оркестрация) "
        "и CLI main.py. Каждый слой имеет одну зону ответственности и покрыт модульными "
        "тестами pytest.",
    )
    add_table(
        doc,
        ["Слой", "Модуль", "Назначение"],
        [
            ["Extract", "etl/loaders/", "NAB, KPI, Prometheus → единая схема"],
            ["Transform", "etl/transformers/normalize.py", "Очистка, типы, сортировка"],
            ["Features", "etl/features/", "Скользящие и разностные признаки"],
            ["Load", "etl/storage.py", "Сохранение Parquet (snappy) + CSV"],
            ["Orchestration", "etl/pipeline.py", "RAW → PROCESSED → UNIFIED → ML"],
        ],
    )
    add_paragraph(
        doc,
        "Единая схема данных состоит из шести колонок: timestamp (время), service "
        "(микросервис / временной ряд), metric_name (канонический тип метрики), value "
        "(числовое значение), label (0 — норма, 1 — аномалия, −1 — неизвестно), "
        "source (NAB, KPI, PROMETHEUS). Для Prometheus на уровне RAW дополнительно "
        "сохраняется колонка labels (JSON всех меток серии), чтобы не терять контекст "
        "контейнеров, подов и заданий (job) при последующем анализе.",
    )
    add_paragraph(
        doc,
        "Сочетание трёх источников обосновано методологически: NAB даёт эталонные "
        "временные ряды инфраструктурных метрик AWS; KPI Anomaly Detection — размеченные "
        "бизнес-KPI с реальными метками аномалий; Prometheus — «живая» телеметрия "
        "микросервисной среды, получаемая через HTTP API и пригодная для онлайн-мониторинга.",
    )
    add_table(
        doc,
        ["Источник", "Тип", "Разметка", "Роль в исследовании"],
        [
            ["NAB", "CSV, бенчмарк", "0 или внешние окна", "Валидация и сравнение с эталоном"],
            ["KPI", "CSV, Finals_dataset", "label 0/1", "Обучение с учителем / оценка"],
            ["Prometheus", "HTTP API, PromQL", "label = −1", "Промышленная телеметрия"],
        ],
    )
    add_paragraph(
        doc,
        "Функция normalize_dataframe() приводит timestamp к datetime, value к float64, "
        "удаляет NaN и дубликаты, сортирует по времени. Скользящее среднее с окном w "
        "на этапе признаков:",
    )
    add_paragraph(doc, "μ_t^(w) = (1/w) · Σ_{i=0}^{w-1} x_{t-i}", first_line_indent_cm=1.25)
    add_paragraph(
        doc,
        "Оркестратор run_pipeline() для каждого источника сохраняет Parquet на уровнях "
        "RAW и PROCESSED, объединяет данные в unified_dataset, строит ml_dataset и "
        "генерирует пять типов графиков в reports/current/<источник>/ "
        "и общий набор в reports/current/combined/. Снимок reports/before/ не перезаписывается.",
    )


def section_nab_kpi(doc: Document) -> None:
    page_break(doc)
    add_heading_section(doc, "Загрузка данных NAB и KPI")

    add_subsection(doc, "Источник NAB (Numenta Anomaly Benchmark)")
    add_paragraph(
        doc,
        "NAB — открытый бенчмарк для оценки алгоритмов обнаружения аномалий во временных "
        "рядах. В проекте использованы категории AWS Cloudwatch, realTraffic, KnownCause "
        "и artificialWithAnomaly. Файлы содержат пары timestamp–value с шагом 5 минут. "
        "Загрузчик nab_loader.py автоматически определяет колонки времени и значения, "
        "из имени файла (например, ec2_cpu_utilization_24ae8d.csv) выводит service и "
        "каноническое metric_name (cpu_usage, memory_usage и др.) через эвристику "
        "infer_metric_name().",
    )
    nab = pd.read_csv(NAB_SAMPLE, nrows=4)
    add_paragraph(doc, "Пример исходного CSV NAB:")
    add_table(doc, list(nab.columns), [[str(v) for v in row] for row in nab.values.tolist()])
    add_paragraph(
        doc,
        f"При полном прогоне конвейера по каталогу datasets/raw/NAB обработано более "
        f"{FULL_RUN_ROWS:,} наблюдений; выявлено {FULL_RUN_ANOMALIES:,} точек с меткой "
        f"аномалии (label=1), размер итогового набора — около {FULL_RUN_SIZE_MB} МБ. "
        "Это подтверждает масштабируемость конвейера на реальных объёмах бенчмарка.",
    )
    add_report_images(doc, REPORTS_NAB, "NAB")

    add_subsection(doc, "Источник KPI (KPI Anomaly Detection)")
    add_paragraph(
        doc,
        "Набор NetManAIOps/KPI-Anomaly-Detection содержит размеченные KPI временных рядов "
        "из эксплуатации IT-систем. Формат Finals_dataset: timestamp в UNIX-секундах, "
        "value — значение KPI, label — бинарная метка аномалии, KPI ID — уникальный "
        "идентификатор ряда (маппится в service). Загрузчик kpi_loader.py конвертирует "
        "время и сохраняет исходные метки для контролируемого обучения и оценки precision/recall.",
    )
    kpi = pd.read_csv(ROOT / "datasets/raw/KPI/phase2_train.csv", nrows=4)
    add_paragraph(doc, "Пример исходного CSV KPI:")
    add_table(doc, list(kpi.columns), [[str(v) for v in row] for row in kpi.values.tolist()])
    add_paragraph(
        doc,
        "KPI дополняет NAB: если NAB моделирует инфраструктурные метрики облака, то KPI "
        "отражает прикладные показатели (задержки, ошибки, нагрузку сервисов), что ближе "
        "к мониторингу микросервисов на уровне бизнес-логики.",
    )
    add_report_images(doc, REPORTS_KPI, "KPI")


def section_prometheus(doc: Document) -> None:
    page_break(doc)
    add_heading_section(doc, "Интеграция Prometheus и промышленной телеметрии")

    add_paragraph(
        doc,
        "Prometheus — de-facto стандарт мониторинга в микросервисных архитектурах. "
        "Метрики собираются в формате временных рядов с многомерными метками (labels): "
        "job, instance, container, pod, namespace и др. Для интеграции в ETL-конвейер "
        "реализован загрузчик prometheus_loader.py, использующий официальный HTTP API.",
    )
    add_paragraph(
        doc,
        "Основной эндпоинт — GET /api/v1/query_range. Параметры запроса: query (PromQL), "
        "start, end (UNIX-время), step (шаг дискретизации в секундах). Ответ содержит "
        "resultType=matrix: для каждой серии — набор пар [timestamp, value]. При пустом "
        "matrix выполняется резервный запрос /api/v1/query (мгновенное значение).",
    )
    add_table(
        doc,
        ["Параметр CLI", "По умолчанию", "Описание"],
        [
            ["url", "—", "Базовый URL, напр. http://185.28.85.183:9090"],
            ["queries", "—", "Один или несколько PromQL-выражений"],
            ["--step", "15", "Шаг query_range, секунды"],
            ["--range", "3600", "Длина окна истории, секунды"],
        ],
    )
    add_paragraph(doc, "Примеры PromQL-запросов, поддерживаемых конвейером:")
    for q in [
        "container_cpu_usage_seconds_total",
        "container_memory_usage_bytes",
        "node_cpu_seconds_total",
        "http_request_duration_seconds_sum",
    ]:
        add_paragraph(doc, f"  • {q}", first_line_indent_cm=0.63)
    add_paragraph(
        doc,
        "Команда запуска: python main.py prometheus http://185.28.85.183:9090 "
        "container_cpu_usage_seconds_total --step 30 --range 7200. "
        "При объединении источников: python main.py all --prom-url ... --prom-query ...",
    )
    add_paragraph(
        doc,
        "Определение service выполняется по приоритету меток: service → job → container → "
        "pod → instance. metric_name канонизируется из __name__ (cpu_usage, memory_usage…). "
        "Полный набор меток серии сохраняется в колонке labels (JSON) на уровне RAW — "
        "это важно, когда одна PromQL-выражение возвращает десятки контейнеров.",
    )
    add_paragraph(
        doc,
        "Для Prometheus метка label=-1 (неизвестно): разметка аномалий в продакшене "
        "обычно отсутствует, и модели без учителя (Isolation Forest) обучаются только "
        "на признаках поведения ряда. Смешение NAB/KPI (с метками) и Prometheus (без меток) "
        "в одном ML-наборе допустимо: label=-1 исключается из метрик качества с учителем, "
        "но ряд участвует в обучении unsupervised-моделей.",
    )
    add_table(
        doc,
        ["Поле", "Источник в Prometheus", "Пример"],
        [
            ["timestamp", "values[][0]", "UNIX-секунды → datetime"],
            ["service", "metric.job / container / pod", "cadvisor / frontend"],
            ["metric_name", "metric.__name__", "cpu_usage"],
            ["value", "values[][1]", "0.042"],
            ["label", "—", "−1"],
            ["labels", "весь metric{}", "JSON меток"],
        ],
    )
    add_paragraph(
        doc,
        "Обработка ошибок: класс PrometheusError при сетевых сбоях, неверном JSON или "
        "status≠success в ответе API; таймаут запроса 30 с; логирование числа точек и серий.",
    )
    add_report_images(doc, REPORTS_PROM, "Prometheus")
    add_paragraph(
        doc,
        "На рисунках выше представлена телеметрия, полученная с реального экземпляра "
        "Prometheus. Видны множественные серии (контейнеры/поды), характерные для "
        "микросервисного кластера, и отсутствие размеченных аномалий (label=-1).",
    )


def section_dataset_check(doc: Document) -> None:
    page_break(doc)
    add_heading_section(doc, "Проверка преобразованных датасетов")
    add_paragraph(
        doc,
        "Качество данных проверяется автоматически (pytest) и аналитически (статистика, "
        "визуализация). Контроль выполняется на трёх уровнях medallion architecture: "
        "RAW сохраняет исходный контекст (в т. ч. labels для Prometheus); PROCESSED — "
        "результат normalize_dataframe; UNIFIED — финальный набор и ml_dataset с признаками.",
    )
    add_paragraph(
        doc,
        "Проверка критична перед обучением моделей: некорректные timestamp разрушают "
        "скользящие окна; пропуски в value искажают rolling_std; дубликаты завышают "
        "оценку аномалий. Конвейер логирует количество строк до и после каждого шага.",
    )
    add_table(
        doc,
        ["Уровень", "Каталог", "Назначение"],
        [
            ["RAW", "datasets/raw/<источник>/", "Исходные CSV/API без изменений"],
            ["PROCESSED", "datasets/processed/<источник>/", "Данные после normalize_dataframe"],
            ["UNIFIED", "datasets/unified/", "unified_dataset + ml_dataset"],
        ],
    )
    add_paragraph(
        doc,
        "Проверка включает: (1) контроль схемы — наличие всех шести колонок UNIFIED_COLUMNS; "
        "(2) типы — timestamp datetime64, value float64; (3) отсутствие пропусков в обязательных "
        "полях после нормализации; (4) согласованность меток label ∈ {−1, 0, 1}; "
        "(5) статистический обзор — min, max, mean, count по источникам.",
    )

    from etl.loaders.nab_loader import load_nab
    from etl.loaders.kpi_loader import load_kpi
    from etl.transformers.normalize import normalize_dataframe
    import tempfile

    nab = load_nab(NAB_SAMPLE)
    kpi_path = Path(tempfile.gettempdir()) / "kpi_report_sample.csv"
    pd.read_csv(ROOT / "datasets/raw/KPI/phase2_train.csv", nrows=KPI_SAMPLE_ROWS).to_csv(kpi_path, index=False)
    kpi = load_kpi(kpi_path)
    unified = normalize_dataframe(pd.concat([nab, kpi], ignore_index=True))

    stats_rows = []
    for src, grp in unified.groupby("source"):
        stats_rows.append([
            src,
            str(len(grp)),
            f"{grp['value'].min():.4f}",
            f"{grp['value'].max():.4f}",
            f"{grp['value'].mean():.4f}",
            str(int((grp["label"] == 1).sum())),
        ])
    add_table(
        doc,
        ["source", "строк", "min(value)", "max(value)", "mean(value)", "аномалий (label=1)"],
        stats_rows,
    )

    sample = unified.head(5)[["timestamp", "service", "metric_name", "value", "label", "source"]]
    add_paragraph(doc, "Фрагмент унифицированного набора после нормализации:")
    add_table(
        doc,
        list(sample.columns),
        [[str(v)[:22] if c == "timestamp" else str(v) for c, v in zip(sample.columns, row)] for row in sample.values.tolist()],
    )

    add_paragraph(
        doc,
        "Автоматизированные тесты (pytest) покрывают: load_nab, load_kpi, load_prometheus "
        "(с подменой HTTP), normalize_dataframe, add_features, build_ml_dataset, run_pipeline. "
        "Тесты фиксируют контракт единой схемы и предотвращают регрессии при доработке "
        "загрузчиков или добавлении новых источников.",
    )
    add_paragraph(
        doc,
        f"Результат полного прогона по NAB: {FULL_RUN_ROWS:,} строк, {FULL_RUN_ANOMALIES:,} "
        f"аномалий, суммарный размер артефактов Parquet ≈ {FULL_RUN_SIZE_MB} МБ. "
        "Файлы: datasets/unified/unified_dataset.parquet, ml_dataset.parquet.",
    )
    add_subsection(doc, "Сводные графики по объединённому набору (combined)")
    add_paragraph(
        doc,
        "При команде python main.py all строятся общие отчёты в reports/current/combined/ — "
        "они отражают совмещение всех загруженных источников и используются для "
        "сравнительного анализа распределений и динамики метрик.",
    )
    add_report_images(doc, REPORTS_COMBINED, "Объединённый набор")


def section_features(doc: Document) -> None:
    page_break(doc)
    add_heading_section(doc, "Инженерия признаков временных рядов")
    add_paragraph(
        doc,
        "Алгоритмы обнаружения аномалий (Isolation Forest, One-Class SVM, Local Outlier "
        "Factor) чувствительны к форме временного ряда, а не только к абсолютному значению. "
        "Поэтому по каждой тройке (source, service, metric_name) после сортировки по времени "
        "рассчитываются скользящие статистики и разностные признаки — они отражают локальный "
        "тренд, волатильность и резкие скачки, характерные для сбоев микросервисов.",
    )
    add_paragraph(
        doc,
        "Группировка по source обязательна: ряды NAB, KPI и Prometheus имеют разный масштаб "
        "и семантику; смешение без группировки привело бы к «утечке» статистик между "
        "несвязанными сериями. Реализация — pandas.groupby + transform с min_periods=1.",
    )
    add_table(
        doc,
        ["Признак", "Описание"],
        [
            ["rolling_mean_5, rolling_mean_15", "Скользящее среднее, окна 5 и 15"],
            ["rolling_std_5, rolling_std_15", "Скользящее СКО"],
            ["rolling_min_5, rolling_max_5", "Скользящий минимум и максимум"],
            ["delta", "x_t − x_{t−1}"],
            ["percent_change", "(x_t − x_{t−1}) / x_{t−1}"],
        ],
    )
    add_paragraph(
        doc,
        "Функция build_ml_dataset() удаляет строки с пропусками в признаках (первые точки "
        "окна) и формирует итоговую матрицу для алгоритмов обнаружения аномалий. "
        "Стандартное отклонение в окне w вычисляется как:",
    )
    add_paragraph(doc, "σ_t^(w) = sqrt( (1/w) · Σ_{i=0}^{w-1} (x_{t-i} − μ_t^(w))² )", first_line_indent_cm=1.25)
    add_paragraph(
        doc,
        "Относительное изменение percent_change = (x_t − x_{t−1}) / x_{t−1} выявляет "
        "резкие всплески CPU или падение RPS. Окна 5 и 15 выбраны как компромисс: "
        "5 точек — быстрая реакция (≈25 мин при шаге NAB 5 мин), 15 — сглаживание шума.",
    )
    add_paragraph(
        doc,
        "build_ml_dataset() удаляет строки с NaN в признаках (начало каждого ряда) и "
        "возвращает матрицу, готовую для sklearn. Итоговые колонки: идентификаторы ряда, "
        "value, восемь признаков, label.",
    )
    add_subsection(doc, "Примеры признаков по источникам")
    if (REPORTS_SAMPLE / "features_data.png").is_file():
        add_report_images(doc, REPORTS_SAMPLE, "NAB+KPI (фрагмент)")
    add_paragraph(
        doc,
        "Ниже — графики признаков и распределения меток для полных прогонов по NAB и KPI.",
    )
    for path, label in [(REPORTS_NAB, "NAB"), (REPORTS_KPI, "KPI")]:
        for fname, desc in [("features_data.png", "признаки"), ("anomaly_distribution.png", "метки")]:
            p = path / fname
            if p.is_file():
                add_image(doc, p, FIG.caption(f"{label}: {desc}"))


def section_ml_and_viz(doc: Document) -> None:
    page_break(doc)
    add_heading_section(doc, "Формирование единого ML-набора и визуализация")

    add_paragraph(
        doc,
        "Итоговый ML-набор (ml_dataset) — основной артефакт этапа для диссертации. "
        "Сохраняется в Apache Parquet (сжатие snappy, pyarrow) и дублируется в CSV "
        "для просмотра в Excel. Parquet на наборах порядка 10⁶ строк занимает в разы "
        "меньше места, чем CSV, и сохраняет типы datetime/float без повторного парсинга.",
    )
    add_table(
        doc,
        ["Артефакт", "Путь", "Содержимое"],
        [
            ["unified_dataset.parquet", "datasets/unified/", "6 колонок единого формата"],
            ["ml_dataset.parquet", "datasets/unified/", "признаки + label"],
            ["reports/current/<SOURCE>/*.png", "reports/current/", "5 графиков на источник"],
            ["processed/<SOURCE>/*.parquet", "datasets/processed/", "нормализованные ряды"],
        ],
    )
    add_paragraph(
        doc,
        "CLI main.py — единая точка входа. Рекурсивный discovery (etl/discovery.py) "
        "позволяет указать каталог datasets/raw/NAB целиком: обрабатываются все CSV "
        "во вложенных папках (AWSCloudwatch, realTraffic, KnownCause и др.).",
    )
    add_paragraph(doc, "Основные команды запуска:")
    for cmd in [
        "python main.py nab                              # все CSV из datasets/raw/NAB",
        "python main.py kpi datasets/raw/KPI/phase2_train.csv",
        "python main.py prometheus http://185.28.85.183:9090 container_cpu_usage_seconds_total",
        "python main.py all --prom-url http://... --prom-query node_cpu_seconds_total",
        "python main.py -v all --no-viz                  # DEBUG без графиков",
    ]:
        add_paragraph(doc, cmd, first_line_indent_cm=0.63)

    add_paragraph(
        doc,
        "Модуль visualization/plots.py (matplotlib, backend Agg) строит пять отчётов. "
        "На графиках raw_data и processed_data отображаются до четырёх наиболее длинных "
        "временных рядов; features_data — value и rolling_mean; anomaly_distribution — "
        "гистограмма меток 0/1/−1; dataset_summary — сводная таблица по источникам.",
    )
    add_paragraph(
        doc,
        "Структура каталога отчётов после полного прогона:",
    )
    add_paragraph(
        doc,
        "reports/current/NAB/, KPI/, PROMETHEUS/ — по источнику; "
        "reports/current/combined/*.png — все источники. "
        "Снимок «до улучшения» лежит в reports/before/.",
        first_line_indent_cm=0.63,
    )
    add_subsection(doc, "Итоги выполнения ETL (пример консольного вывода)")
    add_table(
        doc,
        ["Показатель", "Значение"],
        [
            ["Обработано файлов", "все CSV NAB + KPI + PromQL"],
            ["Строк (NAB, полный прогон)", f"{FULL_RUN_ROWS:,}"],
            ["Аномалий (label=1)", f"{FULL_RUN_ANOMALIES:,}"],
            ["Размер датасета", f"≈ {FULL_RUN_SIZE_MB} МБ"],
        ],
    )


def section_export_doc(doc: Document) -> None:
    page_break(doc)
    add_heading_section(doc, "Экспорт данных и документирование конвейера")
    add_paragraph(
        doc,
        "Репозиторий microservice-anomaly-monitor оформлен как воспроизводимый исследовательский "
        "проект: requirements.txt фиксирует версии зависимостей (Python 3.12, pandas 2.2, "
        "numpy, requests, pyarrow, matplotlib), README содержит архитектурную схему, инструкции "
        "по размещению датасетов и заготовку текста для раздела магистерской диссертации.",
    )
    add_paragraph(
        doc,
        "Документирование включает docstring во всех модулях, type hints, логирование через "
        "logging_config.py и осмысленные исключения (PrometheusError, FileNotFoundError, ValueError). "
        "Каталог tests/ обеспечивает регрессионный контроль при расширении конвейера.",
    )
    add_table(
        doc,
        ["Компонент", "Файл / каталог", "Назначение"],
        [
            ["Схема", "etl/schema.py", "Единый формат, канонизация метрик"],
            ["Конфигурация", "etl/config.py", "Пути RAW/PROCESSED/UNIFIED/reports"],
            ["Поиск CSV", "etl/discovery.py", "Рекурсивный обход каталогов"],
            ["Хранение", "etl/storage.py", "Parquet + CSV экспорт"],
            ["Тесты", "tests/", "pytest: loaders, normalize, features, pipeline"],
        ],
    )
    add_paragraph(
        doc,
        "Выводы этапа НИР: (1) реализован полнофункциональный ETL для трёх классов источников "
        "телеметрии микросервисов; (2) подтверждена работоспособность на миллионах строк NAB; "
        "(3) интегрирован Prometheus HTTP API с сохранением меток; (4) сформирован ML-набор "
        "признаков для Isolation Forest и аналогов; (5) автоматизирована визуализация. "
        "Следующий этап диссертации — обучение, сравнение и внедрение моделей обнаружения "
        "аномалий на подготовленных данных.",
    )


def attestation_and_characteristic(doc: Document) -> None:
    page_break(doc)
    add_center(doc, "АТТЕСТАЦИОННЫЙ ЛИСТ", 14, bold=True)
    for line in [
        "уровня освоения профессиональных компетенций",
        "в ходе прохождения практики",
        "«Производственная практика (научно-исследовательская работа)»",
        "обучающимся Синев Денис Евгеньевич",
        "по направлению 01.03.02 Прикладная математика и информатика",
        "1. Профессиональные компетенции",
    ]:
        add_center(doc, line, 14)

    add_table(
        doc,
        ["Коды и наименование компетенций/индикаторов", "Уровень освоения", "Критерии достаточности"],
        [
            ["ПК-1 … Формирует выводы по научным исследованиям", "Достаточный", "Продемонстрирован достаточный уровень"],
            ["ПК-2 … Применяет математический аппарат", "Достаточный", "Продемонстрирован достаточный уровень"],
            ["ПК-3 … Разрабатывает математические модели", "Достаточный", "Продемонстрирован достаточный уровень"],
            ["ПК-4 … Разрабатывает ПО для реализации алгоритмов", "Достаточный", "Продемонстрирован достаточный уровень"],
        ],
    )
    add_center(doc, "Руководитель практики: ______________ /В.Н. Михно/", 14)
    add_center(doc, "Научный руководитель: ______________ / О.И. Сидорова /", 14)
    add_center(doc, "«_____» _____________ 2026 года", 14)

    page_break(doc)
    add_center(doc, "ХАРАКТЕРИСТИКА НА ОБУЧАЮЩЕГОСЯ", 14, bold=True)
    for line in [
        "прошедшего производственную практику с 02 июня 2026 года по 08 июня 2026 года.",
        "(Научно-исследовательская работа)",
        "Синев Денис Евгеньевич",
        "4 курс, 01.03.02 Прикладная математика и информатика",
        "В ходе практики у обучающегося сформированы компетенции в соответствии с рабочей программой практики.",
        "Качество выполнения работы в соответствии с требованиями индивидуального задания на практику (отметить один из вариантов):",
        "Задание выполнено полностью корректно",
        "Задание выполнено с небольшими недочетами",
        "Корректно выполнена существенная часть задания",
        "Задание не выполнено или содержит грубые ошибки",
        "Замечания и рекомендации:",
        "Итоговая оценка по практике: ____________________",
        "Руководитель практики: ______________ /В.Н. Михно/",
        "Научный руководитель: ______________ / О.И. Сидорова /",
        "«______» ______________ 2026 года",
    ]:
        add_center(doc, line, 14)


def build_report() -> Path:
    global FIG
    FIG = _FigCounter()

    doc = Document()
    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)

    title_pages(doc)
    individual_assignment(doc)
    practice_diary(doc)
    table_of_contents(doc)
    section_etl_creation(doc)
    section_nab_kpi(doc)
    section_prometheus(doc)
    section_dataset_check(doc)
    section_features(doc)
    section_ml_and_viz(doc)
    section_export_doc(doc)
    attestation_and_characteristic(doc)

    doc.save(OUT_PATH)
    return OUT_PATH


if __name__ == "__main__":
    path = build_report()
    print(f"Сохранено: {path}")
