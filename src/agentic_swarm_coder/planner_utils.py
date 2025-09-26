"""Helper utilities for working with planner outputs."""

from __future__ import annotations

from typing import Tuple

from .schemas import PlannerPlan


def summarise_plan(output: object) -> Tuple[str, bool]:
    """Convert planner output into a textual summary and completion flag."""

    if isinstance(output, PlannerPlan):
        summary_text = output.summary()
        return (summary_text or "Planner returned an empty plan.", output.complete)

    text = str(output).strip() if output is not None else ""
    if not text:
        return ("Planner returned no output.", False)
    return text, False
