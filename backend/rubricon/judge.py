from __future__ import annotations

import asyncio

import anthropic

from rubricon.models import Criterion, CriterionScore, Rubric, Trajectory
from rubricon.prompts.judge_v1 import (
    PROMPT_VERSION,
    RECORD_SCORE_TOOL,
    SYSTEM_PROMPT,
    USER_TEMPLATE,
)

JUDGE_MODEL = "claude-haiku-4-5-20251001"

_MAX_TOTAL_CHARS = 3000
_MAX_FIELD_CHARS = 300


def format_trajectory(trajectory: Trajectory) -> str:
    """Serialize trajectory spans to a readable numbered list for the prompt."""
    parts: list[str] = []
    total_chars = 0

    for i, span in enumerate(trajectory.spans, 1):
        header = (
            f"[{i}] {span.type.value.upper()}  id={span.id}"
            f"  started={span.started_at.isoformat()}  ended={span.ended_at.isoformat()}"
        )

        data_lines: list[str] = []
        if span.type.value == "model_call":
            input_str = str(span.data.get("input_messages", ""))[:_MAX_FIELD_CHARS]
            output_str = str(span.data.get("output_content", ""))[:_MAX_FIELD_CHARS]
            data_lines.append(f"    input: {input_str}")
            data_lines.append(f"    output: {output_str}")
        elif span.type.value == "tool_call":
            data_lines.append(f"    tool: {span.data.get('tool_name', '')}")
            data_lines.append(
                f"    input: {str(span.data.get('tool_input', ''))[:_MAX_FIELD_CHARS]}"
            )
        elif span.type.value == "tool_result":
            data_lines.append(
                f"    content: {str(span.data.get('content', ''))[:_MAX_FIELD_CHARS]}"
            )
        elif span.type.value == "final_output":
            data_lines.append(
                f"    text: {str(span.data.get('text', ''))[:_MAX_FIELD_CHARS]}"
            )

        span_text = header + "\n" + "\n".join(data_lines)

        if total_chars + len(span_text) + 1 > _MAX_TOTAL_CHARS:
            parts.append(f"[... truncated after {i - 1} spans — {_MAX_TOTAL_CHARS} char limit ...]")
            break

        parts.append(span_text)
        total_chars += len(span_text) + 1  # +1 for the joining newline

    return "\n".join(parts)


async def judge_criterion(
    client: anthropic.AsyncAnthropic,
    criterion: Criterion,
    trajectory: Trajectory,
    model: str = JUDGE_MODEL,
) -> CriterionScore:
    """Call Claude with tool_use=RECORD_SCORE_TOOL; parse the tool_use block."""
    descriptors_block = "\n".join(
        f"  {score}: {desc}" for score, desc in sorted(criterion.descriptors.items())
    )
    trajectory_text = format_trajectory(trajectory)

    user_message = USER_TEMPLATE.format(
        criterion_name=criterion.name,
        criterion_description=criterion.description,
        descriptors_block=descriptors_block,
        trajectory_text=trajectory_text,
    )

    response = await client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[RECORD_SCORE_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_message}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_score":
            inp = block.input
            score = inp["score"]
            return CriterionScore(
                criterion_name=criterion.name,
                score=score,
                justification=inp["justification"],
                cited_span_id=inp.get("cited_span_id"),
                passed=score >= criterion.pass_threshold,
                prompt_version=PROMPT_VERSION,
            )

    raise RuntimeError("judge did not call record_score")


async def judge_scenario(
    client: anthropic.AsyncAnthropic,
    rubric: Rubric,
    scenario_id: str,
    trajectory: Trajectory,
    model: str = JUDGE_MODEL,
) -> list[CriterionScore]:
    """Judge every criterion concurrently; return all CriterionScore objects."""

    async def _safe_judge(criterion: Criterion) -> CriterionScore:
        try:
            return await judge_criterion(client, criterion, trajectory, model=model)
        except Exception as exc:  # noqa: BLE001
            return CriterionScore(
                criterion_name=criterion.name,
                score=0,
                justification=f"[judge error: {exc}]",
                cited_span_id=None,
                passed=False,
                prompt_version=PROMPT_VERSION,
            )

    results = await asyncio.gather(*[_safe_judge(c) for c in rubric.criteria])
    return list(results)


def compute_weighted_score(criterion_scores: list[CriterionScore], rubric: Rubric) -> float:
    """Weighted average: sum(score * weight) / sum(weight). Returns 0.0 on empty."""
    if not criterion_scores:
        return 0.0

    weight_by_name = {c.name: c.weight for c in rubric.criteria}

    total_weight = 0.0
    weighted_sum = 0.0
    for cs in criterion_scores:
        w = weight_by_name.get(cs.criterion_name, 1.0)
        weighted_sum += cs.score * w
        total_weight += w

    if total_weight == 0.0:
        return 0.0

    return weighted_sum / total_weight
