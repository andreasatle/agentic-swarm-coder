"""Public entry points for running the Agentic Swarm Coder workflow."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from .config import RuntimeSettings, load_settings
from .pipeline import WorkflowResult, execute_workflow


async def run_async(goal: Optional[str] = None, workspace: Optional[Path] = None) -> WorkflowResult:
    """Run the workflow asynchronously and return the collected results."""

    settings = load_settings(goal=goal, workspace=workspace)
    return await execute_workflow(settings)


def run(goal: Optional[str] = None, workspace: Optional[Path] = None) -> WorkflowResult:
    """Synchronous helper that runs the async workflow via ``asyncio.run``."""

    return asyncio.run(run_async(goal=goal, workspace=workspace))


def format_cli_output(result: WorkflowResult) -> str:
    """Format the workflow result for display in a CLI context."""

    return (
        "\n--- PLAN ---\n"
        f"{result.plan_summary}\n"
        "\n--- CODER SUMMARY ---\n"
        f"{result.coder_summary}\n"
    )


def main(goal: Optional[str] = None, workspace: Optional[Path] = None) -> None:
    """Entry point for the CLI script."""

    result = run(goal=goal, workspace=workspace)
    print(format_cli_output(result))
