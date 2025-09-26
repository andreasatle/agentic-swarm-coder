"""Configuration helpers for the Agentic Swarm Coder runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .logging import configure_logging


class ConfigurationError(ValueError):
    """Raised when runtime configuration is invalid or incomplete."""

_WORKSPACE_ENV_VAR = "WORKSPACE_DIR"
_GOAL_ENV_VAR = "GOAL"
_LOG_LEVEL_ENV_VAR = "AGENTIC_SWARM_LOG_LEVEL"
_LOG_FILE_ENV_VAR = "AGENTIC_SWARM_LOG_FILE"
_LOG_FILE_LEVEL_ENV_VAR = "AGENTIC_SWARM_LOG_FILE_LEVEL"
_MAX_ITERATIONS_ENV_VAR = "AGENTIC_SWARM_MAX_ITERATIONS"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RuntimeSettings:
    """Represents the resolved settings required to run the workflow."""

    goal: str
    workspace: Path
    max_iterations: int


def _resolve_workspace(base_dir: Optional[Path], *, allow_from_env: bool = True) -> Path:
    if base_dir is not None:
        workspace = base_dir
    elif allow_from_env and (env_path := os.getenv(_WORKSPACE_ENV_VAR)):
        workspace = Path(env_path)
    else:
        raise ConfigurationError(
            "Workspace path is required. Provide --workspace or set WORKSPACE_DIR."
        )

    workspace = workspace.expanduser().resolve()
    _validate_workspace_location(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _validate_workspace_location(workspace: Path) -> None:
    try:
        if workspace.is_relative_to(_PROJECT_ROOT):
            raise ConfigurationError(
                "Workspace directory must be outside the Agentic Swarm Coder project. "
                "Set --workspace (or WORKSPACE_DIR) to an external path."
            )
    except AttributeError:
        # Python <3.9 fallback—should not trigger in supported versions
        if str(_PROJECT_ROOT) in str(workspace.resolve()):
            raise ConfigurationError(
                "Workspace directory must be outside the Agentic Swarm Coder project."
            )


def load_settings(
    goal: Optional[str] = None,
    workspace: Optional[Path] = None,
    *,
    max_iterations: Optional[int] = None,
) -> RuntimeSettings:
    """Resolve runtime settings from provided parameters and environment variables."""

    load_dotenv()  # Allows .env values to override defaults
    configure_logging(
        os.getenv(_LOG_LEVEL_ENV_VAR),
        log_file=os.getenv(_LOG_FILE_ENV_VAR),
        file_level=os.getenv(_LOG_FILE_LEVEL_ENV_VAR),
    )
    resolved_goal = goal or os.getenv(_GOAL_ENV_VAR)
    if not resolved_goal:
        raise ConfigurationError(
            "Goal is required. Provide --goal or set the GOAL environment variable."
        )
    resolved_workspace = _resolve_workspace(workspace)
    resolved_iterations = _resolve_iterations(max_iterations)
    return RuntimeSettings(
        goal=resolved_goal,
        workspace=resolved_workspace,
        max_iterations=resolved_iterations,
    )


def _resolve_iterations(cli_value: Optional[int]) -> int:
    if cli_value is not None:
        if cli_value < 1:
            raise ConfigurationError("Iterations must be at least 1.")
        return cli_value

    env_value = os.getenv(_MAX_ITERATIONS_ENV_VAR)
    if env_value:
        try:
            parsed = int(env_value)
        except ValueError as exc:
            raise ConfigurationError(
                f"Invalid {_MAX_ITERATIONS_ENV_VAR} value: {env_value!r}"
            ) from exc
        if parsed < 1:
            raise ConfigurationError("Iterations must be at least 1.")
        return parsed

    return 5
