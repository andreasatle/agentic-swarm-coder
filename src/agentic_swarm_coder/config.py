"""Configuration helpers for the Agentic Swarm Coder runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .logging import configure_logging

_WORKSPACE_ENV_VAR = "WORKSPACE_DIR"
_GOAL_ENV_VAR = "GOAL"
_LOG_LEVEL_ENV_VAR = "AGENTIC_SWARM_LOG_LEVEL"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
        raise ValueError(
            "Workspace path is required. Provide --workspace or set WORKSPACE_DIR."
        )

    workspace = workspace.expanduser().resolve()
    _validate_workspace_location(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _validate_workspace_location(workspace: Path) -> None:
    try:
        if workspace.is_relative_to(_PROJECT_ROOT):
            raise ValueError(
                "Workspace directory must be outside the Agentic Swarm Coder project. "
                "Set --workspace (or WORKSPACE_DIR) to an external path."
            )
    except AttributeError:
        # Python <3.9 fallback—should not trigger in supported versions
        if str(_PROJECT_ROOT) in str(workspace.resolve()):
            raise ValueError(
                "Workspace directory must be outside the Agentic Swarm Coder project."
            )


def load_settings(goal: Optional[str] = None, workspace: Optional[Path] = None) -> RuntimeSettings:
    """Resolve runtime settings from provided parameters and environment variables."""

    load_dotenv()  # Allows .env values to override defaults
    configure_logging(os.getenv(_LOG_LEVEL_ENV_VAR))
    resolved_goal = goal or os.getenv(_GOAL_ENV_VAR)
    if not resolved_goal:
        raise ValueError(
            "Goal is required. Provide --goal or set the GOAL environment variable."
        )
    resolved_workspace = _resolve_workspace(workspace)
    return RuntimeSettings(goal=resolved_goal, workspace=resolved_workspace)
