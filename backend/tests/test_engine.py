"""Tests for the run engine."""
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from rubricon.engine import execute_run
from rubricon.models import (
    Criterion,
    Rubric,
    Scenario,
    ScenarioResult,
    SpanType,
    Suite,
    Trajectory,
    TrajectorySpan,
)

NOW = datetime.now(tz=timezone.utc)


def _fixed_trajectory() -> Trajectory:
    span = TrajectorySpan(
        id=uuid.uuid4().hex,  # unique per call to avoid DB UNIQUE constraint failures
        type=SpanType.FINAL_OUTPUT,
        started_at=NOW,
        ended_at=NOW,
        data={"text": "answer"},
    )
    return Trajectory(spans=[span], final_output="answer")


def _make_suite(n: int = 3) -> Suite:
    return Suite(
        name="engine_test_suite",
        description="",
        scenarios=[
            Scenario(id=f"s{i}", description=f"scenario {i}", input=f"input {i}")
            for i in range(n)
        ],
        rubric=Rubric(
            criteria=[
                Criterion(
                    name="correctness",
                    description="d",
                    weight=1.0,
                    descriptors={1: "bad", 5: "good"},
                    pass_threshold=3,
                )
            ]
        ),
    )


async def test_execute_run_produces_correct_results(tmp_path: Path):
    mock_agent = AsyncMock()
    mock_agent.run.side_effect = lambda input: _fixed_trajectory()  # noqa: A006

    suite = _make_suite(3)
    run_id = await execute_run(suite, mock_agent, db_path=str(tmp_path / "test.db"))

    assert isinstance(run_id, str)
    assert len(run_id) == 32  # uuid4 hex
    assert mock_agent.run.call_count == 3


async def test_execute_run_error_scenario_doesnt_abort_others(tmp_path: Path):
    call_count = 0

    async def side_effect(input: str):  # noqa: A002
        nonlocal call_count
        call_count += 1
        if "input 1" in input:
            raise RuntimeError("simulated failure")
        return _fixed_trajectory()

    mock_agent = AsyncMock()
    mock_agent.run.side_effect = side_effect

    suite = _make_suite(3)
    results: list[ScenarioResult] = []

    def cb(r: ScenarioResult) -> None:
        results.append(r)

    await execute_run(
        suite, mock_agent, db_path=str(tmp_path / "err.db"), progress_callback=cb
    )

    assert call_count == 3
    statuses = {r.scenario_id: r.status for r in results}
    assert statuses["s0"] == "pass"
    assert statuses["s1"] == "error"
    assert statuses["s2"] == "pass"
    error_result = next(r for r in results if r.status == "error")
    assert "simulated failure" in (error_result.error or "")


async def test_execute_run_concurrency_respected(tmp_path: Path):
    """Mock tracks concurrent calls and asserts the limit is respected."""
    concurrency = 2
    active = 0
    max_active = 0

    async def side_effect(input: str):  # noqa: A002
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)  # yield so others can start
        active -= 1
        return _fixed_trajectory()

    mock_agent = AsyncMock()
    mock_agent.run.side_effect = side_effect

    suite = _make_suite(6)
    await execute_run(
        suite,
        mock_agent,
        db_path=str(tmp_path / "conc.db"),
        concurrency=concurrency,
    )

    assert max_active <= concurrency


async def test_progress_callback_called_for_each_scenario(tmp_path: Path):
    mock_agent = AsyncMock()
    mock_agent.run.side_effect = lambda input: _fixed_trajectory()  # noqa: A006

    suite = _make_suite(3)
    called: list[ScenarioResult] = []

    await execute_run(
        suite, mock_agent, db_path=str(tmp_path / "cb.db"), progress_callback=called.append
    )

    assert len(called) == 3
    assert all(r.status == "pass" for r in called)
