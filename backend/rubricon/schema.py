from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class SuiteRow(Base):
    __tablename__ = "suites"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    yaml_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, server_default=func.now())

    runs: Mapped[list[RunRow]] = relationship("RunRow", back_populates="suite")


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    suite_id: Mapped[str] = mapped_column(Text, ForeignKey("suites.id"), nullable=False)
    started_at: Mapped[str] = mapped_column(Text, nullable=False)
    finished_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="running")
    overall_score: Mapped[float | None] = mapped_column(nullable=True)

    suite: Mapped[SuiteRow] = relationship("SuiteRow", back_populates="runs")
    scenario_results: Mapped[list[ScenarioResultRow]] = relationship(
        "ScenarioResultRow", back_populates="run"
    )


class ScenarioResultRow(Base):
    __tablename__ = "scenario_results"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(Text, ForeignKey("runs.id"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    weighted_score: Mapped[float | None] = mapped_column(nullable=True)

    run: Mapped[RunRow] = relationship("RunRow", back_populates="scenario_results")
    trajectory_spans: Mapped[list[TrajectorySpanRow]] = relationship(
        "TrajectorySpanRow", back_populates="scenario_result"
    )
    scores: Mapped[list[ScoreRow]] = relationship("ScoreRow", back_populates="scenario_result")


class TrajectorySpanRow(Base):
    __tablename__ = "trajectory_spans"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    scenario_result_id: Mapped[str] = mapped_column(
        Text, ForeignKey("scenario_results.id"), nullable=False
    )
    span_type: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str] = mapped_column(Text, nullable=False)
    finished_at: Mapped[str] = mapped_column(Text, nullable=False)
    data_json: Mapped[Any] = mapped_column(JSON, nullable=False)

    scenario_result: Mapped[ScenarioResultRow] = relationship(
        "ScenarioResultRow", back_populates="trajectory_spans"
    )


class ScoreRow(Base):
    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    scenario_result_id: Mapped[str] = mapped_column(
        Text, ForeignKey("scenario_results.id"), nullable=False
    )
    criterion_name: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int | None] = mapped_column(nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    cited_span_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(Text, nullable=True)

    scenario_result: Mapped[ScenarioResultRow] = relationship(
        "ScenarioResultRow", back_populates="scores"
    )
