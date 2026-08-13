# Графики ETL

Все PNG лежат **в корне репозитория**, не внутри `datasets/`.

```
reports/
├── before/     ← снимок «как было» (для выступления). Конвейер НЕ перезаписывает.
│   ├── NAB/
│   ├── KPI/
│   ├── PROMETHEUS/
│   ├── combined/      # общие графики по всем источникам
│   └── REPORT_SAMPLE/ # мини-прогон для отчёта НИР
└── current/    ← новые прогоны (`python main.py …`). Можно сравнивать с before/.
    ├── NAB/
    ├── KPI/
    ├── PROMETHEUS/
    └── combined/
```

В каждой папке источника одни и те же 5 файлов:

| Файл | Что на графике |
|------|----------------|
| `raw_data.png` | исходные ряды |
| `processed_data.png` | после очистки |
| `features_data.png` | признаки |
| `anomaly_distribution.png` | метки аномалий |
| `dataset_summary.png` | сводка |

`datasets/` — только данные (raw / processed / unified). Картинки оттуда убраны.

Оба каталога (`before/` и `current/`) кладутся в git, чтобы графики можно было скачать с GitHub.
Конвейер пишет только в `current/` и **не имеет права** менять файлы в `before/`.
