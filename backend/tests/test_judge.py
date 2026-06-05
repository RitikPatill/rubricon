from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rubricon.judge import (
    JUDGE_MODEL,
    compute_weighted_score,
    format_trajectory,
    judge_criterion,
    judge_scenario,
)
from rubricon.models import (
    Criterion,
    CriterionScore,
    Rubric,
    SpanType,
    Trajectory,
    TrajectorySpan,
)
from rubricon.prompts.judge_v1 import USER_TEMPLATE

SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "judge_prompt_v1.txt"

_TS = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
_TS2 = datetime(2024, 1, 1, 12, 0, 1, tzinfo=timezone.utc)


def _make_span(span_id: str, span_type: SpanType, data: dict) -> TrajectorySpan:
    return TrajectorySpan(
        id=span_id,
        type=span_type,
        started_at=_TS,
        ended_at=_TS2,
        data=data,
    )


def _make_criterion(name: str = "accuracy", weight: float = 1.0, threshold: int = 3) -> Criterion:
    return Criterion(
        name=name,
        description="How accurate is the agent's final answer?",
        weight=weight,
        descriptors={
            1: "Completely wrong",
            2: "Mostly wrong",
            3: "Partially correct",
            4: "Mostly correct",
            5: "Completely correct",
        },
        pass_threshold=threshold,
    )


# ---------------------------------------------------------------------------
# test_format_trajectory_basic
# ---------------------------------------------------------------------------

def test_format_trajectory_basic():
    spans = [
        _make_span("span1", SpanType.MODEL_CALL, {
            "input_messages": [{"role": "user", "content": "hello"}],
            "output_content": [{"type": "text", "text": "world"}],
        }),
        _make_span("span2", SpanType.TOOL_CALL, {
            "tool_name": "web_search",
            "tool_input": {"query": "test query"},
        }),
        _make_span("span3", SpanType.FINAL_OUTPUT, {
            "text": "The answer is 42.",
        }),
    ]
    trajectory = Trajectory(spans=spans, final_output="The answer is 42.")

    result = format_trajectory(trajectory)

    assert "MODEL_CALL" in result
    assert "TOOL_CALL" in result
    assert "FINAL_OUTPUT" in result
    assert "span1" in result
    assert "span2" in result
    assert "span3" in result
    assert len(result) <= 3000


# ---------------------------------------------------------------------------
# test_format_trajectory_truncation
# ---------------------------------------------------------------------------

def test_format_trajectory_truncation():
    big_data = "x" * 5000
    spans = [
        _make_span(f"span{i}", SpanType.MODEL_CALL, {
            "input_messages": big_data,
            "output_content": big_data,
        })
        for i in range(10)
    ]
    trajectory = Trajectory(spans=spans)

    result = format_trajectory(trajectory)

    assert len(result) <= 3000


# ---------------------------------------------------------------------------
# test_judge_criterion_mock
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_judge_criterion_mock():
    criterion = _make_criterion(threshold=3)
    trajectory = Trajectory(spans=[
        _make_span("s1", SpanType.FINAL_OUTPUT, {"text": "42"}),
    ])

    # Build a fake tool_use block
    fake_tool_use = MagicMock()
    fake_tool_use.type = "tool_use"
    fake_tool_use.name = "record_score"
    fake_tool_use.input = {"score": 4, "justification": "good", "cited_span_id": None}

    fake_response = MagicMock()
    fake_response.content = [fake_tool_use]

    import anthropic
    client = anthropic.AsyncAnthropic.__new__(anthropic.AsyncAnthropic)
    client.messages = AsyncMock()
    client.messages.create = AsyncMock(return_value=fake_response)

    cs = await judge_criterion(client, criterion, trajectory)

    assert cs.score == 4
    assert cs.passed is True
    assert cs.justification == "good"
    assert cs.cited_span_id is None
    assert cs.prompt_version == "v1"
    assert cs.criterion_name == "accuracy"


# ---------------------------------------------------------------------------
# test_judge_criterion_no_tool_call_raises
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_judge_criterion_no_tool_call_raises():
    criterion = _make_criterion()
    trajectory = Trajectory(spans=[])

    # Response with end_turn and a text block (no tool_use)
    fake_text_block = MagicMock()
    fake_text_block.type = "text"
    fake_text_block.text = "I think the score is 4."

    fake_response = MagicMock()
    fake_response.content = [fake_text_block]

    import anthropic
    client = anthropic.AsyncAnthropic.__new__(anthropic.AsyncAnthropic)
    client.messages = AsyncMock()
    client.messages.create = AsyncMock(return_value=fake_response)

    with pytest.raises(RuntimeError, match="judge did not call record_score"):
        await judge_criterion(client, criterion, trajectory)


# ---------------------------------------------------------------------------
# test_compute_weighted_score
# ---------------------------------------------------------------------------

def test_compute_weighted_score():
    rubric = Rubric(criteria=[
        _make_criterion(name="accuracy", weight=2.0),
        _make_criterion(name="clarity", weight=1.0),
    ])

    criterion_scores = [
        CriterionScore(
            criterion_name="accuracy",
            score=4,
            justification="good",
            passed=True,
        ),
        CriterionScore(
            criterion_name="clarity",
            score=2,
            justification="needs work",
            passed=False,
        ),
    ]

    result = compute_weighted_score(criterion_scores, rubric)

    expected = (4 * 2.0 + 2 * 1.0) / (2.0 + 1.0)
    assert abs(result - expected) < 1e-9


def test_compute_weighted_score_empty():
    rubric = Rubric(criteria=[_make_criterion()])
    assert compute_weighted_score([], rubric) == 0.0


# ---------------------------------------------------------------------------
# test_prompt_snapshot
# ---------------------------------------------------------------------------

def test_prompt_snapshot():
    criterion = _make_criterion()
    trajectory_text = (
        "[1] FINAL_OUTPUT  id=abc123  started=2024-01-01T12:00:00+00:00  ended=2024-01-01T12:00:01+00:00\n"
        "    text: The answer is 42."
    )
    descriptors_block = "\n".join(
        f"  {score}: {desc}"
        for score, desc in sorted(criterion.descriptors.items())
    )

    rendered = USER_TEMPLATE.format(
        criterion_name=criterion.name,
        criterion_description=criterion.description,
        descriptors_block=descriptors_block,
        trajectory_text=trajectory_text,
    )

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SNAPSHOT_PATH.exists():
        SNAPSHOT_PATH.write_text(rendered, encoding="utf-8", newline="\n")
        # First run: snapshot written, test passes
        return

    expected = SNAPSHOT_PATH.read_text(encoding="utf-8")
    assert rendered == expected, (
        "Judge prompt snapshot mismatch — if intentional, delete "
        f"{SNAPSHOT_PATH} and re-run to regenerate."
    )
