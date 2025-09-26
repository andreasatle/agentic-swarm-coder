"""Utilities for invoking agents with retry/backoff policies."""

from __future__ import annotations

import asyncio
import random
from typing import Any

from agents import Agent, Runner
from openai import RateLimitError

from .logging import get_logger

LOGGER = get_logger("backoff")

RATE_LIMIT_MAX_RETRIES = 5
RATE_LIMIT_INITIAL_DELAY = 1.5
RATE_LIMIT_BACKOFF_MULTIPLIER = 2.0
RATE_LIMIT_JITTER = 0.5


async def run_with_backoff(
    agent: Agent,
    instruction: str,
    *,
    max_turns: int,
    max_retries: int = RATE_LIMIT_MAX_RETRIES,
) -> Any:
    """Run an agent with exponential backoff on rate limit errors."""

    delay = RATE_LIMIT_INITIAL_DELAY
    attempt = 0
    while True:
        attempt += 1
        try:
            return await Runner.run(agent, instruction, max_turns=max_turns)
        except RateLimitError as exc:
            if attempt >= max_retries:
                LOGGER.error(
                    "Rate limit persisted after %d attempts: %s",
                    attempt,
                    exc,
                )
                raise

            snooze = delay + random.random() * RATE_LIMIT_JITTER
            LOGGER.warning(
                "Rate limit hit (attempt %d/%d). Sleeping %.2fs before retrying.",
                attempt,
                max_retries,
                snooze,
            )
            await asyncio.sleep(snooze)
            delay *= RATE_LIMIT_BACKOFF_MULTIPLIER
