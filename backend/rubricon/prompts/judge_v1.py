from __future__ import annotations

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = (
    "You are an impartial rubric judge evaluating an AI agent's execution trajectory.\n"
    "Your task is to score the agent's performance on a single criterion using the 1–5 scale\n"
    "defined by the descriptors provided.\n\n"
    "Rules:\n"
    "- Base your score solely on evidence in the trajectory.\n"
    "- Cite the span ID (from the trajectory listing) that most influenced your score.\n"
    "- Be concise but specific in your justification.\n"
    "- Always call record_score — never respond with plain text."
)

USER_TEMPLATE = (
    "Evaluate the agent trajectory below against this criterion.\n\n"
    "## Criterion\n"
    "**Name:** {criterion_name}\n"
    "**Description:** {criterion_description}\n\n"
    "## Scoring Descriptors\n"
    "{descriptors_block}\n\n"
    "## Agent Trajectory\n"
    "{trajectory_text}\n\n"
    "Call record_score with your integer score (1–5), a brief justification, "
    "and the cited_span_id of the span that most influenced your decision (or null)."
)

RECORD_SCORE_TOOL: dict = {
    "name": "record_score",
    "description": "Submit your score for this criterion.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {"type": "integer", "minimum": 1, "maximum": 5},
            "justification": {"type": "string"},
            "cited_span_id": {"type": ["string", "null"]},
        },
        "required": ["score", "justification"],
    },
}
