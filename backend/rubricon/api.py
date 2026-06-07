from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from rubricon.storage import get_engine, get_run, list_runs, list_suites


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class SuiteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    created_at: str


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    suite_id: str
    suite_name: str
    started_at: str
    finished_at: str | None
    status: str
    overall_score: float | None


class CriterionScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    criterion_name: str
    score: int
    justification: str
    cited_span_id: str | None
    passed: bool


class ScenarioSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_id: str
    status: str
    weighted_score: float | None
    scores: list[CriterionScoreOut]


class RunDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    suite_name: str
    started_at: str
    finished_at: str | None
    overall_score: float | None
    scenario_results: list[ScenarioSummary]


class SpanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    started_at: str
    ended_at: str
    data: dict[str, Any]


class TrajectoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    spans: list[SpanOut]
    final_output: str | None


class CriterionDiff(BaseModel):
    criterion_name: str
    score_a: float | None
    score_b: float | None
    delta: float | None
    passed_a: bool | None
    passed_b: bool | None


class ScenarioDiff(BaseModel):
    scenario_id: str
    score_a: float | None
    score_b: float | None
    delta: float | None
    status_a: str
    status_b: str
    criteria: list[CriterionDiff]


class RunCompareResult(BaseModel):
    run_a: RunSummary
    run_b: RunSummary
    overall_delta: float | None
    scenarios: list[ScenarioDiff]


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(db_path: str = "rubricon.db") -> FastAPI:
    _state: dict[str, Any] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[type-arg]
        _state["engine"] = await get_engine(db_path)
        yield
        await _state["engine"].dispose()

    app = FastAPI(title="Rubricon API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/suites", response_model=list[SuiteSummary])
    async def get_suites() -> list[dict]:
        return await list_suites(_state["engine"])

    @app.get("/runs", response_model=list[RunSummary])
    async def get_runs(suite_id: str | None = None) -> list[dict]:
        return await list_runs(_state["engine"], suite_id=suite_id)

    @app.get("/runs/{run_id}", response_model=RunDetail)
    async def get_run_detail(run_id: str) -> RunDetail:
        record = await get_run(_state["engine"], run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return RunDetail(
            id=record.id,
            suite_name=record.suite_name,
            started_at=record.started_at.isoformat(),
            finished_at=record.finished_at.isoformat() if record.finished_at else None,
            overall_score=record.overall_score,
            scenario_results=[
                ScenarioSummary(
                    scenario_id=sr.scenario_id,
                    status=sr.status,
                    weighted_score=sr.weighted_score,
                    scores=[
                        CriterionScoreOut(
                            criterion_name=cs.criterion_name,
                            score=cs.score,
                            justification=cs.justification,
                            cited_span_id=cs.cited_span_id,
                            passed=cs.passed,
                        )
                        for cs in sr.scores
                    ],
                )
                for sr in record.scenario_results
            ],
        )

    @app.get("/compare", response_model=RunCompareResult)
    async def compare_runs(run_a: str, run_b: str) -> RunCompareResult:
        record_a = await get_run(_state["engine"], run_a)
        record_b = await get_run(_state["engine"], run_b)
        if record_a is None or record_b is None:
            raise HTTPException(status_code=404, detail="One or both runs not found")

        runs_map = await list_runs(_state["engine"])
        runs_by_id = {r["id"]: r for r in runs_map}

        def _run_summary(record_id: str) -> RunSummary:
            r = runs_by_id[record_id]
            return RunSummary(
                id=r["id"],
                suite_id=r["suite_id"],
                suite_name=r["suite_name"],
                started_at=r["started_at"],
                finished_at=r["finished_at"],
                status=r["status"],
                overall_score=r["overall_score"],
            )

        summary_a = _run_summary(run_a)
        summary_b = _run_summary(run_b)

        # Build per-scenario index for each run
        scenarios_a = {sr.scenario_id: sr for sr in record_a.scenario_results}
        scenarios_b = {sr.scenario_id: sr for sr in record_b.scenario_results}
        all_scenario_ids = sorted(set(scenarios_a) | set(scenarios_b))

        scenario_diffs: list[ScenarioDiff] = []
        for sid in all_scenario_ids:
            sr_a = scenarios_a.get(sid)
            sr_b = scenarios_b.get(sid)

            score_a = sr_a.weighted_score if sr_a else None
            score_b = sr_b.weighted_score if sr_b else None
            delta = (score_b - score_a) if (score_a is not None and score_b is not None) else None
            status_a = sr_a.status if sr_a else "missing"
            status_b = sr_b.status if sr_b else "missing"

            # Build per-criterion index
            criteria_a = {cs.criterion_name: cs for cs in sr_a.scores} if sr_a else {}
            criteria_b = {cs.criterion_name: cs for cs in sr_b.scores} if sr_b else {}
            all_criteria = sorted(set(criteria_a) | set(criteria_b))

            criterion_diffs: list[CriterionDiff] = []
            for cname in all_criteria:
                cs_a = criteria_a.get(cname)
                cs_b = criteria_b.get(cname)
                c_score_a = float(cs_a.score) if cs_a else None
                c_score_b = float(cs_b.score) if cs_b else None
                c_delta = (c_score_b - c_score_a) if (c_score_a is not None and c_score_b is not None) else None
                criterion_diffs.append(CriterionDiff(
                    criterion_name=cname,
                    score_a=c_score_a,
                    score_b=c_score_b,
                    delta=c_delta,
                    passed_a=cs_a.passed if cs_a else None,
                    passed_b=cs_b.passed if cs_b else None,
                ))

            scenario_diffs.append(ScenarioDiff(
                scenario_id=sid,
                score_a=score_a,
                score_b=score_b,
                delta=delta,
                status_a=status_a,
                status_b=status_b,
                criteria=criterion_diffs,
            ))

        overall_a = summary_a.overall_score
        overall_b = summary_b.overall_score
        overall_delta = (overall_b - overall_a) if (overall_a is not None and overall_b is not None) else None

        return RunCompareResult(
            run_a=summary_a,
            run_b=summary_b,
            overall_delta=overall_delta,
            scenarios=scenario_diffs,
        )

    @app.get(
        "/runs/{run_id}/scenarios/{scenario_id}/trajectory",
        response_model=TrajectoryOut,
    )
    async def get_trajectory(run_id: str, scenario_id: str) -> TrajectoryOut:
        record = await get_run(_state["engine"], run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Run not found")
        for sr in record.scenario_results:
            if sr.scenario_id == scenario_id:
                return TrajectoryOut(
                    spans=[
                        SpanOut(
                            id=span.id,
                            type=span.type.value,
                            started_at=span.started_at.isoformat(),
                            ended_at=span.ended_at.isoformat(),
                            data=span.data,
                        )
                        for span in sr.trajectory.spans
                    ],
                    final_output=sr.trajectory.final_output,
                )
        raise HTTPException(status_code=404, detail="Scenario not found in run")

    return app
