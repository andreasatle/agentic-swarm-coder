# Agentic Swarm Coder

A thin wrapper around the OpenAI Agents SDK that spins up a planner/coder pair
connected to the MCP filesystem server.

## Project layout

```
├── main.py                    # Thin CLI wrapper delegating into the package
├── src/
│   └── agentic_swarm_coder/
│       ├── app.py             # Public entry points; CLI helpers
│       ├── config.py          # Runtime settings resolution (env + defaults)
│       ├── pipeline.py        # Planner/coder orchestration logic
│       ├── prompts.py         # Prompt templates and builders
│       └── __init__.py        # Package exports
```

## Usage

1. Install dependencies (via `uv sync`, `pip install -e .`, etc.).
2. Optionally set `GOAL` and/or `WORKSPACE_DIR` in your environment or `.env`.
3. Run the workflow:
   ```bash
   python main.py --goal "Describe the task here"
   # or via the installed entry point
   agentic-swarm-coder --goal "Describe the task here"
   ```

The CLI prints a plan from the planner agent followed by the coder summary.
