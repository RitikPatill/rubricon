"""Tests for FastAPI read endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rubricon.api import create_app
from rubricon.models import (
    Criterion,
    CriterionScore,
    Rubric,
    RunRecord,
    Scenario,
    ScenarioResult,
    SpanType,
    Suite,
    Trajectory,
    TrajectorySpan,
)
from rubricon.storage import get_engine, persist_run

NOW = datetime.now(tz=timezone.utc)


def _make_suite(name: str = "api_test_suite") -> Suite:
    return Suite(
        name=name,
        description="API test suite description",
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


def _make_run(run_id: str = "run001") -> RunRecord:
    span = TrajectorySpan(
        id=uuid.uuid4().hex,
        type=SpanType.FINAL_OUTPUT,
        started_at=NOW,
        ended_at=NOW,
        data={"text": "hello"},
    )
    trajectory = Trajectory(spans=[span], final_output="done")
    sr = ScenarioResult(
        scenario_id="s1",
        status="pass",
        trajectory=trajectory,
        started_at=NOW,
        finished_at=NOW,
        scores=[
            CriterionScore(
                criterion_name="correctness",
                score=4,
                justification="Good answer",
                passed=True,
                prompt_version="v1",
            )
        ],
        weighted_score=4.0,
    )
    return RunRecord(
        id=run_id,
        suite_name="api_test_suite",
        started_at=NOW,
        finished_at=NOW,
        scenario_results=[sr],
        overall_score=4.0,
    )


@pytest.fixture
async def client(tmp_path: Path):
    db = str(tmp_path / "test.db")
    app = create_app(db_path=db)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c, db


async def test_get_suites_empty(client):
    c, _ = client
    resp = await c.get("/suites")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_suites_after_seed(client):
    c, db = client
    engine = await get_engine(db)
    suite = _make_suite()
    run = _make_run()
    await persist_run(engine, suite, run)
    await engine.dispose()

    resp = await c.get("/suites")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "api_test_suite"
    assert data[0]["description"] == "API test suite description"


async def test_get_runs_empty(client):
    c, _ = client
    resp = await c.get("/runs")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_runs_after_seed(client):
    c, db = client
    engine = await get_engine(db)
    suite = _make_suite()
    run = _make_run(run_id="run_for_list")
    await persist_run(engine, suite, run)
    await engine.dispose()

    resp = await c.get("/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "run_for_list"
    assert data[0]["suite_name"] == "api_test_suite"
    assert data[0]["overall_score"] == 4.0


async def test_get_runs_bad_suite_id(client):
    c, db = client
    engine = await get_engine(db)
    suite = _make_suite()
    run = _make_run()
    await persist_run(engine, suite, run)
    await engine.dispose()

    resp = await c.get("/runs?suite_id=nonexistent")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_run_detail(client):
    c, db = client
    engine = await get_engine(db)
    suite = _make_suite()
    run = _make_run(run_id="run_detail")
    await persist_run(engine, suite, run)
    await engine.dispose()

    resp = await c.get("/runs/run_detail")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "run_detail"
    assert data["suite_name"] == "api_test_suite"
    assert data["overall_score"] == 4.0
    assert len(data["scenario_results"]) == 1
    sr = data["scenario_results"][0]
    assert sr["scenario_id"] == "s1"
    assert sr["status"] == "pass"
    assert len(sr["scores"]) == 1
    assert sr["scores"][0]["criterion_name"] == "correctness"
    assert sr["scores"][0]["score"] == 4
    assert sr["scores"][0]["passed"] is True


async def test_get_run_detail_not_found(client):
    c, _ = client
    resp = await c.get("/runs/nonexistent")
    assert resp.status_code == 404


async def test_get_trajectory(client):
    c, db = client
    engine = await get_engine(db)
    suite = _make_suite()
    run = _make_run(run_id="run_traj")
    await persist_run(engine, suite, run)
    await engine.dispose()

    resp = await c.get("/runs/run_traj/scenarios/s1/trajectory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_output"] == "done"
    assert len(data["spans"]) == 1
    assert data["spans"][0]["type"] == "final_output"


async def test_get_trajectory_bad_scenario(client):
    c, db = client
    engine = await get_engine(db)
    suite = _make_suite()
    run = _make_run(run_id="run_traj2")
    await persist_run(engine, suite, run)
    await engine.dispose()

    resp = await c.get("/runs/run_traj2/scenarios/bad_scenario/trajectory")
    assert resp.status_code == 404
