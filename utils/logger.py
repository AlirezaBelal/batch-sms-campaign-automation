"""Application logging configuration."""

import logging
from pathlib import Path

from config import LOG_FILE, LOG_FORMAT, LOG_LEVEL


def configure_logging() -> None:
    """Configure console and file logging for the campaign application."""
    log_path = Path(LOG_FILE)
    if log_path.parent != Path("."):
        log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
