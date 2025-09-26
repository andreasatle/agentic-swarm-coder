"""CLI entry point for Agentic Swarm Coder."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from agentic_swarm_coder import main as run_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Agentic Swarm Coder workflow.")
    parser.add_argument(
        "--goal",
        type=str,
        required=True,
        help="Goal description to send to the planner agent.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Path to the workspace directory.",
    )
    parser.add_argument(
        "-n",
        "--iterations",
        type=int,
        default=5,
        help="Maximum planner/coder/QA iterations (default: 5).",
    )
    return parser.parse_args()


def cli(goal: str, workspace: Path, iterations: int = 5) -> None:
    run_workflow(goal=goal, workspace=workspace, max_iterations=iterations)


if __name__ == "__main__":
    arguments = parse_args()
    cli(goal=arguments.goal, workspace=arguments.workspace, iterations=arguments.iterations)
