"""Workspace helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .logging import get_logger

LOGGER = get_logger("scaffold")


async def ensure_workspace_initialized(workspace: Path) -> None:
    """Ensure the workspace is ready for agent runs.

    The directory is created if necessary. When ``pyproject.toml`` is absent
    and ``uv`` is available, we run ``uv init .`` inside the workspace and
    guarantee bare ``src`` / ``tests`` packages exist so subsequent agent
    steps have a predictable layout. Existing projects are left untouched.
    """

    workspace = workspace.expanduser()
    workspace.mkdir(parents=True, exist_ok=True)

    legacy_subdir = workspace / "workspace"
    if legacy_subdir.exists():
        LOGGER.warning(
            "Found nested workspace directory at %s. It will not be modified automatically.",
            legacy_subdir,
        )

    pyproject = workspace / "pyproject.toml"
    initialised = False

    if not pyproject.exists():
        if _uv_available():
            _run_uv_init(workspace)
            initialised = True
        else:
            LOGGER.warning(
                "uv command not found; cannot initialise project automatically at %s."
                " Initialise the workspace manually.",
                workspace,
            )

    if initialised:
        _ensure_basic_layout(workspace)


def _uv_available() -> bool:
    try:
        subprocess.run(
            ["uv", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _run_uv_init(workspace: Path) -> None:
    LOGGER.info("Initialising workspace with `uv init .` at %s", workspace)
    try:
        subprocess.run(
            ["uv", "init", "."],
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        LOGGER.error(
            "uv init failed in %s with exit code %s. Output:\n%s",
            workspace,
            exc.returncode,
            exc.output,
        )
        raise


def _ensure_basic_layout(workspace: Path) -> None:
    src_dir = workspace / "src"
    tests_dir = workspace / "tests"

    src_dir.mkdir(exist_ok=True)
    tests_dir.mkdir(exist_ok=True)

    (src_dir / "__init__.py").touch(exist_ok=True)
    (tests_dir / "__init__.py").touch(exist_ok=True)
