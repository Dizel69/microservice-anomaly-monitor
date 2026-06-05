"""Централизованная настройка логирования для ETL-конвейера."""

from __future__ import annotations

import logging
from typing import Optional

_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """Настроить корневой логгер один раз за время жизни процесса.

    Args:
        level: Уровень логирования (например, ``logging.INFO``).
    """

    global _configured
    if _configured:
        logging.getLogger().setLevel(level)
        return

    logging.basicConfig(
        level=level,
        format=_DEFAULT_FORMAT,
        datefmt=_DEFAULT_DATEFMT,
    )
    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Вернуть настроенный логгер.

    Args:
        name: Имя логгера. Если ``None`` — возвращается логгер пакета ``etl``.

    Returns:
        Экземпляр :class:`logging.Logger`.
    """

    configure_logging()
    return logging.getLogger(name if name else "etl")
