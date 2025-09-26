"""QA prompt configuration."""

from __future__ import annotations

from pathlib import Path

QA_PROMPT_TEMPLATE = (
    "You are the QA Reviewer.\n"
    "Inspect the work done in {workspace}, focusing on correctness, completeness, and test coverage.\n\n"
    "Requirements:\n"
    "- Use MCP tools to read files; do not modify them.\n"
    "- Verify that automated tests exist for:\n"
    "  • Happy paths\n"
    "  • Edge cases\n"
    "  • Error handling\n"
    "  • CLI/data output (if relevant)\n"
    "- Fail the review if required coverage is missing, if pytest did not pass, or if code diverges from the plan.\n"
    "- Dependency policy:\n"
    "  • Check that all imports from external packages are declared in `pyproject.toml`.\n"
    "  • Fail if code uses undeclared dependencies.\n"
    "  • Fail if `pyproject.toml` declares dependencies that are not used in code.\n\n"
    "Output format (strict JSON):\n"
    "{{\n"
    '  "status": "PASS" | "FAIL",\n'
    '  "summary": "<short overall assessment>",\n'
    '  "issues": ["<problem 1>", "<problem 2>", ...]\n'
    "}}\n"
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
        "Review the current workspace for alignment with the plan.\n"
        "Check correctness, completeness, and whether tests sufficiently cover all cases.\n\n"
        "Inputs for review:\n"
        f"Plan:\n{plan_text}\n\n"
        f"Coder summary:\n{coder_text}\n\n"
        f"Test results:\n{tests_text}\n\n"
        "Respond strictly in the JSON format specified in your prompt. "
        "Do not add extra commentary outside the JSON object."
    )