import typer

from .config import Config, DEFAULT_BASE_URL, save_config
from .environment import environment_app
from .optimize import optimize_app
from .router import router_app
from .task import task_app

app = typer.Typer(add_completion=False, help="IronLabs platform CLI.")
app.add_typer(task_app, name="task")
app.add_typer(environment_app, name="environment")
app.add_typer(optimize_app, name="optimize")
app.add_typer(router_app, name="router")


@app.command()
def login(
    api_key: str = typer.Option(..., prompt=True, hide_input=True, help="Your IronLabs API key"),
    base_url: str = typer.Option(DEFAULT_BASE_URL, help="IronLabs base URL"),
):
    """Store your IronLabs API key locally."""
    if not base_url:
        typer.secho("--base-url is required.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    save_config(Config(api_key=api_key, base_url=base_url))
    typer.echo("Logged in. Credentials saved to ~/.config/protege/config.json")


if __name__ == "__main__":
    app()
