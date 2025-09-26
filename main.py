"""CLI entry point for Agentic Swarm Coder."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from agentic_swarm_coder import main as run_workflow

LOG_FILE_ENV_VAR = "AGENTIC_SWARM_LOG_FILE"
LOG_FILE_LEVEL_ENV_VAR = "AGENTIC_SWARM_LOG_FILE_LEVEL"


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
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Optional path for detailed agent logs (sets AGENTIC_SWARM_LOG_FILE).",
    )
    parser.add_argument(
        "--log-file-level",
        type=str,
        help="Log level to use for the log file (sets AGENTIC_SWARM_LOG_FILE_LEVEL).",
    )
    return parser.parse_args()


def cli(goal: str, workspace: Path, iterations: int = 5) -> None:
    run_workflow(goal=goal, workspace=workspace, max_iterations=iterations)


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.log_file is not None:
        os.environ[LOG_FILE_ENV_VAR] = str(arguments.log_file)
    if arguments.log_file_level is not None:
        os.environ[LOG_FILE_LEVEL_ENV_VAR] = arguments.log_file_level
    cli(goal=arguments.goal, workspace=arguments.workspace, iterations=arguments.iterations)
