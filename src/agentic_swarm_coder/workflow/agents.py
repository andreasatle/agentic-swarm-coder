"""Factory helpers for constructing agents used in the workflow."""

from __future__ import annotations

from agents import Agent
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings

from ..prompts import (
    PLANNER_PROMPT,
    build_coder_instruction,
    build_coder_prompt,
    build_planner_instruction,
    build_qa_instruction,
    build_qa_prompt,
)
from ..schemas import QAReview

__all__ = [
    "create_planner",
    "create_coder",
    "create_qa_reviewer",
    "build_planner_instruction",
    "build_coder_instruction",
    "build_coder_prompt",
    "build_qa_instruction",
    "build_qa_prompt",
]


def create_planner() -> Agent:
    return Agent(name="Planner", instructions=PLANNER_PROMPT)


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
