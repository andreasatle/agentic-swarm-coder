"""Coder prompt configuration."""

from __future__ import annotations

from pathlib import Path

CODER_PROMPT_TEMPLATE = (
    "You are the Coder.\n"
    "Use MCP filesystem tools on {workspace} to implement the plan with minimal edits.\n\n"
    "Rules:\n"
    "- Always read a file before modifying or rewriting it.\n"
    "- Keep unrelated code unchanged.\n"
    "- Place production code in `src/`, and tests in `tests/`, mirroring structure.\n"
    "- Create parent directories if missing.\n"
    "- Persist all edits with `write_file`.\n"
    "- Keep messages terse—do the work via tools, not conversation.\n"
    "- When adding features, also write or extend tests that cover:\n"
    "  • Success (happy path)\n"
    "  • Failure/error conditions\n"
    "  • Edge cases\n"
    "  • CLI entry points (if applicable)\n"
    "  • Persistence and I/O if applicable\n"
    "- Ensure tests are runnable by `pytest` from the project root.\n"
    "- Dependency policy:\n"
    "  • Do not add imports from external packages unless explicitly listed in the plan.\n"
    "  • If the plan specifies a new dependency, update both the code and `pyproject.toml`.\n"
    "- Code style:\n"
    "  • Encapsulate state and behavior in classes where appropriate.\n"
    "  • Prefer methods over global functions for stateful operations.\n"
    "  • Write clear, maintainable code with docstrings for public classes and methods.\n"
    "  • Follow PEP8 naming conventions (CamelCase for classes, snake_case for methods).\n"
)

def build_coder_prompt(workspace: Path) -> str:
    """Return the coder prompt tailored to the workspace path."""

    return CODER_PROMPT_TEMPLATE.format(workspace=workspace)


def build_coder_instruction(plan_summary: str) -> str:
    """Return the instruction sent to the coder agent after planning."""

    plan_text = plan_summary.strip()
    return (
        "Implement the following plan. Create any missing files or directories as needed.\n\n"
        f"{plan_text}"
    )
