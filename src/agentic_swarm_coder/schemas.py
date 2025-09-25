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
