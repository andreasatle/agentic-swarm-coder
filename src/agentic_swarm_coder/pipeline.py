"""Async workflow loop orchestrating planner, coder, and QA agents."""

from __future__ import annotations

import logging

from agents import Agent
from agents.exceptions import MaxTurnsExceeded
from agents.mcp import MCPServerStdio

from .config import RuntimeSettings
from .instrumentation import (
    log_agent_execution,
    log_iteration_status,
    log_workflow_completion,
    log_workflow_success,
)
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
from .planner_utils import summarise_plan

LOGGER = get_logger("pipeline")
MAX_AGENT_TURNS = 20


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

        for iteration_index in range(1, settings.max_iterations + 1):
            try:
                planner_run = await _run_planner_agent(
                    iteration_index=iteration_index,
                    agent=planner,
                    instruction=build_planner_instruction(
                        settings.goal, feedback=feedback
                    ),
                )
            except MaxTurnsExceeded as exc:
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


            plan_summary, plan_complete = summarise_plan(planner_run.final_output)

            try:
                coder_run = await _run_coder_agent(
                    iteration_index=iteration_index,
                    agent=coder,
                    instruction=build_coder_instruction(plan_summary),
                )
            except MaxTurnsExceeded as exc:
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

            test_result = await execute_tests(iteration_index, settings.workspace)

            try:
                reviewer_run = await _run_qa_agent(
                    iteration_index=iteration_index,
                    agent=reviewer,
                    instruction=build_qa_instruction(
                        plan_summary=plan_summary,
                        coder_summary=coder_run.final_output,
                        test_summary=format_test_summary(test_result),
                    ),
                )
            except MaxTurnsExceeded as exc:
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
            log_iteration_status(
                logger=LOGGER,
                iteration_index=iteration_index,
                status=status,
                qa_review=qa_review,
            )
            if status is True:
                log_workflow_success(
                    logger=LOGGER,
                    iteration_index=iteration_index,
                    total_iterations=len(iterations),
                )
                success = True
                break

            feedback = planner_feedback(qa_review, reviewer_run.final_output)

        log_workflow_completion(
            logger=LOGGER,
            success=success,
            iteration_count=len(iterations),
        )

    return WorkflowResult(iterations=iterations, success=success)


async def _invoke_with_backoff(agent: Agent, instruction: str):
    return await run_with_backoff(agent, instruction, max_turns=MAX_AGENT_TURNS)


@log_agent_execution(
    logger=LOGGER,
    agent_name="planner",
    start_event="iteration.plan.request",
    result_event="iteration.plan.result",
    error_event="iteration.plan.max_turns",
    handled_exceptions=(MaxTurnsExceeded,),
)
async def _run_planner_agent(
    *,
    iteration_index: int,
    agent: Agent,
    instruction: str,
):
    return await _invoke_with_backoff(agent, instruction)


@log_agent_execution(
    logger=LOGGER,
    agent_name="coder",
    start_event="iteration.coder.start",
    result_event="iteration.coder.summary",
    error_event="iteration.coder.max_turns",
    handled_exceptions=(MaxTurnsExceeded,),
)
async def _run_coder_agent(
    *,
    iteration_index: int,
    agent: Agent,
    instruction: str,
):
    return await _invoke_with_backoff(agent, instruction)


@log_agent_execution(
    logger=LOGGER,
    agent_name="qa",
    start_event="iteration.qa.start",
    include_output=False,
    error_event="iteration.qa.max_turns",
    handled_exceptions=(MaxTurnsExceeded,),
)
async def _run_qa_agent(
    *,
    iteration_index: int,
    agent: Agent,
    instruction: str,
):
    return await _invoke_with_backoff(agent, instruction)
