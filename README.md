# Rubricon

> Rubric-based evaluation harness for AI agents. Define test scenarios and grading criteria in YAML, point it at your agent, get structured LLM-judged scores plus full trajectory traces — all viewable in a web dashboard.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## What works (M3 — run engine + trajectory capture)

- **Monorepo initialized** with `uv` (Python) and `pnpm` workspaces.
- **Pydantic domain models** — `Suite`, `Scenario`, `Rubric`, `Criterion`, `Trajectory`, `TrajectorySpan`, `ScenarioResult`, `RunRecord`.
- **YAML loader** — `load_suite(path)` validates YAML against Pydantic models with friendly error messages.
- **SQLAlchemy 2.0 async ORM** — five tables: `suites`, `runs`, `scenario_results`, `trajectory_spans`, `scores` (schema-only for M4).
- **Async storage layer** — `persist_run` upserts suite + inserts run/results/spans in one transaction; `get_run` retrieves full `RunRecord`.
- **Agent adapter protocol** + `ResearchAgent` — drives a real Anthropic agentic loop with a stubbed `web_search` tool; captures every model call, tool call, tool result, and final output as `TrajectorySpan` objects.
- **Run engine** — `execute_run` runs all scenarios concurrently behind an `asyncio.Semaphore`; one failure never aborts the rest.
- **CLI** — `rubricon run <suite.yaml>` streams a Rich live progress table; prints run ID and pass/fail summary when complete.
- **Example suite** — `backend/examples/research_agent_suite.yaml` (3 scenarios, 2 rubric criteria).
- **Test suite** — `tests/test_models.py`, `test_loader.py`, `test_engine.py`, `test_storage.py`.

LLM judge scores (`M4`), FastAPI server (`M5`), and Next.js dashboard (`M6+`) are not yet implemented.

---

## Why this exists

Agent teams keep rebuilding the same brittle eval loop: a bag of prompts, ad-hoc assertions, and `print()` statements. There is no shared mental model for *what "good" looks like* per scenario. Rubricon makes that explicit: every test case carries a **rubric** — weighted criteria with 1–5 descriptors — and an LLM judge scores each criterion against the agent's full **trajectory**, not just the final answer.

This catches the failure mode every agent developer has hit: right answer, wrong reasoning; or right reasoning, hallucinated tool call.

---

## Demo flow

Steps 1–3 work today. Steps 4–8 require M5/M6 (FastAPI server and Next.js dashboard — not yet implemented).

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

4. *(M5)* **Open the dashboard**
   ```bash
   rubricon serve
   # → http://localhost:3000
   ```

5. *(M6)* **Review results** — click the latest run, see overall score 3.6/5, two failing scenarios highlighted in red.

6. *(M6)* **Inspect a failure** — click a failing scenario to open the trajectory timeline. Collapsible spans show the agent called `web_search` with a malformed query; the judge's justification quotes that exact span.

7. **Tweak your agent** — edit the system prompt, re-run the suite.

8. *(M6)* **Compare runs** — hit **Compare** in the dashboard to diff two runs side-by-side: which scenarios moved, which criteria moved, regressions flagged in red.

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
rubricon serve   # not yet implemented — M5
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
│   │   └── test_storage.py
│   └── rubricon/
│       ├── __init__.py
│       ├── models.py           # Pydantic domain models
│       ├── loader.py           # YAML suite loader
│       ├── schema.py           # SQLAlchemy ORM (5 tables)
│       ├── storage.py          # async SQLite persist/read
│       ├── agent.py            # Agent protocol + ResearchAgent
│       ├── engine.py           # async run orchestrator
│       └── cli.py              # Typer CLI: run / serve
├── dashboard/                  # Next.js 14 App Router scaffold
│   ├── src/app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
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
- [ ] **M4** — LLM judge with versioned prompts (Claude scores each rubric criterion against trajectory)
- [ ] **M5** — FastAPI read-only server
- [ ] **M6** — Next.js dashboard (suite list → run detail → trajectory → diff)
- **Later**: cost/latency dashboards, OpenAI judge, VS Code extension

---

## Contributing

PRs welcome. Run `pre-commit install` after cloning to enable lint hooks.

---

## License

MIT — see [LICENSE](LICENSE).
