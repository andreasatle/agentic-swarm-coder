"""Prompt definitions for the planner and coder agents."""

from __future__ import annotations

from pathlib import Path

PLANNER_PROMPT = (
    "You are the Planner.\n"
    "Given a coding goal, output a short numbered plan (≤3 steps)\n"
    "and list the files to create/edit under ./workspace. Prefer minimal changes."
)


def build_coder_prompt(workspace: Path) -> str:
    """Return the coder prompt tailored to the workspace path."""

    return (
        "You are the Coder.\n"
        f"Use MCP filesystem tools on {workspace} to implement the plan with minimal edits.\n"
        "Rules:\n"
        "- Read a file before rewriting it\n"
        "- Create parent directories as needed\n"
        "- Persist changes with write_file\n"
        "- Keep messages terse; do the work via tools"
    )
