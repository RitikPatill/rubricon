from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone

import anthropic

from rubricon.agent import Agent
from rubricon.judge import JUDGE_MODEL, compute_weighted_score, judge_scenario
from rubricon.loader import generate_run_id
from rubricon.models import RunRecord, ScenarioResult, Suite, Trajectory
from rubricon.storage import get_engine, persist_run


async def _run_scenario(
    scenario,
    agent: Agent,
    semaphore: asyncio.Semaphore,
    progress_callback: Callable[[ScenarioResult], None] | None,
) -> ScenarioResult:
    async with semaphore:
        started_at = datetime.now(tz=timezone.utc)
        try:
            trajectory: Trajectory = await agent.run(scenario.input)
            result = ScenarioResult(
                scenario_id=scenario.id,
                status="pass",
                trajectory=trajectory,
                started_at=started_at,
                finished_at=datetime.now(tz=timezone.utc),
            )
        except Exception as exc:  # noqa: BLE001
            result = ScenarioResult(
                scenario_id=scenario.id,
                status="error",
                trajectory=Trajectory(),
                error=str(exc),
                started_at=started_at,
                finished_at=datetime.now(tz=timezone.utc),
            )

    if progress_callback is not None:
        progress_callback(result)
    return result


async def _judge_results(
    suite: Suite,
    results: list[ScenarioResult],
    judge_enabled: bool,
    judge_model: str,
) -> list[ScenarioResult]:
    """Attach CriterionScore list and weighted_score to each passing result."""
    if not judge_enabled:
        return results

    client = anthropic.AsyncAnthropic()

    async def _judge_one(result: ScenarioResult) -> ScenarioResult:
        if result.status != "pass":
            return result
        scores = await judge_scenario(
            client=client,
            rubric=suite.rubric,
            scenario_id=result.scenario_id,
            trajectory=result.trajectory,
            model=judge_model,
        )
        result.scores = scores
        result.weighted_score = compute_weighted_score(scores, suite.rubric)
        return result

    judged = await asyncio.gather(*[_judge_one(r) for r in results])
    return list(judged)


async def execute_run(
    suite: Suite,
    agent: Agent,
    db_path: str = "rubricon.db",
    concurrency: int = 4,
    progress_callback: Callable[[ScenarioResult], None] | None = None,
    judge_enabled: bool = True,
    judge_model: str = JUDGE_MODEL,
) -> str:
    """Execute all scenarios concurrently and persist the run. Returns run_id."""
    run_id = generate_run_id()
    started_at = datetime.now(tz=timezone.utc)

    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        _run_scenario(scenario, agent, semaphore, progress_callback)
        for scenario in suite.scenarios
    ]
    results: list[ScenarioResult] = list(await asyncio.gather(*tasks))

    # Judge phase — runs after all agent scenarios complete
    results = await _judge_results(suite, results, judge_enabled, judge_model)

    # Notify progress callbacks with updated scores
    if progress_callback is not None:
        for result in results:
            if result.weighted_score is not None:
                progress_callback(result)

    scored = [r.weighted_score for r in results if r.weighted_score is not None]
    overall_score = sum(scored) / len(scored) if scored else None

    finished_at = datetime.now(tz=timezone.utc)
    run = RunRecord(
        id=run_id,
        suite_name=suite.name,
        started_at=started_at,
        finished_at=finished_at,
        scenario_results=results,
        overall_score=overall_score,
    )

    engine = await get_engine(db_path)
    await persist_run(engine, suite, run)
    await engine.dispose()

    return run_id
