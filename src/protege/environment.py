from typing import Any

import typer

from .api_client import ApiError, request
from .cli_utils import fail, get_config, parse_kv
from .config import Config

environment_app = typer.Typer(
    add_completion=False,
    help="Manage Environments — named, encrypted key-sets shared across Tasks and, in the future, Custom Router.",
)


def create_env(config: Config, env_name: str, keys: dict[str, str]) -> dict[str, Any]:
    return request(config, "POST", "/envs", json_body={"envName": env_name, "keys": keys})


def list_envs(config: Config) -> list[dict[str, Any]]:
    return request(config, "GET", "/envs")


def get_env(config: Config, env_id: str) -> dict[str, Any]:
    return request(config, "GET", f"/envs/{env_id}")


def update_env(
    config: Config,
    env_id: str,
    *,
    env_name: str | None = None,
    keys: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if env_name is not None:
        body["envName"] = env_name
    if keys is not None:
        body["keys"] = keys
    return request(config, "PATCH", f"/envs/{env_id}", json_body=body)


def delete_env(config: Config, env_id: str) -> None:
    request(config, "DELETE", f"/envs/{env_id}")


@environment_app.command("create")
def environment_create(
    name: str,
    key: list[str] = typer.Option([], "--key", help="KEY=VALUE, repeatable"),
):
    """Create an Environment. Prints the new environment id."""
    keys = parse_kv(key, "--key")
    if not keys:
        fail(RuntimeError("At least one --key KEY=VALUE is required"))
    config = get_config()
    try:
        env = create_env(config, name, keys)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Created environment {env['id']}")


@environment_app.command("list")
def environment_list():
    """List your Environments."""
    config = get_config()
    try:
        envs = list_envs(config)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    for e in envs:
        key_names = ", ".join(k["name"] for k in e.get("keys", []))
        typer.echo(f"{e['id']}  {e.get('envName', '')}  [{key_names}]")


@environment_app.command("show")
def environment_show(env_id: str):
    """Show an Environment's details (values are always masked). ENV_ID is printed by `environment create`/`environment list`."""
    config = get_config()
    try:
        env = get_env(config, env_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"id: {env['id']}")
    typer.echo(f"envName: {env.get('envName', '')}")
    for k in env.get("keys", []):
        typer.echo(f"  {k['name']} = {k['masked']}")


@environment_app.command("update")
def environment_update(
    env_id: str,
    rename: str = typer.Option(None, "--rename", help="New environment name"),
    set_: list[str] = typer.Option([], "--set", help="KEY=VALUE to add/overwrite, repeatable"),
    unset: list[str] = typer.Option([], "--unset", help="KEY to remove, repeatable"),
):
    """Rename an Environment and/or add/overwrite/remove its keys."""
    if rename is None and not set_ and not unset:
        fail(RuntimeError("Provide at least one of --rename, --set, --unset"))
    keys: dict[str, str | None] = parse_kv(set_, "--set")
    for k in unset:
        keys[k] = None
    config = get_config()
    try:
        env = update_env(config, env_id, env_name=rename, keys=keys or None)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Updated environment {env['id']}")


@environment_app.command("delete")
def environment_delete(env_id: str):
    """Delete an Environment."""
    config = get_config()
    try:
        delete_env(config, env_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Deleted environment {env_id}")
