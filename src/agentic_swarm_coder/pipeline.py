"""Async workflow loop orchestrating planner, coder, and QA agents."""

from __future__ import annotations

from agents import Agent
from agents.exceptions import MaxTurnsExceeded
from agents.mcp import MCPServerStdio

from .config import RuntimeSettings
from .logging import get_logger
from .scaffold import ensure_workspace_initialized
from .workflow.agents import (
    build_coder_instruction,
    build_coder_prompt,
    build_planner_instruction,
    build_qa_instruction,
    build_qa_prompt,
    create_coder,
    create_planner,
    create_qa_reviewer,
)
from .workflow.backoff import run_with_backoff
from .workflow.qa import planner_feedback, qa_passed, summarise_output
from .workflow.testing import execute_tests, format_test_summary
from .workflow.types import (
    IterationResult,
    TestRunResult,
    WorkflowResult,
    build_iteration_result,
)

LOGGER = get_logger("pipeline")
MAX_AGENT_TURNS = 20
MAX_ITERATIONS = 3


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

        LOGGER.info("Starting workflow in workspace %s", settings.workspace)

        iterations: list[IterationResult] = []
        feedback: str | None = None
        success = False

        for iteration_index in range(1, MAX_ITERATIONS + 1):
            LOGGER.info("Iteration %d: requesting plan", iteration_index)
            planner_run = await _invoke_with_backoff(
                planner,
                build_planner_instruction(settings.goal, feedback=feedback),
            )
            LOGGER.debug(
                "Iteration %d: planner output:\n%s",
                iteration_index,
                planner_run.final_output,
            )

            LOGGER.info("Iteration %d: running coder", iteration_index)
            try:
                coder_run = await _invoke_with_backoff(
                    coder,
                    build_coder_instruction(planner_run.final_output),
                )
            except MaxTurnsExceeded as exc:
                LOGGER.error(
                    "Iteration %d: coder exceeded max turns (%s)", iteration_index, exc
                )
                iterations.append(
                    build_iteration_result(
                        plan_summary=planner_run.final_output,
                        coder_summary="Coder exceeded max turns",
                        qa_summary="",
                        qa_review=None,
                        test_result=TestRunResult(
                            command=None,
                            exit_code=None,
                            output=None,
                        ),
                    )
                )
                break
            LOGGER.debug(
                "Iteration %d: coder summary:\n%s",
                iteration_index,
                coder_run.final_output,
            )

            test_result = await execute_tests(iteration_index, settings.workspace)

            LOGGER.info("Iteration %d: running QA reviewer", iteration_index)
            try:
                reviewer_run = await _invoke_with_backoff(
                    reviewer,
                    build_qa_instruction(
                        plan_summary=planner_run.final_output,
                        coder_summary=coder_run.final_output,
                        test_summary=format_test_summary(test_result),
                    ),
                )
            except MaxTurnsExceeded as exc:
                LOGGER.error(
                    "Iteration %d: QA exceeded max turns (%s)", iteration_index, exc
                )
                iterations.append(
                    build_iteration_result(
                        plan_summary=planner_run.final_output,
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
                    plan_summary=planner_run.final_output,
                    coder_summary=coder_run.final_output,
                    qa_summary=qa_summary_text,
                    qa_review=qa_review,
                    test_result=test_result,
                )
            )

            status = qa_passed(qa_review, reviewer_run.final_output)
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
            feedback = planner_feedback(qa_review, reviewer_run.final_output)

        if not success:
            LOGGER.info("Workflow completed without QA pass after %d iterations", len(iterations))
        else:
            LOGGER.info("Workflow succeeded in %d iterations", len(iterations))

    return WorkflowResult(iterations=iterations, success=success)


async def _invoke_with_backoff(agent: Agent, instruction: str):
    return await run_with_backoff(agent, instruction, max_turns=MAX_AGENT_TURNS)
