"""Planner prompt configuration."""

from __future__ import annotations

PLANNER_PROMPT = (
    "You are the Planner.\n"
    "Given a coding goal (and optional QA feedback), output a short numbered plan (≤3 steps)\n"
    "and list the files to create/edit under ./workspace. Prefer minimal changes.\n"
    "Keep each step small and verifiable—ideally touching a single file or test. If a change would span multiple files or behaviours, split it into multiple plan items.\n"
    "Always include explicit steps for implementing production code and creating/expanding tests that cover happy paths, edge cases, error handling, and CLI/IO behaviour referenced in the goal or QA feedback.\n"
    "If the goal implies multiple CLI invocations, repeated workflows, or other scenarios needing shared state, include a step to design or reuse an appropriate persistence/configuration strategy."
)


def build_planner_instruction(goal: str, *, feedback: str | None = None) -> str:
    """Return the instruction sent to the planner for the current iteration."""

    base = ["Goal:", goal.strip()]
    if feedback:
        base.extend(
            [
                "",
                "QA feedback from previous iteration:",
                feedback.strip(),
                "",
                "Revise the plan to address the feedback while keeping the steps minimal.",
            ]
        )
    else:
        base.extend(["", "Produce a plan that will achieve the goal."])

    return "\n".join(base)
