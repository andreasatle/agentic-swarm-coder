"""Public entry points for running the Agentic Swarm Coder workflow."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from .config import RuntimeSettings, load_settings
from .pipeline import IterationResult, WorkflowResult, execute_workflow


async def run_async(goal: Optional[str] = None, workspace: Optional[Path] = None) -> WorkflowResult:
    """Run the workflow asynchronously and return the collected results."""

    settings = load_settings(goal=goal, workspace=workspace)
    return await execute_workflow(settings)


def run(goal: Optional[str] = None, workspace: Optional[Path] = None) -> WorkflowResult:
    """Synchronous helper that runs the async workflow via ``asyncio.run``."""

    return asyncio.run(run_async(goal=goal, workspace=workspace))


def format_cli_output(result: WorkflowResult) -> str:
    """Format the workflow result for display in a CLI context."""

    sections: list[str] = []
    for index, iteration in enumerate(result.iterations, start=1):
        sections.extend(
            [
                f"\n=== ITERATION {index} ===\n",
                "--- PLAN ---\n",
                f"{iteration.plan_summary}\n",
                "\n--- CODER SUMMARY ---\n",
                f"{iteration.coder_summary}\n",
                "\n--- TEST RESULTS ---\n",
                _format_iteration_test_output(iteration),
                "\n--- QA SUMMARY ---\n",
                f"{iteration.qa_summary}\n",
            ]
        )

    overall = "SUCCESS" if result.success else "INCOMPLETE"
    sections.append(f"\n=== RESULT: {overall} ===\n")
    return "".join(sections)


def _format_iteration_test_output(iteration: IterationResult) -> str:
    command = iteration.test_command or "pytest"
    exit_code = iteration.test_exit_code
    output = (iteration.test_output or "<no output>").strip()
    if exit_code is None:
        status = "NOT RUN"
    else:
        status = "PASS" if exit_code == 0 else f"FAIL (exit {exit_code})"
    return f"Command: {command}\nStatus: {status}\nOutput:\n{output}\n"


def main(goal: Optional[str] = None, workspace: Optional[Path] = None) -> None:
    """Entry point for the CLI script."""

    result = run(goal=goal, workspace=workspace)
    print(format_cli_output(result))
