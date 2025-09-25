"""Coder prompt configuration."""

from __future__ import annotations

from pathlib import Path

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
