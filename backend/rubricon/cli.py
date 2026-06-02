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
            row["score"],
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
        row = {
            "scenario_id": result.scenario_id,
            "status": result.status,
            "spans": len(result.trajectory.spans),
            "score": "pending",
        }
        rows.append(row)
        rows_by_id[result.scenario_id] = row

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
            )
        )
        live.update(_make_table(rows))

    pass_count = sum(1 for r in rows if r["status"] == "pass")
    fail_count = len(rows) - pass_count
    console.print()
    console.print(f"[bold green]Done.[/bold green]  Run ID: [cyan]{run_id}[/cyan]")
    console.print(
        f"  Scenarios: {len(rows)}  |  "
        f"[green]pass: {pass_count}[/green]  |  "
        f"[red]fail/error: {fail_count}[/red]"
    )
    console.print(f"  DB: {db}")


@app.command()
def serve() -> None:
    """Start the Rubricon dashboard server."""
    typer.echo("[rubricon] serve not yet implemented")


if __name__ == "__main__":
    app()
