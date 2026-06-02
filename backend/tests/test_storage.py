"""Tests for async storage layer."""
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from rubricon.models import (
    Criterion,
    Rubric,
    RunRecord,
    Scenario,
    ScenarioResult,
    SpanType,
    Suite,
    Trajectory,
    TrajectorySpan,
)
from rubricon.storage import get_engine, persist_run, get_run

NOW = datetime.now(tz=timezone.utc)


def _make_span(span_id: str | None = None) -> TrajectorySpan:
    return TrajectorySpan(
        id=span_id or uuid.uuid4().hex,
        type=SpanType.FINAL_OUTPUT,
        started_at=NOW,
        ended_at=NOW,
        data={"text": "hello"},
    )


def _make_suite(name: str = "test_suite") -> Suite:
    return Suite(
        name=name,
        description="desc",
        scenarios=[Scenario(id="s1", description="d", input="in")],
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


def _make_run(run_id: str = "run001", suite_name: str = "test_suite") -> RunRecord:
    trajectory = Trajectory(spans=[_make_span()], final_output="done")
    sr = ScenarioResult(
        scenario_id="s1",
        status="pass",
        trajectory=trajectory,
        started_at=NOW,
        finished_at=NOW,
    )
    return RunRecord(
        id=run_id,
        suite_name=suite_name,
        started_at=NOW,
        finished_at=NOW,
        scenario_results=[sr],
    )


async def test_persist_and_get_run_round_trip(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    engine = await get_engine(db_path)
    suite = _make_suite()
    run = _make_run()

    await persist_run(engine, suite, run)
    retrieved = await get_run(engine, run.id)
    await engine.dispose()

    assert retrieved is not None
    assert retrieved.id == run.id
    assert retrieved.suite_name == suite.name
    assert len(retrieved.scenario_results) == 1
    assert retrieved.scenario_results[0].scenario_id == "s1"
    assert retrieved.scenario_results[0].status == "pass"
    assert retrieved.scenario_results[0].trajectory.final_output == "done"


async def test_persist_run_twice_same_suite_no_duplicate(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    engine = await get_engine(db_path)
    suite = _make_suite()

    run1 = _make_run(run_id="run001")
    run2 = _make_run(run_id="run002")

    await persist_run(engine, suite, run1)
    await persist_run(engine, suite, run2)

    # Check suite table has exactly one row for this suite name
    from sqlalchemy import select, func
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from rubricon.schema import SuiteRow

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(func.count()).select_from(SuiteRow).where(SuiteRow.name == suite.name)
        )
        count = result.scalar_one()

    await engine.dispose()
    assert count == 1


async def test_trajectory_spans_total_count(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    engine = await get_engine(db_path)
    suite = _make_suite()

    # Two scenario results, each with 2 spans
    span_a1 = _make_span("spanA1")
    span_a2 = TrajectorySpan(
        id="spanA2",
        type=SpanType.MODEL_CALL,
        started_at=NOW,
        ended_at=NOW,
        data={"model": "claude"},
    )
    span_b1 = _make_span("spanB1")
    span_b2 = TrajectorySpan(
        id="spanB2",
        type=SpanType.TOOL_CALL,
        started_at=NOW,
        ended_at=NOW,
        data={"tool_name": "web_search"},
    )

    run = RunRecord(
        id="run_spans",
        suite_name=suite.name,
        started_at=NOW,
        finished_at=NOW,
        scenario_results=[
            ScenarioResult(
                scenario_id="s1",
                status="pass",
                trajectory=Trajectory(spans=[span_a1, span_a2], final_output="a"),
                started_at=NOW,
                finished_at=NOW,
            ),
            ScenarioResult(
                scenario_id="s2",
                status="pass",
                trajectory=Trajectory(spans=[span_b1, span_b2], final_output="b"),
                started_at=NOW,
                finished_at=NOW,
            ),
        ],
    )

    await persist_run(engine, suite, run)

    from sqlalchemy import select, func
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from rubricon.schema import TrajectorySpanRow

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(select(func.count()).select_from(TrajectorySpanRow))
        count = result.scalar_one()

    await engine.dispose()
    assert count == 4


async def test_get_run_nonexistent_returns_none(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    engine = await get_engine(db_path)
    result = await get_run(engine, "does_not_exist")
    await engine.dispose()
    assert result is None
