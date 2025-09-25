"""Prompt definitions for the planner, coder, and QA agents."""

from __future__ import annotations

from pathlib import Path

PLANNER_PROMPT = (
    "You are the Planner.\n"
    "Given a coding goal (and optional QA feedback), output a short numbered plan (≤3 steps)\n"
    "and list the files to create/edit under ./workspace. Prefer minimal changes.\n"
    "Keep each step small and verifiable—ideally touching a single file or test. If a change would span multiple files or behaviours, split it into multiple plan items.\n"
    "Always include explicit steps for implementing production code and creating/expanding tests that cover happy paths, edge cases, error handling, and CLI/IO behaviour referenced in the goal or QA feedback.\n"
    "If the goal implies multiple CLI invocations, repeated workflows, or other scenarios needing shared state, include a step to design or reuse an appropriate persistence/configuration strategy."
)

CODER_PROMPT_TEMPLATE = (
    "You are the Coder.\n"
    "Use MCP filesystem tools on {workspace} to implement the plan with minimal edits.\n"
    "Rules:\n"
    "- Read a file before rewriting it\n"
    "- Create parent directories as needed\n"
    "- Persist changes with write_file\n"
    "- Keep messages terse; do the work via tools\n"
    "- When adding features, write or extend automated tests that cover success, failure, edge cases, and CLI entry points so QA can verify them via pytest"
)

QA_PROMPT_TEMPLATE = (
    "You are the QA Reviewer.\n"
    "Inspect the work done in {workspace}, focusing on correctness, completeness, and test coverage.\n"
    "Verify that automated tests exist for happy paths, edge cases, error handling, and any CLI/data output described in the plan.\n"
    "Use MCP tools to read files; do not modify them. Fail the review if required coverage is missing or pytest did not pass.\n"
    "Respond strictly as JSON matching the schema: {{\"status\": \"PASS|FAIL\", \"summary\": string, \"issues\": [string, ...]}}."
)


def build_coder_prompt(workspace: Path) -> str:
    """Return the coder prompt tailored to the workspace path."""

    return CODER_PROMPT_TEMPLATE.format(workspace=workspace)


def build_qa_prompt(workspace: Path) -> str:
    """Return the QA reviewer prompt tailored to the workspace path."""

    return QA_PROMPT_TEMPLATE.format(workspace=workspace)


def build_planner_instruction(goal: str, *, feedback: str | None = None) -> str:
    """Return the instruction sent to the planner for the current iteration."""

    base = [
        "Goal:",
        goal.strip(),
    ]
    if feedback:
        base.extend(
            [
                "",
                "QA feedback from previous iteration:",
                feedback.strip(),
                "",
                "Revise the plan to address the feedback while keeping the steps minimal.",
            ]
        )
    else:
        base.extend(
            [
                "",
                "Produce a plan that will achieve the goal.",
            ]
        )

    return "\n".join(base)


def build_coder_instruction(plan_summary: str) -> str:
    """Return the instruction sent to the coder agent after planning."""

    plan_text = plan_summary.strip()
    return (
        "Implement the following plan. Create any missing files or directories as needed.\n\n"
        f"{plan_text}"
    )


def build_qa_instruction(
    *, plan_summary: str, coder_summary: str, test_summary: str | None = None
) -> str:
    """Return the instruction sent to the QA agent after the coder finishes."""

    plan_text = plan_summary.strip()
    coder_text = coder_summary.strip()
    tests_text = (test_summary or "Tests were not executed in this iteration.").strip()
    return (
        "Review the current workspace for alignment with the plan and highlight any issues.\n"
        "Describe missing functionality, broken tests, or risky changes. Analyse whether tests cover edge cases, error handling paths, and CLI interactions demanded by the goal.\n"
        "If pytest failed, or any critical scenario lacks automated coverage, you must return OVERALL_STATUS: FAIL and outline the gaps to address.\n"
        "Finish your response with a single line `OVERALL_STATUS: PASS` or `OVERALL_STATUS: FAIL`.\n"
        "Plan:\n"
        f"{plan_text}\n\n"
        "Coder summary:\n"
        f"{coder_text}\n\n"
        "Test results:\n"
        f"{tests_text}"
    )
