"""Helpers for executing the project's automated tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import logging

from ..logging import get_logger, log_event
from .types import TestRunResult

LOGGER = get_logger("workflow.testing")


async def run_pytest(workspace: Path) -> TestRunResult:
    """Execute pytest in the workspace and capture the combined output."""

    command = ["pytest", "-q"]
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except FileNotFoundError as exc:
        message = f"pytest command not found: {exc}"
        LOGGER.error(message)
        return TestRunResult(command=" ".join(command), exit_code=None, output=message)

    stdout, _ = await process.communicate()
    output = stdout.decode("utf-8", errors="replace")
    return TestRunResult(
        command=" ".join(command),
        exit_code=process.returncode,
        output=output,
    )


async def execute_tests(iteration_index: int, workspace: Path) -> TestRunResult:
    log_event(
        LOGGER,
        logging.INFO,
        "iteration.tests.start",
        iteration=iteration_index,
    )
    result = await run_pytest(workspace)
    if result.exit_code is None:
        log_event(
            LOGGER,
            logging.WARNING,
            "iteration.tests.skipped",
            iteration=iteration_index,
            output=result.output,
        )
    elif result.exit_code != 0:
        log_event(
            LOGGER,
            logging.INFO,
            "iteration.tests.failed",
            iteration=iteration_index,
            exit_code=result.exit_code,
        )
    else:
        log_event(
            LOGGER,
            logging.INFO,
            "iteration.tests.passed",
            iteration=iteration_index,
        )
    log_event(
        LOGGER,
        logging.DEBUG,
        "iteration.tests.output",
        iteration=iteration_index,
        command=result.command,
        output=result.output,
    )
    return result


def format_test_summary(result: TestRunResult) -> str:
    """Produce a text summary of the test execution for the QA agent."""

    command = result.command or "pytest"
    output = (result.output or "<no output>").strip()

    if result.exit_code is None:
        return (
            f"Command: {command}\n"
            "Status: not run (missing command or error before execution)\n"
            f"Output:\n{output}"
        )

    status = "PASS" if result.exit_code == 0 else "FAIL"
    return (
        f"Command: {command}\n"
        f"Exit code: {result.exit_code} ({status})\n"
        f"Output:\n{output}"
    )
