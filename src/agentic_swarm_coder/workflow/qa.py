"""Utilities for parsing and summarising QA outputs."""

from __future__ import annotations

import re
from typing import Any

from ..logging import get_logger
from ..schemas import QAReview

LOGGER = get_logger("workflow.qa")

_QA_STATUS_PATTERN = re.compile(
    r"^\s*\**\s*OVERALL_STATUS:\s*(PASS|FAIL)\s*\**\s*$",
    re.IGNORECASE,
)


def qa_passed(review: QAReview | None, qa_output: str) -> bool | None:
    """Determine whether QA approved the iteration."""

    if review is not None:
        return review.status == "PASS"

    for line in reversed(qa_output.strip().splitlines()):
        match = _QA_STATUS_PATTERN.match(line)
        if match:
            status = match.group(1).upper()
            if status == "PASS":
                return True
            if status == "FAIL":
                return False
    return None


def coerce_review(output: Any) -> QAReview | None:
    """Best-effort conversion of an agent output into a QAReview object."""

    if isinstance(output, QAReview):
        return output

    if isinstance(output, str):
        output = output.strip()
        if not output:
            return None
        try:
            return QAReview.model_validate_json(output)
        except ValueError:
            return None

    try:
        return QAReview.model_validate(output)  # type: ignore[arg-type]
    except ValueError:
        return None


def format_summary(review: QAReview | None, raw_output: Any) -> str:
    if review is None:
        return str(raw_output)

    issues_text = "\n- ".join(review.issues)
    issues_block = f"\nIssues:\n- {issues_text}" if review.issues else ""
    return f"Status: {review.status}\nSummary: {review.summary}{issues_block}"


def summarise_output(output: Any, iteration_index: int) -> tuple[QAReview | None, str]:
    review = coerce_review(output)
    summary_text = format_summary(review, output)
    LOGGER.debug(
        "Iteration %d: QA structured summary:\n%s",
        iteration_index,
        summary_text,
    )
    return review, summary_text


def planner_feedback(review: QAReview | None, raw_output: Any) -> str:
    if review is None:
        return str(raw_output)

    if not review.issues:
        return f"QA Summary: {review.summary}\nStatus: {review.status}"

    bullet_list = "\n".join(f"- {issue}" for issue in review.issues)
    return (
        "QA Summary: "
        f"{review.summary}\n"
        "Status: "
        f"{review.status}\n"
        "Outstanding issues:\n"
        f"{bullet_list}"
    )
