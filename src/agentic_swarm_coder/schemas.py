"""Pydantic models shared across the agent workflow."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class QAReview(BaseModel):
    """Structured response produced by the QA agent."""

    status: Literal["PASS", "FAIL"] = Field(
        ..., description="Overall judgement of the iteration outcome."
    )
    summary: str = Field(
        ..., description="High-level recap of findings for this iteration."
    )
    issues: List[str] = Field(
        default_factory=list,
        description="Specific problems or follow-up actions discovered by QA.",
    )


class PlannerPlan(BaseModel):
    """Structured response produced by the planner agent."""

    steps: List[str] = Field(
        ...,
        description="Ordered list of planned actions expressed as short imperatives.",
    )
    files: List[str] = Field(
        default_factory=list,
        description="Files or directories to create or modify relative to the workspace root.",
    )
    complete: bool = Field(
        ...,
        description="True when this plan represents the final set of steps to satisfy the goal.",
    )

    def summary(self) -> str:
        numbered_steps = "\n".join(
            f"{index}. {step.strip()}" for index, step in enumerate(self.steps, start=1)
        )
        files_block = (
            "\n\nFiles to touch:\n" + "\n".join(sorted({path.strip() for path in self.files}))
            if self.files
            else ""
        )
        status_line = "\n\nPlanner marked goal as complete." if self.complete else ""
        return f"{numbered_steps}{files_block}{status_line}".strip()
