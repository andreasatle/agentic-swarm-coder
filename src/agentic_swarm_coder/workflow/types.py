"""Shared data structures for workflow execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..schemas import QAReview


@dataclass(frozen=True)
class TestRunResult:
    """Represents the outcome of running the project test suite."""

    command: str | None
    exit_code: int | None
    output: str | None


@dataclass(frozen=True)
class IterationResult:
    """Container for the textual outputs produced in a single loop iteration."""

    plan_summary: str
    coder_summary: str
    qa_summary: str
    qa_review: Optional[QAReview]
    test_command: str | None
    test_exit_code: int | None
    test_output: str | None


@dataclass(frozen=True)
class WorkflowResult:
    """High-level outcome of running the multi-agent workflow."""

    iterations: list[IterationResult]
    success: bool


def build_iteration_result(
    *,
    plan_summary: str,
    coder_summary: str,
    qa_summary: str,
    qa_review: QAReview | None,
    test_result: TestRunResult,
) -> IterationResult:
    """Helper to construct an iteration result from component parts."""

    return IterationResult(
        plan_summary=plan_summary,
        coder_summary=coder_summary,
        qa_summary=qa_summary,
        qa_review=qa_review,
        test_command=test_result.command,
        test_exit_code=test_result.exit_code,
        test_output=test_result.output,
    )
