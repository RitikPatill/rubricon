from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone

from rubricon.agent import Agent
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


async def execute_run(
    suite: Suite,
    agent: Agent,
    db_path: str = "rubricon.db",
    concurrency: int = 4,
    progress_callback: Callable[[ScenarioResult], None] | None = None,
) -> str:
    """Execute all scenarios concurrently and persist the run. Returns run_id."""
    run_id = generate_run_id()
    started_at = datetime.now(tz=timezone.utc)

    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        _run_scenario(scenario, agent, semaphore, progress_callback)
        for scenario in suite.scenarios
    ]
    results: list[ScenarioResult] = await asyncio.gather(*tasks)

    finished_at = datetime.now(tz=timezone.utc)
    run = RunRecord(
        id=run_id,
        suite_name=suite.name,
        started_at=started_at,
        finished_at=finished_at,
        scenario_results=list(results),
    )

    engine = await get_engine(db_path)
    await persist_run(engine, suite, run)
    await engine.dispose()

    return run_id
