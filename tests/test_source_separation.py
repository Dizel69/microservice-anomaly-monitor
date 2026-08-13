"""Источники не смешиваются: KPI грузится только KPI-загрузчиком, NAB — своим."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import main as cli
from etl.loaders import load_kpi, load_nab
from etl.schema import LABEL, SERVICE, SOURCE, SOURCE_KPI, SOURCE_NAB


def test_kpi_file_rejected_by_nab_loader(kpi_csv) -> None:
    """Файл KPI, поданный в загрузчик NAB, не превращается в source=NAB."""

    path = kpi_csv()

    with pytest.raises(ValueError, match="KPI"):
        load_nab(path)


def test_cli_blocks_kpi_file_in_nab_command(kpi_csv) -> None:
    """CLI-команда 'nab' на файле KPI завершается ошибкой, а не тихой записью."""

    path = kpi_csv()
    exit_code = cli.main(["--no-viz", "nab", str(path)])

    assert exit_code == 1


def test_kpi_loader_sets_kpi_source_and_service_from_kpi_id(kpi_csv) -> None:
    """KPI-загрузчик ставит source=KPI и берёт service из колонки 'KPI ID'."""

    frame = load_kpi(kpi_csv())

    assert frame[SOURCE].unique().tolist() == [SOURCE_KPI]
    assert frame[SERVICE].unique().tolist() == [
        "da10a69f-d836-3baa-ad40-3e548ecf1fbd"
    ]


def test_kpi_loader_preserves_binary_labels(kpi_csv) -> None:
    """Эталонные метки KPI (0/1) сохраняются как есть."""

    frame = load_kpi(kpi_csv(rows=6))

    assert sorted(frame[LABEL].unique().tolist()) == [0, 1]
    assert int((frame[LABEL] == 1).sum()) == 1


def test_kpi_loader_reads_gzip(kpi_csv) -> None:
    """Сжатый .csv.gz читается так же, как несжатый .csv."""

    plain = load_kpi(kpi_csv(name="phase2_train.csv"))
    packed = load_kpi(kpi_csv(name="phase2_train.csv.gz"))

    pd.testing.assert_frame_equal(plain, packed)


def test_nab_file_rejected_by_kpi_loader(nab_dataset) -> None:
    """Файл NAB (без 'KPI ID') не грузится KPI-загрузчиком без явного service."""

    path = nab_dataset()

    with pytest.raises(ValueError, match="KPI ID"):
        load_kpi(path)


def test_nab_loader_sets_nab_source(nab_dataset) -> None:
    """NAB-загрузчик ставит source=NAB."""

    frame = load_nab(nab_dataset())

    assert frame[SOURCE].unique().tolist() == [SOURCE_NAB]


def test_real_kpi_file_is_not_labelled_as_nab(real_kpi_file: Path) -> None:
    """Настоящий файл KPI из репозитория тоже отвергается загрузчиком NAB."""

    with pytest.raises(ValueError, match="KPI"):
        load_nab(real_kpi_file)
