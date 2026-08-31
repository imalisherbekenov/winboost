"""File logging configuration for WinBoost frontends."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOGGER_NAME = "winboost"
LOG_FILENAME = "winboost.log"


def setup_logging() -> logging.Logger:
    """Configure and return the shared WinBoost logger.

    Calling this function more than once is safe and does not add duplicate
    handlers. The GUI can invoke it once during startup.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)

    for handler in logger.handlers:
        if getattr(handler, "_winboost_file_handler", False):
            return logger

    appdata = os.environ.get("APPDATA")
    base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    log_dir = base_dir / "WinBoost"
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_dir / LOG_FILENAME,
        maxBytes=1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    handler._winboost_file_handler = True
    logger.addHandler(handler)
    return logger
