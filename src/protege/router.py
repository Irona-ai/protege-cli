from pathlib import Path
from typing import Any

import typer

from .api_client import ApiError, request
from .cli_utils import fail, get_config, read_bytes
from .config import Config

router_app = typer.Typer(add_completion=False, help="Train and query Custom Router models.")

MAX_DATA_URLS = 10


def upload_dataset(config: Config, json_bytes: bytes) -> dict[str, Any]:
    return request(config, "POST", "/custom-router/upload", content=json_bytes)


def train_router(config: Config, data_urls: list[str], team_id: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"data_urls": data_urls}
    if team_id is not None:
        body["team_id"] = team_id
    return request(config, "POST", "/custom-router/train", json_body=body)


def get_router_status(config: Config, job_id: str) -> dict[str, Any]:
    return request(config, "GET", f"/custom-router/status/{job_id}")


def router_infer(config: Config, router_id: str, prompt: str) -> dict[str, Any]:
    return request(config, "POST", "/custom-router/infer", json_body={"router_id": router_id, "prompt": prompt})


@router_app.command("train")
def router_train(
    data_file: list[Path] = typer.Option([], "--data-file", help="Local training data JSON file, repeatable — uploaded automatically"),
    data_url: list[str] = typer.Option([], "--data-url", help="Already-hosted training data JSON URL, repeatable"),
    team_id: str = typer.Option(None, "--team-id", help="Train under a team workspace (requires admin role on that team)"),
):
    """Train a Custom Router on prompt-to-model examples. Prints the new job id."""
    if not data_file and not data_url:
        fail(RuntimeError("Provide at least one of --data-file, --data-url"))
    config = get_config()

    urls = list(data_url)
    for path in data_file:
        try:
            uploaded = upload_dataset(config, read_bytes(path))
        except (ApiError, RuntimeError) as exc:
            fail(exc)
        urls.append(uploaded["url"])

    if len(urls) > MAX_DATA_URLS:
        fail(RuntimeError(f"At most {MAX_DATA_URLS} training data files/URLs are allowed"))

    try:
        result = train_router(config, urls, team_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Training job queued: {result['job_id']}")


@router_app.command("status")
def router_status(job_id: str):
    """Show a Custom Router training job's status, including the router id once training completes. JOB_ID is printed by `router train`."""
    config = get_config()
    try:
        result = get_router_status(config, job_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"status: {result['status']}")
    if result.get("router_id"):
        typer.echo(f"router id: {result['router_id']}")
    if result.get("error_message"):
        typer.echo(f"error: {result['error_message']}")


@router_app.command("infer")
def router_infer_command(
    router_id: str,
    prompt: str = typer.Option(..., "--prompt", help="Prompt to route"),
):
    """Get the recommended model for a prompt from a trained Custom Router. ROUTER_ID is printed by `router status` once training completes."""
    config = get_config()
    try:
        result = router_infer(config, router_id, prompt)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"top_model: {result['top_model']}")
    typer.echo(f"top_prob: {result['top_prob']}")
