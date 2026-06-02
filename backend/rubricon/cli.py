import typer

app = typer.Typer(help="Rubricon — rubric-based evaluation harness for AI agents.")


@app.command()
def run(suite: str = typer.Argument(..., help="Path to the suite YAML file")) -> None:
    """Run an evaluation suite against your agent."""
    typer.echo("[rubricon] run not yet implemented")


@app.command()
def serve() -> None:
    """Start the Rubricon dashboard server."""
    typer.echo("[rubricon] serve not yet implemented")


if __name__ == "__main__":
    app()
