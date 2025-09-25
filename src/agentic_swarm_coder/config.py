"""Configuration helpers for the Agentic Swarm Coder runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_DEFAULT_GOAL = "Add add(a,b) in src/add.py and a pytest in tests/test_add.py"
_WORKSPACE_ENV_VAR = "WORKSPACE_DIR"
_GOAL_ENV_VAR = "GOAL"


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
    resolved_goal = goal or os.getenv(_GOAL_ENV_VAR, _DEFAULT_GOAL)
    resolved_workspace = _resolve_workspace(workspace)
    return RuntimeSettings(goal=resolved_goal, workspace=resolved_workspace)
