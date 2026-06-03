from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

import anthropic

from rubricon.models import SpanType, Trajectory, TrajectorySpan

# ── helpers ────────────────────────────────────────────────────────────────────

_EPOCH = datetime.now(tz=timezone.utc)
_MONO_START = time.monotonic()


def _now() -> datetime:
    """Datetime aligned to monotonic clock, always UTC."""
    delta = time.monotonic() - _MONO_START
    from datetime import timedelta
    return datetime(
        _EPOCH.year, _EPOCH.month, _EPOCH.day,
        _EPOCH.hour, _EPOCH.minute, _EPOCH.second,
        tzinfo=timezone.utc,
    ) + timedelta(seconds=delta)


def _new_span_id() -> str:
    return uuid.uuid4().hex


# ── protocol ───────────────────────────────────────────────────────────────────

@runtime_checkable
class Agent(Protocol):
    async def run(self, input: str) -> Trajectory:
        ...


# ── stub tool ──────────────────────────────────────────────────────────────────

def _web_search(query: str) -> str:
    return f"[stub] no results for: {query}"


_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."},
            },
            "required": ["query"],
        },
    }
]

_SYSTEM = (
    "You are a helpful research assistant. "
    "Use the web_search tool to look up information when needed."
)

_MODEL = "claude-haiku-4-5-20251001"


# ── reference agent ────────────────────────────────────────────────────────────

class ResearchAgent:
    """Reference tool-using agent built on the Anthropic SDK.

    Drives a real agentic loop with a stubbed web_search tool so trajectory
    capture works without extra API keys while still exercising multi-turn
    tool calling.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def run(self, input: str) -> Trajectory:  # noqa: A002
        spans: list[TrajectorySpan] = []
        messages: list[dict] = [{"role": "user", "content": input}]

        while True:
            call_start = _now()
            response = await self._client.messages.create(
                model=_MODEL,
                max_tokens=1024,
                system=_SYSTEM,
                tools=_TOOLS,
                messages=messages,
            )
            call_end = _now()

            spans.append(
                TrajectorySpan(
                    id=_new_span_id(),
                    type=SpanType.MODEL_CALL,
                    started_at=call_start,
                    ended_at=call_end,
                    data={
                        "input_messages": messages,
                        "output_content": [b.model_dump() for b in response.content],
                        "model": response.model,
                        "usage": response.usage.model_dump(),
                    },
                )
            )

            if response.stop_reason == "tool_use":
                # Append assistant turn
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tc_start = _now()
                    spans.append(
                        TrajectorySpan(
                            id=_new_span_id(),
                            type=SpanType.TOOL_CALL,
                            started_at=tc_start,
                            ended_at=tc_start,
                            data={
                                "tool_name": block.name,
                                "tool_input": block.input,
                                "tool_use_id": block.id,
                            },
                        )
                    )

                    if block.name == "web_search":
                        result_content = _web_search(block.input.get("query", ""))
                    else:
                        result_content = f"[stub] unknown tool: {block.name}"

                    tr_end = _now()
                    spans.append(
                        TrajectorySpan(
                            id=_new_span_id(),
                            type=SpanType.TOOL_RESULT,
                            started_at=tc_start,
                            ended_at=tr_end,
                            data={
                                "tool_use_id": block.id,
                                "tool_name": block.name,
                                "content": result_content,
                            },
                        )
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_content,
                        }
                    )

                messages.append({"role": "user", "content": tool_results})

            else:
                # end_turn or other stop — extract final text
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text = block.text
                        break

                fo_start = _now()
                spans.append(
                    TrajectorySpan(
                        id=_new_span_id(),
                        type=SpanType.FINAL_OUTPUT,
                        started_at=fo_start,
                        ended_at=fo_start,
                        data={"text": final_text},
                    )
                )
                return Trajectory(spans=spans, final_output=final_text)
