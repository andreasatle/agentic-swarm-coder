"""Async pipeline that orchestrates the planner and coder agents."""

from __future__ import annotations

from dataclasses import dataclass

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings

from .config import RuntimeSettings
from .prompts import PLANNER_PROMPT, build_coder_prompt


@dataclass(frozen=True)
class WorkflowResult:
    """Container for the textual outputs produced by the workflow."""

    plan_summary: str
    coder_summary: str


async def execute_workflow(settings: RuntimeSettings) -> WorkflowResult:
    """Run the planner and coder agents according to the provided settings."""

    coder_prompt = build_coder_prompt(settings.workspace)

    async with MCPServerStdio(
        name="filesystem",
        params={
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                str(settings.workspace),
            ],
        },
    ) as filesystem_server:
        planner = Agent(name="Planner", instructions=PLANNER_PROMPT)
        coder = Agent(
            name="Coder",
            instructions=coder_prompt,
            mcp_servers=[filesystem_server],
            model_settings=ModelSettings(tool_choice="required"),
        )

        planner_run = await Runner.run(planner, settings.goal)
        coder_run = await Runner.run(coder, "Implement the plan now.")

    return WorkflowResult(
        plan_summary=planner_run.final_output,
        coder_summary=coder_run.final_output,
    )
