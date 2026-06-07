from __future__ import annotations

import asyncio
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table

from rubricon.loader import load_suite
from rubricon.models import ScenarioResult

app = typer.Typer(help="Rubricon — rubric-based evaluation harness for AI agents.")
console = Console()


def _score_display(row: dict) -> str:
    if row["weighted_score"] is not None:
        return f"{row['weighted_score']:.2f}/5"
    return "—"


def _make_table(rows: list[dict]) -> Table:
    table = Table(title="Rubricon Run", expand=True)
    table.add_column("Scenario ID", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Spans", justify="right")
    table.add_column("Score", justify="right")
    for row in rows:
        status_style = "green" if row["status"] == "pass" else "red"
        table.add_row(
            row["scenario_id"],
            f"[{status_style}]{row['status']}[/{status_style}]",
            str(row["spans"]),
            _score_display(row),
        )
    return table


@app.command()
def run(
    suite: str = typer.Argument(..., help="Path to the suite YAML file"),
    concurrency: int = typer.Option(4, "--concurrency", "-c", help="Max concurrent scenarios"),
    db: str = typer.Option("rubricon.db", "--db", help="Path to SQLite database"),
    agent: str = typer.Option(
        "research", "--agent", help="Agent to use (currently: research)"
    ),
    no_judge: bool = typer.Option(False, "--no-judge", help="Skip LLM judging"),
) -> None:
    """Run an evaluation suite against your agent."""
    if agent == "research":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set — required for the research agent")

    suite_path = Path(suite)
    if not suite_path.exists():
        console.print(f"[red]Suite file not found: {suite}[/red]")
        raise typer.Exit(1)

    try:
        suite_obj = load_suite(suite_path)
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[red]Failed to load suite: {exc}[/red]")
        raise typer.Exit(1)

    console.print(
        f"[bold]Running suite:[/bold] {suite_obj.name} "
        f"({len(suite_obj.scenarios)} scenarios, concurrency={concurrency})"
    )

    rows: list[dict] = []
    rows_by_id: dict[str, dict] = {}

    def progress_callback(result: ScenarioResult) -> None:
        sid = result.scenario_id
        if sid in rows_by_id:
            # Second call after judging — update score on existing row
            rows_by_id[sid]["weighted_score"] = result.weighted_score
        else:
            row = {
                "scenario_id": sid,
                "status": result.status,
                "spans": len(result.trajectory.spans),
                "weighted_score": result.weighted_score,
            }
            rows.append(row)
            rows_by_id[sid] = row

    from rubricon.engine import execute_run

    if agent == "research":
        from rubricon.agent import ResearchAgent
        agent_obj = ResearchAgent(api_key=api_key)
    else:
        console.print(f"[red]Unknown agent: {agent}[/red]")
        raise typer.Exit(1)

    with Live(refresh_per_second=4, console=console) as live:
        def cb(result: ScenarioResult) -> None:
            progress_callback(result)
            live.update(_make_table(rows))

        run_id = asyncio.run(
            execute_run(
                suite=suite_obj,
                agent=agent_obj,
                db_path=db,
                concurrency=concurrency,
                progress_callback=cb,
                judge_enabled=not no_judge,
            )
        )
        live.update(_make_table(rows))

    pass_count = sum(1 for r in rows if r["status"] == "pass")
    fail_count = len(rows) - pass_count
    scored = [r["weighted_score"] for r in rows if r["weighted_score"] is not None]
    overall_score = sum(scored) / len(scored) if scored else None

    console.print()
    console.print(f"[bold green]Done.[/bold green]  Run ID: [cyan]{run_id}[/cyan]")
    console.print(
        f"  Scenarios: {len(rows)}  |  "
        f"[green]pass: {pass_count}[/green]  |  "
        f"[red]fail/error: {fail_count}[/red]"
    )
    if overall_score is not None:
        console.print(f"  Overall score: [bold]{overall_score:.2f}/5[/bold]")
    console.print(f"  DB: {db}")


@app.command()
def compare(
    run_a: str = typer.Argument(..., help="First run ID (baseline)"),
    run_b: str = typer.Argument(..., help="Second run ID (new)"),
    db: str = typer.Option("rubricon.db", "--db", help="Path to SQLite database"),
) -> None:
    """Compare two runs side-by-side: overall delta, per-scenario and per-criterion diffs."""
    from rubricon.storage import get_engine, get_run

    async def _fetch(run_id: str):
        engine = await get_engine(db)
        try:
            return await get_run(engine, run_id)
        finally:
            await engine.dispose()

    record_a = asyncio.run(_fetch(run_a))
    if record_a is None:
        console.print(f"[red]Run not found: {run_a}[/red]")
        raise typer.Exit(1)

    record_b = asyncio.run(_fetch(run_b))
    if record_b is None:
        console.print(f"[red]Run not found: {run_b}[/red]")
        raise typer.Exit(1)

    # Overall summary
    score_a = record_a.overall_score
    score_b = record_b.overall_score
    if score_a is not None and score_b is not None:
        delta = score_b - score_a
        delta_str = f"[green]+{delta:.2f}[/green]" if delta > 0.1 else (f"[red]{delta:.2f}[/red]" if delta < -0.1 else f"{delta:.2f}")
    else:
        delta_str = "—"

    header = Table(title="Overall Comparison", expand=False)
    header.add_column("Run", style="cyan")
    header.add_column("Score", justify="right")
    header.add_column("Delta", justify="right")
    header.add_row(f"A  {run_a[:12]}", f"{score_a:.2f}/5" if score_a is not None else "—", "")
    header.add_row(f"B  {run_b[:12]}", f"{score_b:.2f}/5" if score_b is not None else "—", delta_str)
    console.print(header)
    console.print()

    # Per-scenario table
    scenarios_a = {sr.scenario_id: sr for sr in record_a.scenario_results}
    scenarios_b = {sr.scenario_id: sr for sr in record_b.scenario_results}
    all_ids = sorted(set(scenarios_a) | set(scenarios_b))

    scenario_table = Table(title="Per-Scenario Diff", expand=True)
    scenario_table.add_column("Scenario", style="cyan", no_wrap=True)
    scenario_table.add_column("Score A", justify="right")
    scenario_table.add_column("Score B", justify="right")
    scenario_table.add_column("Delta", justify="right")

    for sid in all_ids:
        sr_a = scenarios_a.get(sid)
        sr_b = scenarios_b.get(sid)
        s_a = sr_a.weighted_score if sr_a else None
        s_b = sr_b.weighted_score if sr_b else None
        if s_a is not None and s_b is not None:
            d = s_b - s_a
            d_str = f"[green]+{d:.2f}[/green]" if d > 0.1 else (f"[red]{d:.2f}[/red]" if d < -0.1 else f"{d:.2f}")
        else:
            d_str = "—"
        scenario_table.add_row(
            sid,
            f"{s_a:.2f}" if s_a is not None else "[dim]missing[/dim]",
            f"{s_b:.2f}" if s_b is not None else "[dim]missing[/dim]",
            d_str,
        )
    console.print(scenario_table)
    console.print()

    # Per-criterion breakdown for changed scenarios
    for sid in all_ids:
        sr_a = scenarios_a.get(sid)
        sr_b = scenarios_b.get(sid)
        s_a = sr_a.weighted_score if sr_a else None
        s_b = sr_b.weighted_score if sr_b else None
        if s_a is None or s_b is None or abs(s_b - s_a) <= 0.1:
            continue

        crit_a = {cs.criterion_name: cs for cs in sr_a.scores} if sr_a else {}
        crit_b = {cs.criterion_name: cs for cs in sr_b.scores} if sr_b else {}
        all_crit = sorted(set(crit_a) | set(crit_b))

        crit_table = Table(title=f"Criteria — {sid}", expand=True)
        crit_table.add_column("Criterion", style="cyan")
        crit_table.add_column("Score A", justify="right")
        crit_table.add_column("Score B", justify="right")
        crit_table.add_column("Delta", justify="right")
        crit_table.add_column("Pass A", justify="center")
        crit_table.add_column("Pass B", justify="center")

        for cname in all_crit:
            cs_a = crit_a.get(cname)
            cs_b = crit_b.get(cname)
            c_a = float(cs_a.score) if cs_a else None
            c_b = float(cs_b.score) if cs_b else None
            if c_a is not None and c_b is not None:
                cd = c_b - c_a
                cd_str = f"[green]+{cd:.1f}[/green]" if cd > 0.1 else (f"[red]{cd:.1f}[/red]" if cd < -0.1 else f"{cd:.1f}")
            else:
                cd_str = "—"
            pass_a = ("[green]✓[/green]" if cs_a.passed else "[red]✗[/red]") if cs_a else "—"
            pass_b = ("[green]✓[/green]" if cs_b.passed else "[red]✗[/red]") if cs_b else "—"
            crit_table.add_row(
                cname,
                f"{c_a:.1f}" if c_a is not None else "[dim]—[/dim]",
                f"{c_b:.1f}" if c_b is not None else "[dim]—[/dim]",
                cd_str,
                pass_a,
                pass_b,
            )
        console.print(crit_table)
        console.print()


@app.command()
def serve(
    db: str = typer.Option("rubricon.db", "--db", help="Path to SQLite database"),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Start the Rubricon API server (then open http://localhost:3000)."""
    import uvicorn

    from rubricon.api import create_app

    console.print(f"[bold]Starting Rubricon API[/bold] on http://{host}:{port}")
    uvicorn.run(create_app(db_path=db), host=host, port=port)


if __name__ == "__main__":
    app()
