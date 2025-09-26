"""Convenience wrappers for invoking agents with logging instrumentation."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from agents import Agent
from agents.exceptions import MaxTurnsExceeded

from .instrumentation import log_agent_execution
from .backoff import run_with_backoff


def _build_agent_runner(
    *,
    logger: logging.Logger,
    agent_name: str,
    start_event: str,
    result_event: str | None,
    include_output: bool,
    error_event: str,
    max_turns: int,
) -> Callable[..., Awaitable[object]]:
    """Return a runner that applies logging around agent execution."""

    @log_agent_execution(
        logger=logger,
        agent_name=agent_name,
        start_event=start_event,
        result_event=result_event,
        include_output=include_output,
        error_event=error_event,
        handled_exceptions=(MaxTurnsExceeded,),
    )
    async def run_agent(
        *,
        iteration_index: int,
        agent: Agent,
        instruction: str,
    ) -> object:
        return await run_with_backoff(agent, instruction, max_turns=max_turns)

    return run_agent


def make_planner_runner(logger: logging.Logger, max_turns: int):
    return _build_agent_runner(
        logger=logger,
        agent_name="planner",
        start_event="iteration.plan.request",
        result_event="iteration.plan.result",
        include_output=True,
        error_event="iteration.plan.max_turns",
        max_turns=max_turns,
    )


def make_coder_runner(logger: logging.Logger, max_turns: int):
    return _build_agent_runner(
        logger=logger,
        agent_name="coder",
        start_event="iteration.coder.start",
        result_event="iteration.coder.summary",
        include_output=True,
        error_event="iteration.coder.max_turns",
        max_turns=max_turns,
    )


def make_qa_runner(logger: logging.Logger, max_turns: int):
    return _build_agent_runner(
        logger=logger,
        agent_name="qa",
        start_event="iteration.qa.start",
        result_event=None,
        include_output=False,
        error_event="iteration.qa.max_turns",
        max_turns=max_turns,
    )
