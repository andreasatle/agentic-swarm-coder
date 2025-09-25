"""Async pipeline that orchestrates the planner, coder, and QA agents."""

from __future__ import annotations

import asyncio
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from agents import Agent, Runner
from agents.exceptions import MaxTurnsExceeded
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings
from openai import RateLimitError

from .config import RuntimeSettings
from .logging import get_logger
from .prompts import (
    PLANNER_PROMPT,
    build_planner_instruction,
    build_coder_instruction,
    build_coder_prompt,
    build_qa_instruction,
    build_qa_prompt,
)
from .schemas import QAReview
from .scaffold import ensure_workspace_initialized


LOGGER = get_logger("pipeline")
MAX_AGENT_TURNS = 20
RATE_LIMIT_MAX_RETRIES = 5
RATE_LIMIT_INITIAL_DELAY = 1.5
RATE_LIMIT_BACKOFF_MULTIPLIER = 2.0
RATE_LIMIT_JITTER = 0.5
_QA_STATUS_PATTERN = re.compile(
    r"^\s*\**\s*OVERALL_STATUS:\s*(PASS|FAIL)\s*\**\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class IterationResult:
    """Container for the textual outputs produced in a single loop iteration."""

    plan_summary: str
    coder_summary: str
    qa_summary: str
    qa_review: Optional[QAReview]
    test_command: str | None
    test_exit_code: int | None
    test_output: str | None


@dataclass(frozen=True)
class TestRunResult:
    """Represents the outcome of running the project test suite."""

    command: str | None
    exit_code: int | None
    output: str | None


@dataclass(frozen=True)
class WorkflowResult:
    """High-level outcome of running the multi-agent workflow."""

    iterations: list[IterationResult]
    success: bool


def _qa_passed(review: QAReview | None, qa_output: str) -> bool | None:
    """Parse the QA output for an OVERALL_STATUS line."""

    if review is not None:
        return review.status == "PASS"

    for line in reversed(qa_output.strip().splitlines()):
        match = _QA_STATUS_PATTERN.match(line)
        if match:
            status = match.group(1).upper()
            if status == "PASS":
                return True
            if status == "FAIL":
                return False
    return None


def _coerce_qa_review(output: Any) -> QAReview | None:
    """Best-effort conversion of an agent output into a QAReview object."""

    if isinstance(output, QAReview):
        return output

    if isinstance(output, str):
        output = output.strip()
        if not output:
            return None
        try:
            return QAReview.model_validate_json(output)
        except ValueError:
            return None

    try:
        return QAReview.model_validate(output)  # type: ignore[arg-type]
    except ValueError:
        return None


def _format_qa_summary(review: QAReview | None, raw_output: Any) -> str:
    if review is None:
        return str(raw_output)

    issues_text = "\n- ".join(review.issues)
    issues_block = f"\nIssues:\n- {issues_text}" if review.issues else ""
    return f"Status: {review.status}\nSummary: {review.summary}{issues_block}"


def _planner_feedback_from_qa(review: QAReview | None, raw_output: Any) -> str:
    if review is None:
        return str(raw_output)

    if not review.issues:
        return f"QA Summary: {review.summary}\nStatus: {review.status}"

    bullet_list = "\n".join(f"- {issue}" for issue in review.issues)
    return (
        "QA Summary: "
        f"{review.summary}\n"
        "Status: "
        f"{review.status}\n"
        "Outstanding issues:\n"
        f"{bullet_list}"
    )


def _format_test_summary(result: TestRunResult) -> str:
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


async def _run_pytest(workspace: Path) -> TestRunResult:
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
        return TestRunResult(
            command=" ".join(command),
            exit_code=None,
            output=message,
        )

    stdout, _ = await process.communicate()
    output = stdout.decode("utf-8", errors="replace")
    return TestRunResult(
        command=" ".join(command),
        exit_code=process.returncode,
        output=output,
    )


async def _execute_tests(iteration_index: int, workspace: Path) -> TestRunResult:
    LOGGER.info("Iteration %d: running tests", iteration_index)
    result = await _run_pytest(workspace)
    if result.exit_code is None:
        LOGGER.warning(
            "Iteration %d: pytest was skipped (%s)",
            iteration_index,
            result.output,
        )
    elif result.exit_code != 0:
        LOGGER.info(
            "Iteration %d: pytest failed with exit code %d",
            iteration_index,
            result.exit_code,
        )
    else:
        LOGGER.info("Iteration %d: pytest succeeded", iteration_index)
    LOGGER.debug(
        "Iteration %d: pytest output for command '%s':\n%s",
        iteration_index,
        result.command or "<not run>",
        result.output or "<no output>",
    )
    return result


async def _invoke_qa(
    reviewer: Agent,
    iteration_index: int,
    *,
    plan_summary: str,
    coder_summary: str,
    test_result: TestRunResult,
):
    instruction = build_qa_instruction(
        plan_summary=plan_summary,
        coder_summary=coder_summary,
        test_summary=_format_test_summary(test_result),
    )
    result = await _run_agent_with_backoff(
        reviewer,
        instruction,
        max_turns=MAX_AGENT_TURNS,
    )
    LOGGER.debug(
        "Iteration %d: QA raw summary:\n%s",
        iteration_index,
        result.final_output,
    )
    return result


def _summarise_qa_output(output: Any, iteration_index: int) -> tuple[QAReview | None, str]:
    review = _coerce_qa_review(output)
    summary_text = _format_qa_summary(review, output)
    LOGGER.debug(
        "Iteration %d: QA structured summary:\n%s",
        iteration_index,
        summary_text,
    )
    return review, summary_text


def _build_iteration_result(
    *,
    plan_summary: str,
    coder_summary: str,
    qa_summary: str,
    qa_review: QAReview | None,
    test_result: TestRunResult,
) -> IterationResult:
    return IterationResult(
        plan_summary=plan_summary,
        coder_summary=coder_summary,
        qa_summary=qa_summary,
        qa_review=qa_review,
        test_command=test_result.command,
        test_exit_code=test_result.exit_code,
        test_output=test_result.output,
    )


async def execute_workflow(settings: RuntimeSettings) -> WorkflowResult:
    """Run the agents with an iterative feedback loop until QA passes or limits hit."""

    coder_prompt = build_coder_prompt(settings.workspace)
    qa_prompt = build_qa_prompt(settings.workspace)

    await ensure_workspace_initialized(settings.workspace)

    async with MCPServerStdio(
        name="filesystem",
        params={
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                str(settings.workspace),
            ],
        },
    ) as filesystem_server:
        planner = Agent(name="Planner", instructions=PLANNER_PROMPT)
        coder = Agent(
            name="Coder",
            instructions=coder_prompt,
            mcp_servers=[filesystem_server],
            model_settings=ModelSettings(tool_choice="required"),
        )
        reviewer = Agent(
            name="QA",
            instructions=qa_prompt,
            mcp_servers=[filesystem_server],
            model_settings=ModelSettings(tool_choice="required"),
            output_type=QAReview,
        )

        LOGGER.info("Starting workflow in workspace %s", settings.workspace)

        iterations: list[IterationResult] = []
        feedback: str | None = None
        success = False

        max_iterations = 3
        for iteration_index in range(1, max_iterations + 1):
            LOGGER.info("Iteration %d: requesting plan", iteration_index)
            try:
                planner_run = await _run_agent_with_backoff(
                    planner,
                    build_planner_instruction(settings.goal, feedback=feedback),
                    max_turns=MAX_AGENT_TURNS,
                )
            except MaxTurnsExceeded as exc:
                LOGGER.error(
                    "Iteration %d: planner exceeded max turns (%s)",
                    iteration_index,
                    exc,
                )
                iterations.append(
                    IterationResult(
                        plan_summary="Planner exceeded max turns",
                        coder_summary="",
                        qa_summary="",
                        qa_review=None,
                        test_command=None,
                        test_exit_code=None,
                        test_output=None,
                    )
                )
                break
            LOGGER.debug(
                "Iteration %d: planner output:\n%s",
                iteration_index,
                planner_run.final_output,
            )

            LOGGER.info("Iteration %d: running coder", iteration_index)
            try:
                coder_run = await _run_agent_with_backoff(
                    coder,
                    build_coder_instruction(planner_run.final_output),
                    max_turns=MAX_AGENT_TURNS,
                )
            except MaxTurnsExceeded as exc:
                LOGGER.error(
                    "Iteration %d: coder exceeded max turns (%s)",
                    iteration_index,
                    exc,
                )
                iterations.append(
                    IterationResult(
                        plan_summary=planner_run.final_output,
                        coder_summary="Coder exceeded max turns",
                        qa_summary="",
                        qa_review=None,
                        test_command=None,
                        test_exit_code=None,
                        test_output=None,
                    )
                )
                break
            LOGGER.debug(
                "Iteration %d: coder summary:\n%s",
                iteration_index,
                coder_run.final_output,
            )

            test_result = await _execute_tests(iteration_index, settings.workspace)

            LOGGER.info("Iteration %d: running QA reviewer", iteration_index)
            try:
                reviewer_run = await _invoke_qa(
                    reviewer,
                    iteration_index,
                    plan_summary=planner_run.final_output,
                    coder_summary=coder_run.final_output,
                    test_result=test_result,
                )
            except MaxTurnsExceeded as exc:
                LOGGER.error(
                    "Iteration %d: QA exceeded max turns (%s)",
                    iteration_index,
                    exc,
                )
                iterations.append(
                    _build_iteration_result(
                        plan_summary=planner_run.final_output,
                        coder_summary=coder_run.final_output,
                        qa_summary="QA exceeded max turns",
                        qa_review=None,
                        test_result=test_result,
                    )
                )
                break
            qa_review, qa_summary_text = _summarise_qa_output(
                reviewer_run.final_output,
                iteration_index,
            )
            iterations.append(
                _build_iteration_result(
                    plan_summary=planner_run.final_output,
                    coder_summary=coder_run.final_output,
                    qa_summary=qa_summary_text,
                    qa_review=qa_review,
                    test_result=test_result,
                )
            )

            status = _qa_passed(qa_review, reviewer_run.final_output)
            if status is True:
                LOGGER.info("Iteration %d: QA passed; stopping workflow", iteration_index)
                success = True
                break

            if status is False:
                LOGGER.info("Iteration %d: QA reported issues; feeding back to planner", iteration_index)
            else:
                LOGGER.warning(
                    "Iteration %d: QA output missing OVERALL_STATUS; assuming more work needed",
                    iteration_index,
                )
            feedback = _planner_feedback_from_qa(qa_review, reviewer_run.final_output)

        if not success:
            LOGGER.info("Workflow completed without QA pass after %d iterations", len(iterations))
        else:
            LOGGER.info("Workflow succeeded in %d iterations", len(iterations))

    return WorkflowResult(iterations=iterations, success=success)


async def _run_agent_with_backoff(
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
