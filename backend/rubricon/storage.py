from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from rubricon.models import CriterionScore, RunRecord, ScenarioResult, Suite, Trajectory, TrajectorySpan
from rubricon.schema import Base, RunRow, ScenarioResultRow, ScoreRow, SuiteRow, TrajectorySpanRow


async def get_engine(db_path: str) -> AsyncEngine:
    """Create async engine and ensure all tables exist."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


def _dt_str(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


async def persist_run(engine: AsyncEngine, suite: Suite, run: RunRecord) -> None:
    """Upsert suite + insert run + results + spans + scores in a single transaction."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            # Upsert suite (by name — one row per unique suite name)
            result = await session.execute(select(SuiteRow).where(SuiteRow.name == suite.name))
            suite_row = result.scalar_one_or_none()
            if suite_row is None:
                suite_row = SuiteRow(
                    id=uuid.uuid4().hex,
                    name=suite.name,
                    description=suite.description,
                    yaml_content=suite.model_dump_json(),
                )
                session.add(suite_row)

            # Insert run
            run_row = RunRow(
                id=run.id,
                suite_id=suite_row.id,
                started_at=_dt_str(run.started_at) or "",
                finished_at=_dt_str(run.finished_at),
                status="completed",
                overall_score=run.overall_score,
            )
            session.add(run_row)

            # Insert scenario results + spans + scores
            for sr in run.scenario_results:
                sr_id = uuid.uuid4().hex
                sr_row = ScenarioResultRow(
                    id=sr_id,
                    run_id=run.id,
                    scenario_id=sr.scenario_id,
                    status=sr.status,
                    error=sr.error,
                    final_output=sr.trajectory.final_output,
                    started_at=_dt_str(sr.started_at),
                    finished_at=_dt_str(sr.finished_at),
                    weighted_score=sr.weighted_score,
                )
                session.add(sr_row)

                for span in sr.trajectory.spans:
                    span_row = TrajectorySpanRow(
                        id=span.id,
                        scenario_result_id=sr_id,
                        span_type=span.type.value,
                        started_at=span.started_at.isoformat(),
                        finished_at=span.ended_at.isoformat(),
                        data_json=span.data,  # JSON column handles serialization
                    )
                    session.add(span_row)

                for cs in sr.scores:
                    score_row = ScoreRow(
                        id=uuid.uuid4().hex,
                        scenario_result_id=sr_id,
                        criterion_name=cs.criterion_name,
                        score=cs.score,
                        justification=cs.justification,
                        cited_span_id=cs.cited_span_id,
                        prompt_version=cs.prompt_version,
                    )
                    session.add(score_row)


async def list_suites(engine: AsyncEngine) -> list[dict]:
    """Select all SuiteRows ordered by created_at DESC."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(SuiteRow).order_by(SuiteRow.created_at.desc())
        )
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "created_at": r.created_at or "",
            }
            for r in rows
        ]


async def list_runs(engine: AsyncEngine, suite_id: str | None = None) -> list[dict]:
    """Select RunRows LEFT-OUTER-JOINed with SuiteRow, optionally filtered by suite_id."""
    from sqlalchemy import String
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        stmt = (
            select(RunRow, SuiteRow.name.label("suite_name"))
            .outerjoin(SuiteRow, RunRow.suite_id == SuiteRow.id)
            .order_by(RunRow.started_at.desc())
        )
        if suite_id is not None:
            stmt = stmt.where(RunRow.suite_id == suite_id)
        result = await session.execute(stmt)
        rows = result.all()
        return [
            {
                "id": row.RunRow.id,
                "suite_id": row.RunRow.suite_id,
                "suite_name": row.suite_name or "",
                "started_at": row.RunRow.started_at,
                "finished_at": row.RunRow.finished_at,
                "status": row.RunRow.status,
                "overall_score": row.RunRow.overall_score,
            }
            for row in rows
        ]


async def get_run(engine: AsyncEngine, run_id: str) -> RunRecord | None:
    """Retrieve a RunRecord from DB by run_id. Span data is plain dicts."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(
            select(RunRow).where(RunRow.id == run_id)
        )
        run_row = result.scalar_one_or_none()
        if run_row is None:
            return None

        suite_result = await session.execute(
            select(SuiteRow).where(SuiteRow.id == run_row.suite_id)
        )
        suite_row = suite_result.scalar_one_or_none()

        # Build per-criterion pass_threshold map from stored suite JSON
        criterion_thresholds: dict[str, int] = {}
        if suite_row:
            stored_suite = Suite.model_validate_json(suite_row.yaml_content)
            criterion_thresholds = {c.name: c.pass_threshold for c in stored_suite.rubric.criteria}

        sr_result = await session.execute(
            select(ScenarioResultRow).where(ScenarioResultRow.run_id == run_id)
        )
        sr_rows = sr_result.scalars().all()

        scenario_results = []
        for sr_row in sr_rows:
            span_result = await session.execute(
                select(TrajectorySpanRow).where(
                    TrajectorySpanRow.scenario_result_id == sr_row.id
                )
            )
            span_rows = span_result.scalars().all()

            spans = []
            for s in span_rows:
                spans.append(
                    TrajectorySpan(
                        id=s.id,
                        type=s.span_type,
                        started_at=datetime.fromisoformat(s.started_at),
                        ended_at=datetime.fromisoformat(s.finished_at),
                        data=s.data_json,
                    )
                )

            # Hydrate scores
            score_result = await session.execute(
                select(ScoreRow).where(ScoreRow.scenario_result_id == sr_row.id)
            )
            score_rows = score_result.scalars().all()
            criterion_scores = [
                CriterionScore(
                    criterion_name=sc.criterion_name,
                    score=sc.score or 0,
                    justification=sc.justification or "",
                    cited_span_id=sc.cited_span_id,
                    passed=(sc.score or 0) >= criterion_thresholds.get(sc.criterion_name, 3),
                    prompt_version=sc.prompt_version or "v1",
                )
                for sc in score_rows
            ]

            trajectory = Trajectory(spans=spans, final_output=sr_row.final_output)
            scenario_results.append(
                ScenarioResult(
                    scenario_id=sr_row.scenario_id,
                    status=sr_row.status,
                    trajectory=trajectory,
                    error=sr_row.error,
                    started_at=datetime.fromisoformat(sr_row.started_at) if sr_row.started_at else None,
                    finished_at=datetime.fromisoformat(sr_row.finished_at) if sr_row.finished_at else None,
                    scores=criterion_scores,
                    weighted_score=sr_row.weighted_score,
                )
            )

        return RunRecord(
            id=run_row.id,
            suite_name=suite_row.name if suite_row else "",
            started_at=datetime.fromisoformat(run_row.started_at),
            finished_at=datetime.fromisoformat(run_row.finished_at) if run_row.finished_at else None,
            scenario_results=scenario_results,
            overall_score=run_row.overall_score,
        )
