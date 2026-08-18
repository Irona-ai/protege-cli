import difflib
from pathlib import Path

import typer

from . import api, cache, local_exec
from ..cli_utils import fail, get_config, parse_kv, read_bytes
from ..config import Config

agent_finetuning_app = typer.Typer(add_completion=False, help="Launch and manage AgentOpt agent-finetuning jobs.")
task_app = typer.Typer(add_completion=False, help="Manage reusable Task definitions (agent code + dataset + eval).")
env_app = typer.Typer(add_completion=False, help="Manage Env key-sets attached to runs.")
agent_finetuning_app.add_typer(task_app, name="task")
agent_finetuning_app.add_typer(env_app, name="env")

TERMINAL_STATUSES = {"completed", "failed", "cancelled", "interrupted", "partial"}



@task_app.command("create")
def task_create(
    zip_path: Path,
    name: str = typer.Option(None, "--name"),
    description: str = typer.Option(None, "--description"),
    env_id: str = typer.Option(None, "--env-id"),
):
    """Create a Task from a local zip (agent.py, eval.py, dataset.json at the root)."""
    config = get_config()
    try:
        task = api.create_task(
            config, read_bytes(zip_path), name=name, description=description, env_id=env_id
        )
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Created task {task['id']}")


@task_app.command("list")
def task_list():
    """List your Tasks."""
    config = get_config()
    try:
        tasks = api.list_tasks(config)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    for t in tasks:
        typer.echo(f"{t['id']}  {t.get('name', '')}")


@task_app.command("show")
def task_show(task_id: str):
    """Show a Task's details."""
    config = get_config()
    try:
        task = api.get_task(config, task_id)
    except (api.ApiError, RuntimeError) as exc:
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
    """Update a Task's name, description, and/or attached env."""
    if name is None and description is None and env_id is None:
        fail(RuntimeError("Provide at least one of --name, --description, --env-id"))
    config = get_config()
    try:
        task = api.update_task(config, task_id, name=name, description=description, env_id=env_id)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Updated task {task['id']}")


@task_app.command("update-zip")
def task_update_zip(task_id: str, zip_path: Path):
    """Replace a Task's agent.py/eval.py/dataset.json."""
    config = get_config()
    try:
        api.update_task_zip(config, task_id, read_bytes(zip_path))
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Updated task {task_id} zip")


@task_app.command("update-dataset-md")
def task_update_dataset_md(task_id: str, file: Path):
    """Replace a Task's dataset.md."""
    config = get_config()
    try:
        api.update_task_dataset_md(config, task_id, read_bytes(file))
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Updated task {task_id} dataset.md")


@task_app.command("update-task-md")
def task_update_task_md(task_id: str, file: Path):
    """Replace a Task's task.md."""
    config = get_config()
    try:
        api.update_task_task_md(config, task_id, read_bytes(file))
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Updated task {task_id} task.md")


@task_app.command("delete")
def task_delete(task_id: str):
    """Delete a Task."""
    config = get_config()
    try:
        api.delete_task(config, task_id)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Deleted task {task_id}")



@env_app.command("create")
def env_create(
    name: str,
    key: list[str] = typer.Option([], "--key", help="KEY=VALUE, repeatable"),
):
    """Create an Env (a named, encrypted key-set)."""
    keys = parse_kv(key, "--key")
    if not keys:
        fail(RuntimeError("At least one --key KEY=VALUE is required"))
    config = get_config()
    try:
        env = api.create_env(config, name, keys)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Created env {env['id']}")


@env_app.command("list")
def env_list():
    """List your Envs."""
    config = get_config()
    try:
        envs = api.list_envs(config)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    for e in envs:
        key_names = ", ".join(k["name"] for k in e.get("keys", []))
        typer.echo(f"{e['id']}  {e.get('envName', '')}  [{key_names}]")


@env_app.command("show")
def env_show(env_id: str):
    """Show an Env's details (values are always masked)."""
    config = get_config()
    try:
        env = api.get_env(config, env_id)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"id: {env['id']}")
    typer.echo(f"envName: {env.get('envName', '')}")
    for k in env.get("keys", []):
        typer.echo(f"  {k['name']} = {k['masked']}")


@env_app.command("update")
def env_update(
    env_id: str,
    rename: str = typer.Option(None, "--rename", help="New env name"),
    set_: list[str] = typer.Option([], "--set", help="KEY=VALUE to add/overwrite, repeatable"),
    unset: list[str] = typer.Option([], "--unset", help="KEY to remove, repeatable"),
):
    """Rename an Env and/or add/overwrite/remove its keys."""
    if rename is None and not set_ and not unset:
        fail(RuntimeError("Provide at least one of --rename, --set, --unset"))
    keys: dict[str, str | None] = parse_kv(set_, "--set")
    for k in unset:
        keys[k] = None
    config = get_config()
    try:
        env = api.update_env(config, env_id, env_name=rename, keys=keys or None)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Updated env {env['id']}")


@env_app.command("delete")
def env_delete(env_id: str):
    """Delete an Env."""
    config = get_config()
    try:
        api.delete_env(config, env_id)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Deleted env {env_id}")


def _ensure_downloaded(
    config: Config, optimized_prompt_id: str, iteration: int | None, force: bool
) -> Path:
    if not force and iteration is None and cache.is_cached(optimized_prompt_id):
        return cache.agent_file_path(optimized_prompt_id)
    try:
        code = api.get_agent_code(config, optimized_prompt_id, iteration)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    return cache.write_agent_file(optimized_prompt_id, code["content"])


@agent_finetuning_app.command()
def download(
    optimized_prompt_id: str,
    iteration: int = typer.Option(None, "--iteration", help="Specific iteration; defaults to the latest"),
    force: bool = typer.Option(False, "--force", help="Re-download even if already cached"),
):
    """Download an agent's code (agent.py) so it can be run locally."""
    config = get_config()
    path = _ensure_downloaded(config, optimized_prompt_id, iteration, force)
    typer.echo(f"Downloaded agent code to {path}")


@agent_finetuning_app.command("run-local")
def run_local(
    optimized_prompt_id: str,
    input: str = typer.Option(..., "--input", help="Input text to pass to the agent"),
    llm_api_key: str = typer.Option(
        None,
        "--llm-api-key",
        envvar="OPENROUTER_API_KEY",
        help="LLM API key the agent uses internally (or set OPENROUTER_API_KEY)",
    ),
    iteration: int = typer.Option(None, "--iteration", help="Specific iteration; defaults to the latest"),
    force_download: bool = typer.Option(False, "--force-download", help="Re-download before running"),
):
    """Download (if needed) and run an agent's code locally against a single input."""
    if not llm_api_key:
        fail(RuntimeError("No LLM API key provided. Pass --llm-api-key or set OPENROUTER_API_KEY."))
    config = get_config()
    path = _ensure_downloaded(config, optimized_prompt_id, iteration, force_download)
    try:
        predictions = local_exec.run_agent(path, [input], llm_api_key)
    except local_exec.LocalExecError as exc:
        fail(exc)
    for prediction in predictions:
        typer.echo(prediction)


def _print_progress(config: Config, job_id: str) -> str:
    training_jobs = api.list_training_jobs(config)
    job = next((j for j in training_jobs if j["id"] == job_id), None)
    if job is None:
        typer.echo(f"Job {job_id}: not found")
        return "failed"

    prompts = [p for p in api.list_optimized_prompts(config) if p["trainingJobId"] == job_id]
    typer.echo(f"Job {job_id}: {job['status']}")
    for p in prompts:
        iterations = p.get("TrainingJob", {}).get("OptimizationIteration", [])
        latest = iterations[-1] if iterations else None
        score = latest.get("score") if latest else None
        iter_num = latest.get("iteration") if latest else None
        typer.echo(f"  {p['model']}: iteration={iter_num} score={score}")
    return job["status"]


@agent_finetuning_app.command()
def run(
    task_id: str = typer.Option(None, "--task-id", help="Launch from an existing Task"),
    input_url: str = typer.Option(None, "--input-url", help="Launch from a zip URL (ad hoc, no Task)"),
    target_models: str = typer.Option(..., "--target-models", help="Comma-separated model list (1-5)"),
    n_iterations: int = typer.Option(15, "--n-iterations"),
    overall_timeout: int = typer.Option(3600, "--overall-timeout"),
    llm_call_timeout: int = typer.Option(600, "--llm-call-timeout"),
    sandbox_timeout: int = typer.Option(3600, "--sandbox-timeout"),
    enable_mcp: bool = typer.Option(False, "--enable-mcp"),
    force_baseline: bool = typer.Option(False, "--force-baseline"),
    run_benchmark: bool = typer.Option(False, "--run-benchmark"),
    force_benchmark: bool = typer.Option(False, "--force-benchmark"),
    env_id: str = typer.Option(None, "--env-id", help="Only used with --input-url; Task-based runs use the Task's own env"),
    team_id: str = typer.Option(None, "--team-id"),
    name: str = typer.Option(None, "--name"),
    description: str = typer.Option(None, "--description"),
    watch: bool = typer.Option(False, "--watch", help="Poll until the job reaches a terminal status"),
):
    """Launch an AgentOpt job against one or more target models."""
    if bool(task_id) == bool(input_url):
        fail(RuntimeError("Provide exactly one of --task-id or --input-url"))

    models = [m.strip() for m in target_models.split(",") if m.strip()]
    if not models:
        fail(RuntimeError("--target-models must contain at least one model"))

    config = get_config()
    body = {
        "task_id": task_id,
        "input_url": input_url,
        "target_models": models,
        "n_iterations": n_iterations,
        "overall_timeout_seconds": overall_timeout,
        "llm_call_timeout_seconds": llm_call_timeout,
        "sandbox_timeout_seconds": sandbox_timeout,
        "enable_mcp": enable_mcp,
        "force_baseline": force_baseline,
        "run_benchmark": run_benchmark,
        "force_benchmark": force_benchmark,
        "env_id": env_id,
        "teamId": team_id,
        "name": name,
        "description": description,
    }
    body = {k: v for k, v in body.items() if v is not None}

    try:
        result = api.launch_job(config, body)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)

    job_id = result["job_id"]
    typer.echo(f"Job queued: {job_id}")

    if not watch:
        return

    import time

    while True:
        try:
            status = _print_progress(config, job_id)
        except (api.ApiError, RuntimeError) as exc:
            fail(exc)
        if status in TERMINAL_STATUSES:
            break
        time.sleep(15)


@agent_finetuning_app.command()
def jobs():
    """List all your AgentOpt jobs."""
    config = get_config()
    try:
        training_jobs = api.list_training_jobs(config)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    if not training_jobs:
        typer.echo("No jobs found.")
        return
    for j in sorted(training_jobs, key=lambda x: x.get("createdAt", ""), reverse=True):
        error = f"  error={j['errorMessage']}" if j.get("errorMessage") else ""
        typer.echo(f"{j['id']}  {j.get('status', '')}  {j.get('createdAt', '')}{error}")


@agent_finetuning_app.command()
def status(job_id: str):
    """Show a job's status and per-model iteration progress."""
    config = get_config()
    try:
        _print_progress(config, job_id)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)


@agent_finetuning_app.command()
def cancel(job_id: str):
    """Cancel a queued or running job."""
    config = get_config()
    try:
        result = api.cancel_job(config, job_id)
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Cancelled {job_id} ({result['sandboxes_killed']} sandbox(es) killed)")


@agent_finetuning_app.command()
def results(
    job_id: str,
    model: str = typer.Option(None, "--model", help="Only show this target model"),
    output_dir: Path = typer.Option(None, "--output-dir", help="Download each model's final agent.py here"),
):
    """Show a job's final results, optionally downloading each model's agent code."""
    config = get_config()
    try:
        prompts = [p for p in api.list_optimized_prompts(config) if p["trainingJobId"] == job_id]
    except (api.ApiError, RuntimeError) as exc:
        fail(exc)

    if model:
        prompts = [p for p in prompts if model in p.get("model", [])]
    if not prompts:
        fail(RuntimeError(f"No results found for job {job_id}"))

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    for p in prompts:
        model_names = ", ".join(p.get("model", []))
        metrics = p.get("metrics") or {}
        typer.echo(f"{model_names}: {metrics}")

        cost = (p.get("costBreakdown") or {}).get("totalCostUsd")
        if cost is not None:
            typer.echo(f"  Cost: ${cost:.4f}")

        orig = p.get("originalPrompt") or ""
        opt = p.get("optimizedPrompt") or orig
        if orig and orig != opt:
            diff = difflib.unified_diff(
                orig.splitlines(keepends=True),
                opt.splitlines(keepends=True),
                fromfile="original",
                tofile="optimized",
                lineterm="",
            )
            typer.echo("  --- Prompt diff ---")
            for line in diff:
                typer.echo(f"  {line}")

        if not output_dir:
            continue

        iterations = p.get("TrainingJob", {}).get("OptimizationIteration", [])
        real_iterations = [i for i in iterations if i.get("iteration", -1) >= 0]
        if not real_iterations:
            typer.echo(f"  (no iteration commits to download for {model_names})")
            continue
        latest = max(real_iterations, key=lambda i: i["iteration"])

        try:
            code = api.get_agent_code(config, p["id"], latest["iteration"])
        except (api.ApiError, RuntimeError) as exc:
            typer.secho(f"  Could not download code for {model_names}: {exc}", fg=typer.colors.RED, err=True)
            continue

        out_path = output_dir / f"{p['id']}_{model_names.replace('/', '_')}.py"
        out_path.write_text(code["content"])
        typer.echo(f"  Saved to {out_path}")
