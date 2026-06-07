# Rubricon

> Rubric-based evaluation harness for AI agents. Define test scenarios and grading criteria in YAML, point it at your agent, get structured LLM-judged scores plus full trajectory traces — all viewable in a web dashboard.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## What works (M7 — run comparison view)

- **Monorepo initialized** with `uv` (Python) and `pnpm` workspaces.
- **Pydantic domain models** — `Suite`, `Scenario`, `Rubric`, `Criterion`, `Trajectory`, `TrajectorySpan`, `ScenarioResult`, `RunRecord`, `CriterionScore`, `ScenarioScore`.
- **YAML loader** — `load_suite(path)` validates YAML against Pydantic models with friendly error messages.
- **SQLAlchemy 2.0 async ORM** — five tables: `suites`, `runs`, `scenario_results`, `trajectory_spans`, `scores`.
- **Async storage layer** — `persist_run` persists scores alongside spans; `get_run` hydrates `CriterionScore` objects from the `scores` table. `list_suites` and `list_runs` support the API.
- **Agent adapter protocol** + `ResearchAgent` — drives a real Anthropic agentic loop with a stubbed `web_search` tool; captures every model call, tool call, tool result, and final output as `TrajectorySpan` objects.
- **Run engine** — `execute_run` runs all scenarios concurrently; after agent phase completes, a judge phase fires all `judge_criterion` calls concurrently per scenario.
- **LLM judge** (`rubricon/judge.py`) — `judge_criterion` calls Claude (`claude-haiku-4-5`) with `tool_choice={"type":"any"}` forcing a structured `record_score` tool call; returns `CriterionScore` (1–5 + justification + cited span). Judge errors are caught per-criterion so one bad call never fails the run.
- **Versioned judge prompts** (`rubricon/prompts/judge_v1.py`) — `PROMPT_VERSION = "v1"` baked into every score; changing the template is visible in snapshot diffs.
- **Weighted scoring** — `compute_weighted_score` computes `sum(score×weight)/sum(weight)`; per-run `overall_score` is the mean of scenario weighted scores.
- **CLI** — `rubricon run <suite.yaml>` streams a Rich live progress table with `x.xx/5` scores after the judge phase; prints `Overall score: x.xx/5` in the summary. Pass `--no-judge` to skip judging. `rubricon serve` starts the FastAPI server. `rubricon compare <run_a> <run_b>` prints a Rich diff table.
- **FastAPI read-only API** (`rubricon/api.py`) — five endpoints: `GET /suites`, `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/scenarios/{id}/trajectory`, `GET /compare?run_a={id}&run_b={id}`. CORS enabled for `localhost:3000`.
- **Next.js dashboard** — nav bar (Rubricon / Runs / Suites), runs list page with color-coded scores and run-selection checkboxes, run detail page with per-scenario score cards and criterion chips, suites list page, compare page (`/compare`).
- **Trajectory timeline** — collapsible span-by-span view of every agent trajectory at `/runs/{id}/scenarios/{id}`; spans color-coded by type (model call → blue, tool call → amber, tool result → green, final output → violet); token counts and latency per span; clicking a criterion justification with a `cited_span_id` highlights and scrolls to the referenced span. Highlight state is URL-shareable via `?highlight={spanId}`.
- **Timeline links** — "Timeline →" link on each scenario card in the run detail page; criterion justifications with cited spans link directly to the pre-highlighted timeline.
- **Example suite** — `backend/examples/research_agent_suite.yaml` (3 scenarios, 2 rubric criteria).
- **Run comparison** — `GET /compare?run_a={id}&run_b={id}` returns structured diff: overall-score delta, per-scenario delta, per-criterion delta with pass indicators. Regressions and improvements are flagged with sign and colour.
- **Compare dashboard** — `/compare?run_a=...&run_b=...` renders the diff with green highlights for improvements (Δ > 0.1) and red for regressions (Δ < −0.1). Clicking a scenario row expands per-criterion breakdown inline.
- **Runs-list compare selector** — checkboxes on the runs list let you select exactly 2 runs; a sticky "Compare selected runs →" button navigates to the compare page.
- **`rubricon compare <run_a> <run_b>` CLI** — prints Rich tables: overall header, per-scenario table with coloured deltas, and per-criterion breakdowns for changed scenarios.
- **Test suite** — `test_models.py`, `test_loader.py`, `test_engine.py`, `test_storage.py`, `test_judge.py`, `test_api.py` (12 API tests, 3 new compare tests) under `backend/tests/`.

---

## Why this exists

Agent teams keep rebuilding the same brittle eval loop: a bag of prompts, ad-hoc assertions, and `print()` statements. There is no shared mental model for *what "good" looks like* per scenario. Rubricon makes that explicit: every test case carries a **rubric** — weighted criteria with 1–5 descriptors — and an LLM judge scores each criterion against the agent's full **trajectory**, not just the final answer.

This catches the failure mode every agent developer has hit: right answer, wrong reasoning; or right reasoning, hallucinated tool call.

---

## Demo flow

Steps 1–8 work today.

1. **Clone and install**
   ```bash
   git clone https://github.com/your-org/rubricon.git
   cd rubricon
   cd backend && uv sync && cd ..
   pnpm i
   ```

2. **Set your API key**
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

3. **Run a suite** — terminal streams scenarios live with Rich progress table; exits with run ID and pass/fail summary
   ```bash
   cd backend
   rubricon run examples/research_agent_suite.yaml
   ```

4. **Open the dashboard**
   ```bash
   # Terminal 1 — API server
   cd backend
   rubricon serve          # → http://localhost:8000

   # Terminal 2 — Next.js dashboard
   cd dashboard
   pnpm dev                # → http://localhost:3000
   ```

5. **Review results** — open `http://localhost:3000`; click the latest run, see overall score and per-scenario cards with criterion scores colored green/yellow/red.

6. **Inspect a failure** — click "Timeline →" on a failing scenario card. The trajectory timeline opens showing collapsible spans: model calls with token counts, tool calls with input JSON, tool results with output. Click a criterion justification to highlight and scroll to the cited span. The `?highlight=` search param makes the view URL-shareable.

7. **Tweak your agent** — edit the system prompt, re-run the suite.

8. **Compare runs** — on the runs list, check two runs and click **Compare selected runs →**; the compare page shows overall delta, per-scenario deltas (green = improvement, red = regression), and expandable per-criterion rows. Or from the CLI:
   ```bash
   rubricon compare <run_a_id> <run_b_id>
   ```

---

## Architecture

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

## Quickstart

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`pip install uv` or `brew install uv`)
- [pnpm](https://pnpm.io/) (`npm install -g pnpm`)

### Install

```bash
# Python backend
cd backend
uv sync

# Node frontend
cd ..
pnpm i
```

### Run an evaluation

```bash
export ANTHROPIC_API_KEY=sk-ant-...
rubricon run examples/research_agent_suite.yaml
```

### Start the dashboard

```bash
# Terminal 1 — API server (port 8000)
cd backend
rubricon serve

# Terminal 2 — Next.js (port 3000)
cd dashboard
pnpm dev
```

---

## Suite format (preview)

```yaml
# examples/research_agent_suite.yaml
name: Research Agent — Basic Factual
scenarios:
  - id: capital_cities
    input: "What is the capital of France?"
    ground_truth: "Paris"
    rubric:
      criteria:
        - id: correctness
          weight: 0.6
          descriptors:
            1: "Wrong answer"
            3: "Partially correct"
            5: "Correct and concise"
        - id: reasoning_quality
          weight: 0.4
          descriptors:
            1: "No reasoning shown"
            3: "Some reasoning"
            5: "Clear, grounded reasoning"
      pass_threshold: 3.5
```

---

## Project structure

```
rubricon/
├── backend/                    # Python package (rubricon)
│   ├── pyproject.toml          # dependencies, ruff config, pytest config
│   ├── uv.lock
│   ├── examples/
│   │   └── research_agent_suite.yaml   # 3-scenario reference suite
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_loader.py
│   │   ├── test_engine.py
│   │   ├── test_storage.py
│   │   ├── test_judge.py       # judge unit tests + snapshot test
│   │   ├── test_api.py         # FastAPI endpoint tests (9 tests)
│   │   └── snapshots/
│   │       └── judge_prompt_v1.txt   # locked prompt snapshot
│   └── rubricon/
│       ├── __init__.py
│       ├── models.py           # Pydantic domain models
│       ├── loader.py           # YAML suite loader
│       ├── schema.py           # SQLAlchemy ORM (5 tables)
│       ├── storage.py          # async SQLite persist/read
│       ├── agent.py            # Agent protocol + ResearchAgent
│       ├── engine.py           # async run orchestrator + judge phase
│       ├── judge.py            # LLM-as-judge: format/judge/score
│       ├── cli.py              # Typer CLI: run / serve
│       ├── api.py              # FastAPI read-only endpoints
│       └── prompts/
│           ├── __init__.py
│           └── judge_v1.py     # versioned judge prompt constants
├── dashboard/                  # Next.js 14 App Router dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx          # nav bar (Rubricon / Runs / Suites)
│   │   │   ├── page.tsx            # redirects → /runs
│   │   │   ├── compare/
│   │   │   │   └── page.tsx        # run comparison page
│   │   │   ├── runs/
│   │   │   │   ├── page.tsx        # runs list (server shell → RunsListClient)
│   │   │   │   └── [runId]/
│   │   │   │       ├── page.tsx    # run detail + per-scenario score cards
│   │   │   │       └── scenarios/
│   │   │   │           └── [scenarioId]/
│   │   │   │               └── page.tsx  # trajectory timeline + criteria panel
│   │   │   ├── suites/
│   │   │   │   └── page.tsx        # suites list
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── CompareView.tsx           # compare diff table with expand/collapse
│   │   │   ├── RunsListClient.tsx        # runs table with checkboxes + compare button
│   │   │   ├── ScenarioDetailClient.tsx  # two-panel layout; highlight state
│   │   │   └── TrajectoryTimeline.tsx    # collapsible span cards
│   │   └── lib/
│   │       └── api.ts              # typed fetch helpers
│   ├── tailwind.config.ts
│   ├── next.config.js
│   └── package.json
├── .gitignore
├── .pre-commit-config.yaml     # ruff (Python) + prettier (TS/YAML)
├── LICENSE
├── pnpm-workspace.yaml
└── README.md
```

---

## Roadmap

- [x] **M1** — Monorepo scaffold: uv + pnpm workspaces, Typer CLI stub, ruff/prettier pre-commit hooks, MIT license
- [x] **M2** — Pydantic domain models, YAML suite loader, SQLAlchemy 2.0 async schema (5 tables), async SQLite storage layer
- [x] **M3** — Agent adapter protocol, `ResearchAgent` (Anthropic agentic loop + trajectory capture), async run engine with concurrency semaphore, Rich CLI, example suite, test suite
- [x] **M4** — LLM judge with versioned prompts (Claude scores each rubric criterion against trajectory; weighted per-scenario and per-run scores; snapshot tests lock prompt drift)
- [x] **M5** — FastAPI read-only API (`/suites`, `/runs`, `/runs/{id}`, `/runs/{id}/scenarios/{id}/trajectory`) + Next.js dashboard shell (runs list, run detail with score cards, suites list)
- [x] **M6** — Trajectory timeline view: collapsible span cards, criterion→span highlight linking, URL-shareable highlight state via `?highlight=`
- [x] **M7** — Run diff/compare view: `GET /compare` endpoint, `/compare` dashboard page with green/red delta chips, runs-list checkboxes + sticky compare button, `rubricon compare` CLI command
- **Later**: cost/latency dashboards, OpenAI judge, VS Code extension

---

## Contributing

PRs welcome. Run `pre-commit install` after cloning to enable lint hooks.

---

## License

MIT — see [LICENSE](LICENSE).
