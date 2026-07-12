"""Logging setup shared across the whole MIRSCOPE package."""
from __future__ import annotations

import logging

LOGGER_NAME = "mirscope"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root MIRSCOPE logger.

    Idempotent: calling it more than once will not attach duplicate handlers.
    Every module obtains a child logger via ``logging.getLogger("mirscope.<name>")``
    so all records share this configuration.
    """
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def get_logger(suffix: str) -> logging.Logger:
    """Return a namespaced child logger, e.g. ``get_logger("loader")``."""
    return logging.getLogger(f"{LOGGER_NAME}.{suffix}")
