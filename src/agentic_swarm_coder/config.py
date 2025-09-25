"""Configuration helpers for the Agentic Swarm Coder runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .logging import configure_logging

#_DEFAULT_GOAL = "Add add(a,b) in src/add.py and a pytest in tests/test_add.py"

_DEFAULT_GOAL = """
Build a small command-line “task timer” utility inside the workspace.

Requirements:
1. Create `workspace/src/task_timer.py` with:
   - a `TaskTimer` class that can `start(task_name)`, `stop()`, and accumulate elapsed time per task (store state in memory).
   - a `to_report()` method that returns a JSON-serializable dict of `{task_name: total_seconds}`.
   - raise a `RuntimeError` if `stop()` is called without a matching `start()`.

2. Add `workspace/src/cli.py` exposing a CLI with these commands:
   - `task-timer start <name>` to start timing a task.
   - `task-timer stop` to stop timing the current task.
   - `task-timer report --format=json|table` which prints either the raw JSON from `to_report()` or an ASCII table.

3. Write pytest tests in `workspace/tests/test_task_timer.py` that cover:
   - starting/stopping multiple tasks in sequence.
   - the error path for calling `stop()` without `start()`.
   - at least one test that uses `time.sleep` with a small patch/mocked clock so tests stay fast.

4. Document usage in `workspace/README.md`, including an example CLI session.

5. Ensure the CLI entry point is wired up in `workspace/pyproject.toml` (console script `task-timer`).
"""

_WORKSPACE_ENV_VAR = "WORKSPACE_DIR"
_GOAL_ENV_VAR = "GOAL"
_LOG_LEVEL_ENV_VAR = "AGENTIC_SWARM_LOG_LEVEL"


@dataclass(frozen=True)
class RuntimeSettings:
    """Represents the resolved settings required to run the workflow."""

    goal: str
    workspace: Path


def _resolve_workspace(base_dir: Optional[Path], *, allow_from_env: bool = True) -> Path:
    if base_dir is not None:
        workspace = base_dir
    elif allow_from_env and (env_path := os.getenv(_WORKSPACE_ENV_VAR)):
        workspace = Path(env_path)
    else:
        workspace = Path(__file__).resolve().parents[2] / "workspace"

    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def load_settings(goal: Optional[str] = None, workspace: Optional[Path] = None) -> RuntimeSettings:
    """Resolve runtime settings from provided parameters and environment variables."""

    load_dotenv()  # Allows .env values to override defaults
    configure_logging(os.getenv(_LOG_LEVEL_ENV_VAR))
    resolved_goal = goal or os.getenv(_GOAL_ENV_VAR, _DEFAULT_GOAL)
    resolved_workspace = _resolve_workspace(workspace)
    return RuntimeSettings(goal=resolved_goal, workspace=resolved_workspace)
