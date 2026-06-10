# Rubricon


> **Video walkthrough:** https://youtu.be/NmtgSvUIuxs
> **60-second overview:** https://youtu.be/HJZUurVyh1w

> Define YAML rubrics, run your agent through test scenarios, get LLM-judged per-criterion scores with full trajectory traces in a web dashboard.

![demo](docs/demo.gif)

## What it is

Rubricon is a local evaluation harness for AI agents. You write a YAML file describing test scenarios and a shared rubric — weighted criteria, each with 1–5 descriptors and a pass threshold. Point it at any agent that returns a `Trajectory`, run one command, and Claude judges each criterion against the agent's full span log: model calls, tool calls, tool results, and final output.

The rubric is first-class, not an afterthought. Every eval run produces structured per-criterion scores with judge justifications that cite specific trajectory spans. A comparison view diffs two runs side-by-side so regressions are immediately obvious — right answer with a hallucinated tool call shows up; right reasoning with a malformed query shows up.

## Quickstart

```bash
git clone https://github.com/RitikPatill/rubricon.git
cd rubricon

# install backend and dashboard deps
cd backend && uv sync && cd ..
pnpm i

# set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# run the bundled 8-scenario example suite (streams per-criterion scores live)
cd backend
uv run rubricon run examples/research_agent_suite.yaml

# start the API server and dashboard (two terminals)
uv run rubricon serve          # → http://localhost:8000
cd ../dashboard && pnpm dev   # → http://localhost:3000
```

## Usage

After `rubricon run`, open the dashboard at `localhost:3000`. The runs list shows each run's overall weighted score. Click a run to see per-scenario score cards; failing scenarios are highlighted. Click into a scenario to see the trajectory timeline — collapsible spans for each model call, tool call, and tool result, with the judge's score, justification, and cited span ID for each criterion.

To compare two runs, check both in the runs list and click **Compare**. The diff page shows per-scenario and per-criterion deltas: green for improvements, red for regressions. The CLI equivalent is `rubricon compare <run_id_a> <run_id_b>`.

To plug in a custom agent, implement one async method — no base class, no registration:

```python
from rubricon.models import Trajectory, TrajectorySpan, SpanType

class MyAgent:
    async def run(self, input: str) -> Trajectory:
        span = TrajectorySpan(id="s1", type=SpanType.FINAL_OUTPUT,
                              data={"text": "my answer"})
        return Trajectory(spans=[span], final_output="my answer")
```

Pass it directly to the engine: `await execute_run(suite, agent=MyAgent(), db_path="rubricon.db")`.

## Architecture

```
suite.yaml ──► Suite Loader (pydantic)
                      │
                      ▼
Agent adapter ◄── Run Engine (asyncio) ──► SQLite storage
  .run()             │ trajectory + rubric        ▲
                     ▼                            │
               LLM Judge (Claude) ── scores ──────┘
                                                  │
Next.js UI ◄──► FastAPI server (read-only) ◄──────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full component breakdown.

## Project structure

```
rubricon/
├── backend/            # Python package: CLI, run engine, LLM judge, FastAPI server
│   ├── rubricon/       # core modules (models, loader, engine, judge, storage, api, cli)
│   ├── examples/       # reference suite YAML (8 scenarios, 3 criteria)
│   └── tests/          # pytest suite; snapshot tests lock judge prompt drift
├── dashboard/          # Next.js 14 App Router + Tailwind
│   └── src/app/        # runs list, run detail, trajectory timeline, compare diff
├── docs/               # demo gif and screenshots
└── record_demo.sh      # ScreenToGif automation script for demo recording
```

## Roadmap

- [ ] OpenAI judge swap — `JUDGE_MODEL` is a single constant in `judge.py`; GPT-4o support is a one-function edit
- [ ] Cost/latency panel — token counts are already stored per span; needs one new API endpoint and a stats card on the run detail page
- [ ] CI integration — `rubricon run` exits non-zero on score-threshold failure; a GitHub Actions workflow turns it into a regression gate with a pass/fail badge
- [ ] Dataset import — `rubricon import dataset.jsonl` to auto-generate suite YAML from existing eval datasets, removing the friction of writing scenarios by hand

## License

MIT — see [LICENSE](LICENSE).

---

Built autonomously by [autodev](https://github.com/RitikPatill/autodev),
a multi-agent orchestrator I designed. Each commit in this repo was
authored by me; the implementation work was performed by Sonnet under
the orchestrator's control. Read the orchestrator's README to see how.
