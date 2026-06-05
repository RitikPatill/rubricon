from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, field_validator


class SpanType(str, Enum):
    MODEL_CALL = "model_call"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FINAL_OUTPUT = "final_output"


class TrajectorySpan(BaseModel):
    id: str
    type: SpanType
    started_at: datetime
    ended_at: datetime
    data: dict[str, Any]


class Trajectory(BaseModel):
    spans: list[TrajectorySpan] = []
    final_output: str | None = None


class Criterion(BaseModel):
    name: str
    description: str
    weight: float = 1.0
    descriptors: dict[int, str]
    pass_threshold: int = 3

    @field_validator("weight")
    @classmethod
    def weight_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("weight must be > 0")
        return v


class Rubric(BaseModel):
    criteria: list[Criterion]


class Scenario(BaseModel):
    id: str
    description: str
    input: str
    ground_truth: str | None = None
    setup: dict[str, Any] | None = None


class Suite(BaseModel):
    name: str
    description: str = ""
    scenarios: list[Scenario]
    rubric: Rubric


class CriterionScore(BaseModel):
    criterion_name: str
    score: int  # 1–5 (0 on judge error)
    justification: str
    cited_span_id: str | None = None
    passed: bool  # score >= criterion.pass_threshold
    prompt_version: str = "v1"


class ScenarioScore(BaseModel):
    scenario_id: str
    criterion_scores: list[CriterionScore]
    weighted_score: float  # output of compute_weighted_score
    passed: bool  # all criteria passed


class ScenarioResult(BaseModel):
    scenario_id: str
    status: str  # "pass" | "error"
    trajectory: Trajectory
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    scores: list[CriterionScore] = []
    weighted_score: float | None = None


class RunRecord(BaseModel):
    id: str
    suite_name: str
    started_at: datetime
    finished_at: datetime | None = None
    scenario_results: list[ScenarioResult] = []
    overall_score: float | None = None  # mean of scenario weighted_scores
