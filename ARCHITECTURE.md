# Rubricon — Architecture

## Component map

```
┌────────────────┐    YAML     ┌─────────────────┐
│  suite.yaml    │────────────▶│  Suite Loader   │
└────────────────┘             │  (pydantic)     │
                               └────────┬────────┘
                                        │
                                        ▼
┌────────────────┐             ┌─────────────────┐    Trajectory     ┌──────────────┐
│  Agent adapter │◀────────────│   Run Engine    │──────────────────▶│   SQLite     │
│  (your code)   │   .run()    │  (asyncio pool) │                   │   storage    │
└────────────────┘             └────────┬────────┘                   └──────┬───────┘
                                        │ trajectory + rubric                │
                                        ▼                                    │
                               ┌─────────────────┐    scores                │
                               │  LLM Judge      │─────────────────────────▶│
                               │  (Anthropic)    │                           │
                               └─────────────────┘                           │
                                                                             │
┌────────────────┐    REST      ┌─────────────────┐                         │
│  Next.js UI    │◀────────────▶│  FastAPI server │◀────────────────────────┘
│  (dashboard)   │              │  (read-only)    │
└────────────────┘              └─────────────────┘
```

---

## Data flow: what happens when `rubricon run suite.yaml` is called

1. **Loader** (`loader.py`) reads the YAML file and validates it against the Pydantic `Suite` model. A `ValidationError` surfaces with field-level context before any API calls are made.

2. **CLI** (`cli.py`) opens (or creates) `rubricon.db`, persists the suite record, and calls `execute_run` with the loaded suite and the configured agent.

3. **Run engine** (`engine.py`) fans out one coroutine per scenario, bounded by a semaphore (default concurrency = 4). Each coroutine calls `agent.run(scenario.input)` and collects the returned `Trajectory`.

4. **Agent** (`agent.py`) drives a real Anthropic agentic loop. Every model call, tool call, tool result, and final output is appended to a `spans` list. When `stop_reason != "tool_use"` the agent wraps spans into a `Trajectory` and returns.

5. **Judge phase** (`engine.py`, `judge.py`) fires once the agent phase is complete. For each scenario, all rubric criteria are judged concurrently. `judge_criterion` formats a prompt (from `prompts/judge_v1.py`), calls Claude with `tool_choice={"type":"any"}` and a `record_score` tool, then parses the forced tool call into a `CriterionScore`. Judge errors are caught per-criterion so a single bad call never aborts the run.

6. **Storage** (`storage.py`) persists the run record, all `TrajectorySpan` rows, and all `CriterionScore` rows in a single async transaction. `compute_weighted_score` calculates the per-scenario weighted average; the run's `overall_score` is the mean across scenarios.

7. **CLI** renders a Rich live progress table updated after each scenario's judge phase completes. Final output: run ID + overall score.

---

## Key modules

**`models.py`** — Pydantic domain models: `Suite`, `Scenario`, `Rubric`, `Criterion`, `Trajectory`, `TrajectorySpan`, `SpanType`, `CriterionScore`, `ScenarioScore`, `RunRecord`. All models are fully JSON-serializable; `TrajectorySpan.data` is a free `dict` so span payloads can evolve without schema migrations.

**`agent.py`** — The `Agent` protocol (a `@runtime_checkable Protocol` with a single `async def run(self, input: str) -> Trajectory` method) plus `ResearchAgent`, the reference implementation. `ResearchAgent` drives a real Anthropic agentic loop with a stubbed `web_search` tool and captures every turn as trajectory spans.

**`engine.py`** — `execute_run` orchestrates the full pipeline: fan-out agent calls, fan-out judge calls, persist results. Uses `asyncio.Semaphore` for bounded concurrency. The agent phase and judge phase are kept separate so `--no-judge` can skip scoring while still persisting trajectories.

**`judge.py`** — `judge_criterion` takes a `Trajectory` and a `Criterion` and returns a `CriterionScore`. Forces structured output via `tool_choice={"type":"any"}` with a `record_score` tool whose input schema mirrors `CriterionScore`. `PROMPT_VERSION` is read from `prompts/judge_v1.py` and stored in every score row.

**`schema.py`** — SQLAlchemy 2.0 async ORM with five tables. Relationships are expressed as foreign keys, not ORM relationships, to keep the schema readable and migration-friendly.

**`storage.py`** — `persist_run` writes a run, its trajectory spans, and its scores atomically. `get_run` re-hydrates a full `RunRecord` with nested `ScenarioScore` and `CriterionScore` objects. `list_suites` and `list_runs` return lightweight summary rows for the API.

**`api.py`** — Read-only FastAPI application. Five endpoints: `GET /suites`, `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/scenarios/{id}/trajectory`, `GET /compare`. CORS is open to `localhost:3000`. No write endpoints — the CLI is the only writer.

**`cli.py`** — Typer application with three commands: `run` (execute a suite, stream Rich progress), `serve` (start the FastAPI server via uvicorn), `compare` (print a Rich diff table for two run IDs).

**Dashboard** (`dashboard/src/app/`) — Next.js 14 App Router. Runs list with per-run score chips and compare-selection checkboxes; run detail with per-scenario score cards; trajectory timeline with collapsible span cards color-coded by span type; compare page with green/red delta chips and expandable per-criterion rows.

---

## Database schema

Five tables. Foreign keys are enforced at the application layer (SQLite does not enforce them by default).

**suites** — id (TEXT PK), name, description, yaml_path, created_at

**runs** — id (TEXT PK), suite_id (→ suites), overall_score (REAL), created_at, metadata (JSON)

**scenario_results** — id (TEXT PK), run_id (→ runs), scenario_id (TEXT), weighted_score (REAL), passed (BOOL), created_at

**trajectory_spans** — id (TEXT PK), scenario_result_id (→ scenario_results), type (TEXT), started_at, ended_at, data (JSON)

**scores** — id (TEXT PK), scenario_result_id (→ scenario_results), criterion_name (TEXT), score (INT 1–5), justification (TEXT), cited_span_id (TEXT, nullable), prompt_version (TEXT), created_at

---

## Judge design

`judge_criterion` calls Claude (`claude-haiku-4-5`) with `tool_choice={"type":"any"}` and a single tool named `record_score`. The tool's input schema requires `score` (integer 1–5), `justification` (string), and `cited_span_id` (string, optional). Because the model is forced to call a tool, the output is always parseable — no regex, no brittle JSON extraction.

`PROMPT_VERSION` (e.g. `"v1"`) is defined in `prompts/judge_v1.py` and stored in every `scores` row. When the prompt changes, the version bumps; historical scores remain tagged with the version that produced them, making prompt drift visible in diffs without touching existing data.

`cited_span_id` links a justification back to a specific `TrajectorySpan`. The dashboard uses this to highlight and scroll to the referenced span in the trajectory timeline. The URL-shareable `?highlight=` param stores the same ID.

---

## Trajectory model

`SpanType` is an enum with four values:

- `MODEL_CALL` — one Anthropic API call; `data` contains `input_messages`, `output_content`, `model`, and `usage` (token counts)
- `TOOL_CALL` — one tool invocation; `data` contains `tool_name`, `tool_input`, `tool_use_id`
- `TOOL_RESULT` — the result returned to the model; `data` contains `tool_use_id`, `tool_name`, `content`
- `FINAL_OUTPUT` — the agent's terminal response; `data` contains `text`

Spans are ordered by `started_at` timestamp. Each span has a stable `id` (UUID hex) that survives serialization. `Trajectory` is immutable after construction — `spans` is a tuple-like list, `final_output` is a string. The entire trajectory serializes to JSON via `.model_dump()` for storage and API responses.

Token counts are in `TrajectorySpan.data["usage"]` for every `MODEL_CALL` span, enabling cost/latency aggregation without schema changes.
