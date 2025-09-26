"""Logging helpers for the Agentic Swarm Coder package."""

from __future__ import annotations

import json
import logging
from pathlib import Path
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


def configure_logging(
    level: Optional[str | int] = None,
    *,
    log_file: Optional[str | Path] = None,
    file_level: Optional[str | int] = None,
) -> logging.Logger:
    """Configure and return the package logger.

    Parameters
    ----------
    level:
        Log level for the console stream handler. Defaults to ``INFO`` when ``None``.
    log_file:
        Optional path to a log file that should receive the full output. Parent
        directories are created automatically.
    file_level:
        Log level for the file handler. Defaults to ``DEBUG`` when ``log_file`` is
        provided.
    """

    logger = logging.getLogger(LOGGER_NAME)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    resolved_stream_level = _resolve_level(level)
    resolved_file_level = _resolve_level(file_level) if file_level is not None else logging.DEBUG

    stream_handler = None
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            stream_handler = handler
            break

    if stream_handler is None:
        stream_handler = logging.StreamHandler()
        logger.addHandler(stream_handler)

    stream_handler.setLevel(resolved_stream_level)
    stream_handler.setFormatter(formatter)

    if log_file is not None:
        log_path = Path(log_file).expanduser().resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = None
        for handler in logger.handlers:
            if (
                isinstance(handler, logging.FileHandler)
                and Path(handler.baseFilename).resolve() == log_path
            ):
                file_handler = handler
                break

        if file_handler is None:
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            logger.addHandler(file_handler)

        file_handler.setLevel(resolved_file_level)
        file_handler.setFormatter(formatter)

        effective_level = min(resolved_stream_level, resolved_file_level)
    else:
        effective_level = resolved_stream_level

    logger.setLevel(effective_level)
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
