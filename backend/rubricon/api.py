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
