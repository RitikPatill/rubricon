# Rubricon

> Rubric-based evaluation harness for AI agents. Define test scenarios and grading criteria in YAML, point it at your agent, get structured LLM-judged scores plus full trajectory traces — all viewable in a web dashboard.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## What works (M1 — scaffold)

- **Monorepo initialized** with `uv` (Python) and `pnpm` workspaces.
- **Python package** `rubricon` installable via `uv sync`; entry point `rubricon` wired through `pyproject.toml`.
- **Typer CLI stub** — `rubricon run <suite>` and `rubricon serve` are registered commands; both print `"not yet implemented"` and exit cleanly.
- **Dependency manifest** declared in `pyproject.toml`: `anthropic`, `fastapi`, `uvicorn`, `pydantic`, `pyyaml`, `typer`, `aiosqlite`, `rich`; dev extras: `ruff`, `pytest`, `pytest-asyncio`, `pre-commit`.
- **Ruff** configured for Python 3.11, line-length 100, E/F/I rule sets.
- **Next.js 14 App Router** scaffold under `dashboard/` with Tailwind CSS and TypeScript.
- **Pre-commit hooks**: `ruff` + `ruff-format` on `backend/`; `prettier` on `dashboard/`.
- **MIT license** and `.gitignore`.

Nothing from M2 onward (models, storage, engine, judge, server, dashboard pages) is implemented yet.

---

## Why this exists

Agent teams keep rebuilding the same brittle eval loop: a bag of prompts, ad-hoc assertions, and `print()` statements. There is no shared mental model for *what "good" looks like* per scenario. Rubricon makes that explicit: every test case carries a **rubric** — weighted criteria with 1–5 descriptors — and an LLM judge scores each criterion against the agent's full **trajectory**, not just the final answer.

This catches the failure mode every agent developer has hit: right answer, wrong reasoning; or right reasoning, hallucinated tool call.

---

## Demo flow (target — not yet functional)

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

3. **Run a suite** — terminal streams 8 scenarios; per-criterion scores print live
   ```bash
   rubricon run examples/research_agent_suite.yaml
   ```

4. **Open the dashboard**
   ```bash
   rubricon serve
   # → http://localhost:3000
   ```

5. **Review results** — click the latest run, see overall score 3.6/5, two failing scenarios highlighted in red.

6. **Inspect a failure** — click a failing scenario to open the trajectory timeline. Collapsible spans show the agent called `web_search` with a malformed query; the judge's justification quotes that exact span.

7. **Tweak your agent** — edit the system prompt, re-run the suite.

8. **Compare runs** — hit **Compare** in the dashboard to diff two runs side-by-side: which scenarios moved, which criteria moved, regressions flagged in red.

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
rubricon serve
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
│   └── rubricon/
│       ├── __init__.py
│       └── cli.py              # typer CLI stub: run / serve (not yet implemented)
│           # planned: models.py, engine.py, judge.py, storage.py, server.py
├── dashboard/                  # Next.js 14 App Router scaffold
│   ├── src/app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   │   # planned: runs/[id]/ (run detail + trajectory view)
│   ├── tailwind.config.ts
│   ├── next.config.js
│   └── package.json
│   # planned: examples/research_agent_suite.yaml
├── .gitignore
├── .pre-commit-config.yaml     # ruff (Python) + prettier (TS/YAML)
├── LICENSE
├── pnpm-workspace.yaml
└── README.md
```

---

## Roadmap

- [x] **M1** — Monorepo scaffold: uv + pnpm workspaces, Typer CLI stub, ruff/prettier pre-commit hooks, MIT license
- [ ] **M2** — Pydantic models: `Suite`, `Scenario`, `Rubric`, `Trajectory`, `Score`
- [ ] **M3** — SQLite schema + storage layer
- [ ] **M4** — Agent adapter protocol + reference research agent
- [ ] **M5** — Run engine (asyncio, concurrency, live streaming)
- [ ] **M6** — LLM judge with versioned prompts
- [ ] **M7** — FastAPI read-only server
- [ ] **M8** — Next.js dashboard (suite list → run detail → trajectory → diff)
- **Later**: cost/latency dashboards, OpenAI judge, VS Code extension

---

## Contributing

PRs welcome. Run `pre-commit install` after cloning to enable lint hooks.

---

## License

MIT — see [LICENSE](LICENSE).
