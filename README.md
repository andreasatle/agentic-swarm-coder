# Agentic Swarm Coder

Agentic Swarm Coder is a thin orchestration layer around the OpenAI Agents SDK.
It coordinates a **planner**, **coder**, and **QA reviewer**—all connected to the
Model Context Protocol (MCP) filesystem server—to iteratively deliver code and
tests inside a target workspace.

Each iteration works as follows:

1. **Planner** returns a JSON plan (`steps`, `files`, `complete`). The `complete`
   flag signals when the planner believes the goal is fully covered.
2. **Coder** executes the plan using MCP file tools, updating source code and
   tests under the requested workspace.
3. **Test runner** executes `pytest -q` so the next agent operates from real
   results.
4. **QA reviewer** audits the work, enforcing correctness, coverage,
   dependency policy, and stylistic safeguards. Its feedback feeds into the next
   planning round until QA passes or the iteration limit is reached.

The CLI prints the collected plan, coder summary, test output, and QA response
for each iteration, including whether the planner declared the goal complete.

## Project layout

```
├── main.py                         # CLI entry point
├── src/
│   └── agentic_swarm_coder/
│       ├── app.py                  # Public run helpers + CLI formatting
│       ├── config.py               # Settings/env resolution (goal, workspace, iterations)
│       ├── pipeline.py             # Planner/coder/QA workflow loop
│       ├── agent_factory.py        # Agent constructors and prompt wiring
│       ├── prompts/                # Planner, coder, QA prompt templates
│       ├── backoff.py              # Rate-limit retry helper for agents
│       ├── qa_utils.py             # QA output parsing + feedback utilities
│       ├── test_runner.py          # Async pytest execution + summaries
│       ├── results.py              # Dataclasses for iteration/workflow results
│       ├── scaffold.py             # Workspace initialisation (mkdir + `uv init .`)
│       └── logging.py              # Structured logging helpers
```

## Installation

The project uses [uv](https://github.com/astral-sh/uv) for dependency
management, but any modern Python packaging workflow will work.

```bash
# create / refresh the virtual environment
uv sync

# optional: run the test suite
uv run pytest -q
```

`ensure_workspace_initialized()` will call `uv init .` in your workspace the
first time it runs (if `pyproject.toml` is missing and `uv` is available), so no
scaffolding script is required.

## Usage

The CLI now requires both a goal and an explicit workspace path.

```bash
# simplest form
python main.py --goal "Build a timer CLI" --workspace /absolute/path/to/workdir

# shorter iteration loop (default is 5)
python main.py --goal "$(cat goal.txt)" --workspace /tmp/project -n 3

# via the installed entry point (after `uv sync` or `pip install -e .`)
agentic-swarm-coder --goal "Refactor module" --workspace ~/Projects/WorkSpace

# write detailed transcripts to disk while keeping console output concise
python main.py --goal "Debug flaky tests" --workspace /tmp/project --log-file ~/logs/swarm-debug.log
```

Keep the workspace outside of the Agentic Swarm Coder repository to avoid
modifying project files. When the directory is empty, the first iteration will
create `src/` and `tests/` packages automatically.

### Configuration

You can still configure settings via environment variables (for use outside the
CLI or when embedding the workflow):

- `GOAL` – default goal text if not supplied programmatically
- `WORKSPACE_DIR` – default workspace path
- `AGENTIC_SWARM_LOG_LEVEL` – log level (`DEBUG`, `INFO`, etc.)
- `AGENTIC_SWARM_LOG_FILE` – optional path for full JSON logs of every agent turn
- `AGENTIC_SWARM_LOG_FILE_LEVEL` – log level for the file handler (defaults to `DEBUG`)
- `AGENTIC_SWARM_MAX_ITERATIONS` – maximum iteration count (must be ≥ 1)

The CLI flags `--log-file` and `--log-file-level` set the corresponding
environment variables automatically.

Environment variables are processed in `.env` as well, courtesy of `python-dotenv`.

## What to expect

- Planner responses are validated against the `PlannerPlan` schema. If the
  planner emits malformed JSON, the workflow falls back to using its raw output
  and marks `plan_complete=False`.
- The coder must use MCP file operations; conversational replies without edits
  are discouraged.
- QA responses are validated against `QAReview` JSON. Missing or malformed
  responses result in `qa_passed` returning `None`, so the planner will receive
  feedback asking for clarification.
- Pytest output is recorded for every iteration and included in the final
  summary. Failures are surfaced to QA, which is expected to mark the iteration
  as FAIL.

## Contributing / Developing

- Run `uv run pytest -q` before pushing changes.
- Use the `-n/--iterations` flag (or `AGENTIC_SWARM_MAX_ITERATIONS`) to exercise
  longer or shorter workflows during development.
- Logging is structured; set `AGENTIC_SWARM_LOG_LEVEL=DEBUG` (or use
  `--log-file`/`AGENTIC_SWARM_LOG_FILE`) to capture full planner/coder/QA
  transcripts without overwhelming the console output.

Feel free to file issues or PRs with additional workflow stages (e.g. git
automation or PR generation). The current layout keeps planner/coder/QA logic
in separate modules so new agents or stages can be added incrementally.
