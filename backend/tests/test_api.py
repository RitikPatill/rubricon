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


# ---------------------------------------------------------------------------
# Compare endpoint tests
# ---------------------------------------------------------------------------


def _make_run_with_score(run_id: str, score: int, weighted: float) -> RunRecord:
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
        status="pass" if weighted >= 3.0 else "fail",
        trajectory=trajectory,
        started_at=NOW,
        finished_at=NOW,
        scores=[
            CriterionScore(
                criterion_name="correctness",
                score=score,
                justification="ok",
                passed=score >= 3,
                prompt_version="v1",
            )
        ],
        weighted_score=weighted,
    )
    return RunRecord(
        id=run_id,
        suite_name="api_test_suite",
        started_at=NOW,
        finished_at=NOW,
        scenario_results=[sr],
        overall_score=weighted,
    )


async def test_compare_two_runs(client):
    c, db = client
    engine = await get_engine(db)
    suite = _make_suite()
    run_a = _make_run_with_score("cmp_run_a", score=2, weighted=2.0)
    run_b = _make_run_with_score("cmp_run_b", score=4, weighted=4.0)
    await persist_run(engine, suite, run_a)
    await persist_run(engine, suite, run_b)
    await engine.dispose()

    resp = await c.get("/compare?run_a=cmp_run_a&run_b=cmp_run_b")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_a"]["id"] == "cmp_run_a"
    assert data["run_b"]["id"] == "cmp_run_b"
    assert abs(data["overall_delta"] - 2.0) < 0.001
    assert len(data["scenarios"]) == 1
    scenario = data["scenarios"][0]
    assert scenario["scenario_id"] == "s1"
    assert abs(scenario["delta"] - 2.0) < 0.001
    assert len(scenario["criteria"]) == 1
    crit = scenario["criteria"][0]
    assert crit["criterion_name"] == "correctness"
    assert abs(crit["delta"] - 2.0) < 0.001


async def test_compare_missing_run(client):
    c, _ = client
    resp = await c.get("/compare?run_a=nonexistent_x&run_b=nonexistent_y")
    assert resp.status_code == 404


async def test_compare_mismatched_scenarios(client):
    """Run A has scenario s1, run B has scenario s2 only; both should appear."""
    c, db = client
    engine = await get_engine(db)

    suite_a = Suite(
        name="suite_mismatch_a",
        description="d",
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
    suite_b = Suite(
        name="suite_mismatch_b",
        description="d",
        scenarios=[Scenario(id="s2", description="d", input="in2")],
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

    def _make_traj() -> Trajectory:
        span = TrajectorySpan(
            id=uuid.uuid4().hex,
            type=SpanType.FINAL_OUTPUT,
            started_at=NOW,
            ended_at=NOW,
            data={"text": "hi"},
        )
        return Trajectory(spans=[span], final_output="done")

    run_a = RunRecord(
        id="mismatch_run_a",
        suite_name="suite_mismatch_a",
        started_at=NOW,
        finished_at=NOW,
        scenario_results=[
            ScenarioResult(
                scenario_id="s1",
                status="pass",
                trajectory=_make_traj(),
                started_at=NOW,
                finished_at=NOW,
                scores=[CriterionScore(criterion_name="correctness", score=4, justification="ok", passed=True, prompt_version="v1")],
                weighted_score=4.0,
            )
        ],
        overall_score=4.0,
    )
    run_b = RunRecord(
        id="mismatch_run_b",
        suite_name="suite_mismatch_b",
        started_at=NOW,
        finished_at=NOW,
        scenario_results=[
            ScenarioResult(
                scenario_id="s2",
                status="pass",
                trajectory=_make_traj(),
                started_at=NOW,
                finished_at=NOW,
                scores=[CriterionScore(criterion_name="correctness", score=3, justification="ok", passed=True, prompt_version="v1")],
                weighted_score=3.0,
            )
        ],
        overall_score=3.0,
    )
    await persist_run(engine, suite_a, run_a)
    await persist_run(engine, suite_b, run_b)
    await engine.dispose()

    resp = await c.get("/compare?run_a=mismatch_run_a&run_b=mismatch_run_b")
    assert resp.status_code == 200
    data = resp.json()
    scenario_ids = {s["scenario_id"] for s in data["scenarios"]}
    assert scenario_ids == {"s1", "s2"}

    s1 = next(s for s in data["scenarios"] if s["scenario_id"] == "s1")
    assert s1["status_b"] == "missing"
    assert s1["score_b"] is None

    s2 = next(s for s in data["scenarios"] if s["scenario_id"] == "s2")
    assert s2["status_a"] == "missing"
    assert s2["score_a"] is None
