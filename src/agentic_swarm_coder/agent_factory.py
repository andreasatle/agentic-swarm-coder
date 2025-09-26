"""Factory helpers for constructing the planner/coder/QA agents."""

from __future__ import annotations

from agents import Agent
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings

from .schemas import PlannerPlan, QAReview
from .prompts import PLANNER_PROMPT

__all__ = [
    "create_planner",
    "create_coder",
    "create_qa_reviewer",
]


def create_planner() -> Agent:
    return Agent(
        name="Planner",
        instructions=PLANNER_PROMPT,
        output_type=PlannerPlan,
    )


def create_coder(instructions: str, filesystem_server: MCPServerStdio) -> Agent:
    return Agent(
        name="Coder",
        instructions=instructions,
        mcp_servers=[filesystem_server],
        model_settings=ModelSettings(tool_choice="required"),
    )


def create_qa_reviewer(instructions: str, filesystem_server: MCPServerStdio) -> Agent:
    return Agent(
        name="QA",
        instructions=instructions,
        mcp_servers=[filesystem_server],
        model_settings=ModelSettings(tool_choice="required"),
        output_type=QAReview,
    )
