# Данные и лицензии

В репозиторий кладутся **исходные датасеты** (чтобы их можно было скачать с GitHub)
и **графики** в `reports/`. Производные наборы (`datasets/processed`, `datasets/unified`)
пересобираются командой `python main.py all` и в git не входят: они слишком большие
и меняются после каждого прогона.

Лимит GitHub: **100 МБ на файл**. Поэтому KPI хранится как `.csv.gz`.

## Что скачивается вместе с репозиторием

| Путь | Что внутри | Лицензия |
|------|------------|----------|
| `datasets/raw/NAB/**/*.csv` | Ряды Numenta Anomaly Benchmark | MIT ([numenta/NAB](https://github.com/numenta/NAB)) |
| `datasets/raw/KPI/phase2_train.csv.gz` | KPI Anomaly Detection, train | MIT ([NetManAIOps/KPI-Anomaly-Detection](https://github.com/NetManAIOps/KPI-Anomaly-Detection)) |
| `datasets/raw/PROMETHEUS/*.parquet` | Выгрузка с нашего Prometheus | данные проекта |
| `reports/before/` | Графики **до** исправления датасетов (для выступления) | этот репозиторий |
| `reports/current/` | Графики **после** новых прогонов ETL | этот репозиторий |

Код проекта — MIT, см. корневой `LICENSE`.

## Как пользоваться KPI из git

pandas читает gzip напрямую. Конвейер тоже:

```bash
python main.py kpi datasets/raw/KPI/phase2_train.csv.gz
# или просто:
python main.py kpi
```

Если нужен несжатый CSV локально:

```bash
gzip -dk datasets/raw/KPI/phase2_train.csv.gz
```

Файл `phase2_train.csv` (~176 МБ) в git **не коммитить**.

## Что не кладём в git

- `datasets/unified/*.csv` / `*.parquet` (сотни мегабайт, результат ETL)
- `datasets/processed/`
- несжатый `phase2_train.csv`
- `.venv/`, `__pycache__/`, отчёты `.docx`

## Уведомление правообладателей (MIT)

NAB © Numenta Inc. Лицензия MIT: https://github.com/numenta/NAB/blob/master/LICENSE.txt

KPI Anomaly Detection © 2021 NetManAIOps_KAD. Лицензия MIT:
https://github.com/NetManAIOps/KPI-Anomaly-Detection/blob/master/LICENSE
