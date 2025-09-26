"""Async workflow loop orchestrating planner, coder, and QA agents."""

from __future__ import annotations

import logging

from agents import Agent
from agents.exceptions import MaxTurnsExceeded
from agents.mcp import MCPServerStdio

from .config import RuntimeSettings
from .logging import get_logger, log_event
from .scaffold import ensure_workspace_initialized
from .agent_factory import create_coder, create_planner, create_qa_reviewer
from .backoff import run_with_backoff
from .prompts.coder import build_coder_instruction, build_coder_prompt
from .prompts.planner import build_planner_instruction
from .prompts.qa import build_qa_instruction, build_qa_prompt
from .qa_utils import planner_feedback, qa_passed, summarise_output
from .results import (
    IterationResult,
    WorkflowResult,
    build_iteration_result,
    empty_test_result,
)
from .test_runner import execute_tests, format_test_summary
from .schemas import PlannerPlan

LOGGER = get_logger("pipeline")
MAX_AGENT_TURNS = 20
MAX_ITERATIONS = 2


async def execute_workflow(settings: RuntimeSettings) -> WorkflowResult:
    """Run the multi-agent workflow until QA approves or the iteration cap is hit."""

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
        planner = create_planner()
        coder = create_coder(coder_prompt, filesystem_server)
        reviewer = create_qa_reviewer(qa_prompt, filesystem_server)

        log_event(
            LOGGER,
            logging.INFO,
            "workflow.start",
            workspace=str(settings.workspace),
            goal=settings.goal,
        )

        iterations: list[IterationResult] = []
        feedback: str | None = None
        success = False

        for iteration_index in range(1, MAX_ITERATIONS + 1):
            log_event(
                LOGGER,
                logging.INFO,
                "iteration.plan.request",
                iteration=iteration_index,
            )
            try:
                planner_run = await _invoke_with_backoff(
                    planner,
                    build_planner_instruction(settings.goal, feedback=feedback),
                )
            except MaxTurnsExceeded as exc:
                log_event(
                    LOGGER,
                    logging.ERROR,
                    "iteration.plan.max_turns",
                    iteration=iteration_index,
                    error=str(exc),
                )
                iterations.append(
                    build_iteration_result(
                        plan_summary="Planner exceeded max turns",
                        plan_complete=False,
                        coder_summary="",
                        qa_summary="",
                        qa_review=None,
                        test_result=empty_test_result(),
                    )
                )
                break

            log_event(
                LOGGER,
                logging.DEBUG,
                "iteration.plan.result",
                iteration=iteration_index,
                content=planner_run.final_output,
            )

            plan_summary, plan_complete = _summarise_plan(planner_run.final_output)

            log_event(
                LOGGER,
                logging.INFO,
                "iteration.coder.start",
                iteration=iteration_index,
            )
            try:
                coder_run = await _invoke_with_backoff(
                    coder,
                    build_coder_instruction(plan_summary),
                )
            except MaxTurnsExceeded as exc:
                log_event(
                    LOGGER,
                    logging.ERROR,
                    "iteration.coder.max_turns",
                    iteration=iteration_index,
                    error=str(exc),
                )
                iterations.append(
                    build_iteration_result(
                        plan_summary=plan_summary,
                        plan_complete=plan_complete,
                        coder_summary="Coder exceeded max turns",
                        qa_summary="",
                        qa_review=None,
                        test_result=empty_test_result(),
                    )
                )
                break
            log_event(
                LOGGER,
                logging.DEBUG,
                "iteration.coder.summary",
                iteration=iteration_index,
                content=coder_run.final_output,
            )

            test_result = await execute_tests(iteration_index, settings.workspace)

            log_event(
                LOGGER,
                logging.INFO,
                "iteration.qa.start",
                iteration=iteration_index,
            )
            try:
                reviewer_run = await _invoke_with_backoff(
                    reviewer,
                    build_qa_instruction(
                        plan_summary=plan_summary,
                        coder_summary=coder_run.final_output,
                        test_summary=format_test_summary(test_result),
                    ),
                )
            except MaxTurnsExceeded as exc:
                log_event(
                    LOGGER,
                    logging.ERROR,
                    "iteration.qa.max_turns",
                    iteration=iteration_index,
                    error=str(exc),
                )
                iterations.append(
                    build_iteration_result(
                        plan_summary=plan_summary,
                        plan_complete=plan_complete,
                        coder_summary=coder_run.final_output,
                        qa_summary="QA exceeded max turns",
                        qa_review=None,
                        test_result=test_result,
                    )
                )
                break

            qa_review, qa_summary_text = summarise_output(
                reviewer_run.final_output,
                iteration_index,
            )
            iterations.append(
                build_iteration_result(
                    plan_summary=plan_summary,
                    plan_complete=plan_complete,
                    coder_summary=coder_run.final_output,
                    qa_summary=qa_summary_text,
                    qa_review=qa_review,
                    test_result=test_result,
                )
            )

            status = qa_passed(qa_review, reviewer_run.final_output)
            log_event(
                LOGGER,
                logging.INFO,
                "iteration.qa.result",
                iteration=iteration_index,
                status=status,
            )
            if status is True:
                log_event(
                    LOGGER,
                    logging.INFO,
                    "workflow.success",
                    iteration=iteration_index,
                    total_iterations=len(iterations) + 1,
                )
                success = True
                break

            if status is False:
                log_event(
                    LOGGER,
                    logging.INFO,
                    "iteration.qa.feedback",
                    iteration=iteration_index,
                    issues=qa_review.issues if qa_review else None,
                )
            else:
                log_event(
                    LOGGER,
                    logging.WARNING,
                    "iteration.qa.missing_status",
                    iteration=iteration_index,
                )
            feedback = planner_feedback(qa_review, reviewer_run.final_output)

        if not success:
            log_event(
                LOGGER,
                logging.INFO,
                "workflow.incomplete",
                iterations=len(iterations),
            )
        else:
            log_event(
                LOGGER,
                logging.INFO,
                "workflow.complete",
                iterations=len(iterations),
            )

    return WorkflowResult(iterations=iterations, success=success)


async def _invoke_with_backoff(agent: Agent, instruction: str):
    return await run_with_backoff(agent, instruction, max_turns=MAX_AGENT_TURNS)


def _summarise_plan(output: object) -> tuple[str, bool]:
    """Convert planner output into a textual summary and completion flag."""

    if isinstance(output, PlannerPlan):
        summary_text = output.summary()
        return (summary_text or "Planner returned an empty plan.", output.complete)

    text = str(output).strip() if output is not None else ""
    if not text:
        return ("Planner returned no output.", False)
    return text, False
