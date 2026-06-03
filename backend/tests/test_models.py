"""Tests for Pydantic domain models."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

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

NOW = datetime.now(tz=timezone.utc)


def _make_span(span_type: SpanType) -> TrajectorySpan:
    return TrajectorySpan(
        id="abc123",
        type=span_type,
        started_at=NOW,
        ended_at=NOW,
        data={"key": "value"},
    )


def _make_suite() -> Suite:
    return Suite(
        name="test_suite",
        description="desc",
        scenarios=[
            Scenario(id="s1", description="d1", input="input1"),
        ],
        rubric=Rubric(
            criteria=[
                Criterion(
                    name="correctness",
                    description="Is it correct?",
                    weight=2.0,
                    descriptors={1: "bad", 5: "great"},
                    pass_threshold=3,
                )
            ]
        ),
    )


def test_suite_round_trip():
    suite = _make_suite()
    dumped = suite.model_dump()
    reloaded = Suite.model_validate(dumped)
    assert reloaded.name == suite.name
    assert reloaded.rubric.criteria[0].name == "correctness"


def test_criterion_rejects_non_positive_weight():
    with pytest.raises(ValidationError):
        Criterion(
            name="c",
            description="d",
            weight=0.0,
            descriptors={1: "bad"},
            pass_threshold=3,
        )

    with pytest.raises(ValidationError):
        Criterion(
            name="c",
            description="d",
            weight=-1.0,
            descriptors={1: "bad"},
            pass_threshold=3,
        )


def test_trajectory_serializes_all_span_types():
    spans = [_make_span(st) for st in SpanType]
    trajectory = Trajectory(spans=spans, final_output="done")
    dumped = trajectory.model_dump()
    reloaded = Trajectory.model_validate(dumped)
    assert len(reloaded.spans) == len(SpanType)
    for span, st in zip(reloaded.spans, SpanType):
        assert span.type == st


def test_scenario_result_optional_fields():
    sr = ScenarioResult(
        scenario_id="s1",
        status="error",
        trajectory=Trajectory(),
        error="boom",
    )
    assert sr.error == "boom"
    assert sr.trajectory.spans == []
