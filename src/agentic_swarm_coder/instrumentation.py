"""Shared logging utilities and decorators for agent execution."""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Mapping, Sequence
from functools import wraps
from typing import Any

try:  # Optional dependency: only used when available
    from pydantic import BaseModel  # type: ignore
except ImportError:  # pragma: no cover - defensive fallback
    BaseModel = None  # type: ignore[misc,assignment]

from .logging import log_event

SERIALIZATION_MAX_DEPTH = 4


def serialise_for_logging(value: Any, *, depth: int = 0) -> Any:
    """Best-effort conversion of complex objects for JSON logging."""

    if depth >= SERIALIZATION_MAX_DEPTH:
        return repr(value)

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Mapping):
        return {
            str(key): serialise_for_logging(item, depth=depth + 1)
            for key, item in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [serialise_for_logging(item, depth=depth + 1) for item in value]

    if dataclasses.is_dataclass(value):
        return serialise_for_logging(dataclasses.asdict(value), depth=depth + 1)

    if BaseModel is not None and isinstance(value, BaseModel):  # type: ignore[arg-type]
        try:
            model_dict = value.model_dump()
        except Exception:  # pragma: no cover - defensive
            model_dict = value.dict() if hasattr(value, "dict") else repr(value)
        return serialise_for_logging(model_dict, depth=depth + 1)

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump()
        except Exception:  # pragma: no cover - defensive
            dumped = None
        if dumped is not None:
            return serialise_for_logging(dumped, depth=depth + 1)

    if hasattr(value, "__dict__"):
        public = {k: v for k, v in vars(value).items() if not k.startswith("_")}
        if public:
            return serialise_for_logging(public, depth=depth + 1)

    return repr(value)


def log_agent_run_details(
    logger: logging.Logger,
    iteration_index: int,
    agent_name: str,
    run_result: Any,
) -> None:
    """Emit a structured transcript log for an agent run when available."""

    if run_result is None:
        log_event(
            logger,
            logging.DEBUG,
            "iteration.agent.transcript",
            iteration=iteration_index,
            agent=agent_name,
            note="Run result missing; nothing to log",
        )
        return

    payload: dict[str, Any] = {"agent": agent_name}

    final_output = getattr(run_result, "final_output", None)
    if final_output is not None:
        payload["final_output"] = serialise_for_logging(final_output)

    for attr in ("messages", "turns", "history", "steps", "response"):
        value = getattr(run_result, attr, None)
        if value:
            payload[attr] = serialise_for_logging(value)

    tool_calls = getattr(run_result, "tool_calls", None)
    if tool_calls:
        payload["tool_calls"] = serialise_for_logging(tool_calls)

    metadata = getattr(run_result, "metadata", None)
    if metadata:
        payload["metadata"] = serialise_for_logging(metadata)

    if len(payload) <= 1:
        payload["repr"] = repr(run_result)

    log_event(
        logger,
        logging.DEBUG,
        "iteration.agent.transcript",
        iteration=iteration_index,
        **payload,
    )


def log_agent_execution(
    *,
    logger: logging.Logger,
    agent_name: str,
    start_event: str,
    start_level: int = logging.INFO,
    result_event: str | None = None,
    result_level: int = logging.DEBUG,
    result_field: str = "content",
    include_output: bool = True,
    error_event: str | None = None,
    error_level: int = logging.ERROR,
    handled_exceptions: tuple[type[BaseException], ...] = (),
):
    """Decorator that standardises logging around agent execution."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, iteration_index: int, **kwargs):
            log_event(
                logger,
                start_level,
                start_event,
                iteration=iteration_index,
            )
            try:
                run_result = await func(*args, iteration_index=iteration_index, **kwargs)
            except handled_exceptions as exc:
                if error_event:
                    log_event(
                        logger,
                        error_level,
                        error_event,
                        iteration=iteration_index,
                        error=str(exc),
                    )
                raise

            if result_event is not None:
                payload: dict[str, Any] = {"iteration": iteration_index}
                if include_output:
                    final_output = getattr(run_result, "final_output", None)
                    if final_output is not None:
                        payload[result_field] = final_output
                log_event(
                    logger,
                    result_level,
                    result_event,
                    **payload,
                )

            log_agent_run_details(logger, iteration_index, agent_name, run_result)
            return run_result

        return wrapper

    return decorator


def log_iteration_status(
    *,
    logger: logging.Logger,
    iteration_index: int,
    status: bool | None,
    qa_review: object,
) -> None:
    """Log QA status along with feedback or missing-status warnings."""

    log_event(
        logger,
        logging.INFO,
        "iteration.qa.result",
        iteration=iteration_index,
        status=status,
    )

    if status is False:
        issues = getattr(qa_review, "issues", None) if qa_review is not None else None
        log_event(
            logger,
            logging.INFO,
            "iteration.qa.feedback",
            iteration=iteration_index,
            issues=issues,
        )
    elif status is None:
        log_event(
            logger,
            logging.WARNING,
            "iteration.qa.missing_status",
            iteration=iteration_index,
        )


def log_workflow_success(
    *,
    logger: logging.Logger,
    iteration_index: int,
    total_iterations: int,
) -> None:
    """Log that the workflow completed successfully within an iteration."""

    log_event(
        logger,
        logging.INFO,
        "workflow.success",
        iteration=iteration_index,
        total_iterations=total_iterations,
    )


def log_workflow_completion(
    *,
    logger: logging.Logger,
    success: bool,
    iteration_count: int,
) -> None:
    """Log the final completion state of the workflow."""

    event = "workflow.complete" if success else "workflow.incomplete"
    log_event(
        logger,
        logging.INFO,
        event,
        iterations=iteration_count,
    )
