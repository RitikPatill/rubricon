from __future__ import annotations

import uuid
from pathlib import Path

import yaml
from pydantic import ValidationError

from rubricon.models import Suite


def load_suite(path: str | Path) -> Suite:
    """Load a Suite from a YAML file. Raises ValueError on schema mismatch."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Suite file not found: {path}")
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    try:
        return Suite.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid suite YAML at {path}:\n{exc}") from exc


def generate_run_id() -> str:
    """Generate a unique run ID (uuid4 hex)."""
    return uuid.uuid4().hex
