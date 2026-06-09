# Contributing to Rubricon

## Dev setup

```bash
git clone https://github.com/your-org/rubricon.git
cd rubricon

# Install pre-commit hooks (ruff + prettier)
pre-commit install

# Python backend
cd backend && uv sync && cd ..

# Node frontend
pnpm i
```

---

## Running tests

All tests run without `ANTHROPIC_API_KEY` — the judge and engine tests mock the Anthropic client.

```bash
cd backend
uv run pytest
```

To run a specific test file:

```bash
uv run pytest tests/test_judge.py -v
```

---

## Code style

- **Python** — [ruff](https://docs.astral.sh/ruff/) with line length 100. Enforced by pre-commit.
- **TypeScript / YAML** — [Prettier](https://prettier.io/) with default settings. Enforced by pre-commit.

Both hooks run automatically on `git commit`. To run manually:

```bash
pre-commit run --all-files
```

---

## Adding a new judge prompt version

1. Create `backend/rubricon/prompts/judge_v2.py` modeled on `judge_v1.py`. Export `PROMPT_VERSION = "v2"` and the prompt constants.
2. Update the import in `judge.py` to point at `judge_v2`.
3. Add a new snapshot file at `backend/tests/snapshots/judge_prompt_v2.txt` containing the rendered prompt for the test fixture. The snapshot test in `test_judge.py` will fail until the snapshot matches.
4. Run `uv run pytest tests/test_judge.py` and verify the new snapshot passes.

Historical scores tagged `"v1"` remain unaffected — the version is stored per score row.

---

## Adding a new agent adapter

Implement `async def run(self, input: str) -> Trajectory`. No base class required; `Agent` is a structural `Protocol`.

```python
from rubricon.models import Trajectory, TrajectorySpan, SpanType

class MyAgent:
    async def run(self, input: str) -> Trajectory:
        span = TrajectorySpan(
            id="span-1",
            type=SpanType.FINAL_OUTPUT,
            data={"text": "my answer"},
        )
        return Trajectory(spans=[span], final_output="my answer")
```

Pass it to the engine:

```python
from rubricon.engine import execute_run
result = await execute_run(suite, agent=MyAgent(), db_path="rubricon.db")
```

---

## PR checklist

- [ ] `uv run pytest` passes with no failures
- [ ] If you changed a judge prompt, update `PROMPT_VERSION` and add a new snapshot
- [ ] No new `pyproject.toml` dependencies without prior discussion
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)
