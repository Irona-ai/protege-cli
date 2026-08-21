from pathlib import Path
from typing import Any

import typer

from .api_client import ApiError, request
from .cli_utils import fail, get_config, read_bytes
from .config import Config

task_app = typer.Typer(add_completion=False, help="Manage Task definitions (agent code + dataset + eval).")


def create_task(
    config: Config,
    zip_bytes: bytes,
    *,
    name: str | None = None,
    description: str | None = None,
    env_id: str | None = None,
) -> dict[str, Any]:
    params = {k: v for k, v in {"name": name, "description": description, "envId": env_id}.items() if v}
    return request(config, "POST", "/tasks", content=zip_bytes, params=params)


def list_tasks(config: Config) -> list[dict[str, Any]]:
    return request(config, "GET", "/tasks")


def get_task(config: Config, task_id: str) -> dict[str, Any]:
    return request(config, "GET", f"/tasks/{task_id}")


def update_task(
    config: Config,
    task_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    env_id: str | None = None,
) -> dict[str, Any]:
    body = {k: v for k, v in {"name": name, "description": description, "envId": env_id}.items() if v is not None}
    return request(config, "PATCH", f"/tasks/{task_id}", json_body=body)


def update_task_zip(config: Config, task_id: str, zip_bytes: bytes) -> dict[str, Any]:
    return request(config, "PATCH", f"/tasks/{task_id}/zip", content=zip_bytes)


def update_task_dataset_md(config: Config, task_id: str, content: bytes) -> dict[str, Any]:
    return request(config, "PATCH", f"/tasks/{task_id}/dataset-md", content=content)


def update_task_task_md(config: Config, task_id: str, content: bytes) -> dict[str, Any]:
    return request(config, "PATCH", f"/tasks/{task_id}/task-md", content=content)


def delete_task(config: Config, task_id: str) -> None:
    request(config, "DELETE", f"/tasks/{task_id}")


@task_app.command("create")
def task_create(
    zip_path: Path,
    name: str = typer.Option(None, "--name"),
    description: str = typer.Option(None, "--description"),
    env_id: str = typer.Option(None, "--env-id"),
):
    """Create a Task from a local zip (agent.py, eval.py, dataset.json at the root). Prints the new task id."""
    config = get_config()
    try:
        task = create_task(config, read_bytes(zip_path), name=name, description=description, env_id=env_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Created task {task['id']}")


@task_app.command("list")
def task_list():
    """List your Tasks."""
    config = get_config()
    try:
        tasks = list_tasks(config)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    for t in tasks:
        typer.echo(f"{t['id']}  {t.get('name', '')}")


@task_app.command("show")
def task_show(task_id: str):
    """Show a Task's details. TASK_ID is printed by `task create`/`task list`."""
    config = get_config()
    try:
        task = get_task(config, task_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    for key, value in task.items():
        typer.echo(f"{key}: {value}")


@task_app.command("update")
def task_update(
    task_id: str,
    name: str = typer.Option(None, "--name"),
    description: str = typer.Option(None, "--description"),
    env_id: str = typer.Option(None, "--env-id"),
):
    """Update a Task's name, description, and/or attached environment."""
    if name is None and description is None and env_id is None:
        fail(RuntimeError("Provide at least one of --name, --description, --env-id"))
    config = get_config()
    try:
        task = update_task(config, task_id, name=name, description=description, env_id=env_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Updated task {task['id']}")


@task_app.command("update-zip")
def task_update_zip(task_id: str, zip_path: Path):
    """Replace a Task's agent.py/eval.py/dataset.json."""
    config = get_config()
    try:
        update_task_zip(config, task_id, read_bytes(zip_path))
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Updated task {task_id} zip")


@task_app.command("update-dataset-md")
def task_update_dataset_md(task_id: str, file: Path):
    """Replace a Task's dataset.md."""
    config = get_config()
    try:
        update_task_dataset_md(config, task_id, read_bytes(file))
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Updated task {task_id} dataset.md")


@task_app.command("update-task-md")
def task_update_task_md(task_id: str, file: Path):
    """Replace a Task's task.md."""
    config = get_config()
    try:
        update_task_task_md(config, task_id, read_bytes(file))
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Updated task {task_id} task.md")


@task_app.command("delete")
def task_delete(task_id: str):
    """Delete a Task."""
    config = get_config()
    try:
        delete_task(config, task_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Deleted task {task_id}")
