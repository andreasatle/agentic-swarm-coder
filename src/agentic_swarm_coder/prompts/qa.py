"""QA prompt configuration."""

from __future__ import annotations

from pathlib import Path

QA_PROMPT_TEMPLATE = (
    "You are the QA Reviewer.\n"
    "Inspect the work done in {workspace}, focusing on correctness, completeness, and test coverage.\n"
    "Verify that automated tests exist for happy paths, edge cases, error handling, and any CLI/data output described in the plan.\n"
    "Use MCP tools to read files; do not modify them. Fail the review if required coverage is missing or pytest did not pass.\n"
    "Respond strictly as JSON matching the schema: {{\"status\": \"PASS|FAIL\", \"summary\": string, \"issues\": [string, ...]}}."
)


def build_qa_prompt(workspace: Path) -> str:
    """Return the QA reviewer prompt tailored to the workspace path."""

    return QA_PROMPT_TEMPLATE.format(workspace=workspace)


def build_qa_instruction(
    *,
    plan_summary: str,
    coder_summary: str,
    test_summary: str | None = None,
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
