# Rubricon — Roadmap

## Done

| Milestone | What it added |
|-----------|---------------|
| M1 | Monorepo scaffold: uv + pnpm workspaces, Typer CLI stub, ruff/prettier pre-commit hooks, MIT license |
| M2 | Pydantic domain models, YAML suite loader, SQLAlchemy 2.0 async schema (5 tables), async SQLite storage layer |
| M3 | Agent adapter protocol, `ResearchAgent` (Anthropic agentic loop + trajectory capture), async run engine with concurrency semaphore, Rich CLI, example suite, test suite |
| M4 | LLM judge with versioned prompts — Claude scores each rubric criterion against trajectory; weighted per-scenario and per-run scores; snapshot tests lock prompt drift |
| M5 | FastAPI read-only API (`/suites`, `/runs`, `/runs/{id}`, `/runs/{id}/scenarios/{id}/trajectory`) + Next.js dashboard shell (runs list, run detail with score cards, suites list) |
| M6 | Trajectory timeline: collapsible span cards, criterion→span highlight linking, URL-shareable highlight state via `?highlight=` |
| M7 | Run diff/compare: `GET /compare` endpoint, `/compare` dashboard page with green/red delta chips, runs-list checkboxes + sticky compare button, `rubricon compare` CLI command |
| M8 | Demo polish: 8-scenario example suite (3 criteria, ~5 pass / ~3 fail), placeholder screenshots in `docs/`, `record_demo.sh` automation script |
| M9 | Portfolio polish: rewritten README, ARCHITECTURE.md, ROADMAP.md, CONTRIBUTING.md |

---

## Near-term

**OpenAI judge swap**
The judge model is a single constant — `JUDGE_MODEL` in `judge.py`. Swapping to GPT-4o requires changing that constant and implementing the same `record_score` tool call pattern against the OpenAI chat completions API. No schema changes, no prompt changes. The design decision is already made; it's a one-function edit.

**Cost/latency panel**
Token counts are already stored in `TrajectorySpan.data["usage"]` for every `MODEL_CALL` span. Aggregating cost and latency per run requires a new read query in `storage.py`, one new `/runs/{id}/stats` API endpoint, and a stats card on the run detail page. No schema migrations needed.

**CI integration**
`rubricon run` already exits non-zero when a run's `overall_score` is below a configurable threshold (pass/fail is tracked per criterion). A GitHub Actions workflow that runs the example suite and checks the exit code turns Rubricon into a regression gate. The badge would show pass/fail against the latest commit.

**Dataset import**
Point `rubricon import dataset.jsonl` at a file of `{"input": "...", "ground_truth": "..."}` rows and it auto-generates a `Suite` YAML. This removes the friction of writing scenario YAML by hand for teams with existing eval datasets.

---

## Explicitly out of scope

- **Auth / multi-tenant** — Rubricon is a local tool. The SQLite file is the source of truth. Multi-user access is not a goal.
- **Hosted version** — No cloud deployment, no SaaS, no data leaving the machine.
- **Fine-tuning / RLHF** — Rubricon scores agents; it does not train them.
- **Non-SQLite databases** — PostgreSQL support would require an async migration layer and complicates the single-file local story.
