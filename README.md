# Agentic Swarm Coder

A thin wrapper around the OpenAI Agents SDK that runs a planner/coder/QA trio
connected to the MCP filesystem server. The agents iterate together: the planner
produces a plan, the coder implements it, the QA reviewer audits the result, and
any QA feedback is fed back into the planner for up to three refinement rounds.

## Project layout

```
├── main.py                    # Thin CLI wrapper delegating into the package
├── src/
│   └── agentic_swarm_coder/
│       ├── app.py             # Public entry points; CLI helpers
│       ├── config.py          # Runtime settings resolution (env + defaults)
│       ├── pipeline.py        # Planner/coder/QA orchestration logic
│       ├── prompts.py         # Prompt templates and builders
│       └── __init__.py        # Package exports
```

## Usage

1. Install dependencies (via `uv sync`, `pip install -e .`, etc.).
2. Optionally set `GOAL`, `WORKSPACE_DIR`, and/or `AGENTIC_SWARM_LOG_LEVEL` (e.g. `DEBUG`) in your environment or `.env`.
3. Run the workflow:
   ```bash
   python main.py --goal "Describe the task here"
   # or via the installed entry point
   agentic-swarm-coder --goal "Describe the task here"
   ```

The CLI prints a plan from the planner agent, the coder summary, and the QA review.
Each iteration also runs `pytest -q` inside the workspace so QA can reason from real test results.
