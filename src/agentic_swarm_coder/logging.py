"""Logging helpers for the Agentic Swarm Coder package."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

LOGGER_NAME = "agentic_swarm_coder"

_LEVEL_ALIASES = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


def _resolve_level(level: Optional[str | int]) -> int:
    if level is None:
        return logging.INFO

    if isinstance(level, int):
        return level

    normalized = level.strip().upper()
    return _LEVEL_ALIASES.get(normalized, logging.INFO)


def configure_logging(level: Optional[str | int] = None) -> logging.Logger:
    """Configure and return the package logger."""

    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s | %(message)s",
            )
        )
        logger.addHandler(handler)

    logger.setLevel(_resolve_level(level))
    logger.propagate = False
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger under the package root."""

    if name:
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    return logging.getLogger(LOGGER_NAME)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    /,
    **fields: Any,
) -> None:
    """Emit a structured log entry encoded as JSON."""

    payload = {"event": event, **fields}
    try:
        message = json.dumps(payload, default=str, sort_keys=True)
    except TypeError:
        message = json.dumps({"event": event}, sort_keys=True)
    logger.log(level, message)
