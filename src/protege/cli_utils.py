from pathlib import Path

import typer

from .config import Config, require_config


def fail(exc: Exception) -> None:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


def get_config() -> Config:
    try:
        return require_config()
    except RuntimeError as exc:
        fail(exc)


def read_bytes(path: Path) -> bytes:
    if not path.exists():
        fail(RuntimeError(f"File not found: {path}"))
    return path.read_bytes()


def parse_kv(pairs: list[str], flag: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            fail(RuntimeError(f"{flag} values must be KEY=VALUE, got: {pair}"))
        key, _, value = pair.partition("=")
        if not key.strip():
            fail(RuntimeError(f"{flag} values must be KEY=VALUE, got: {pair}"))
        result[key.strip()] = value
    return result
