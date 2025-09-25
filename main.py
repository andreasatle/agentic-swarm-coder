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
        help="Override the goal to send to the planner agent.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Optional path to the workspace directory.",
    )
    return parser.parse_args()


def cli(goal: Optional[str] = None, workspace: Optional[Path] = None) -> None:
    run_workflow(goal=goal, workspace=workspace)


if __name__ == "__main__":
    arguments = parse_args()
    cli(goal=arguments.goal, workspace=arguments.workspace)
