import difflib
import time
from pathlib import Path
from typing import Any

import typer

from . import cache, local_exec
from .api_client import ApiError, request
from .cli_utils import fail, get_config, read_bytes
from .config import Config

optimize_app = typer.Typer(add_completion=False, help="Launch and monitor agent-finetuning jobs, then run or inspect the resulting agents.")

TERMINAL_STATUSES = {"completed", "failed", "cancelled", "interrupted", "partial"}
MAX_INFER_INPUTS = 10


def upload_input(config: Config, zip_bytes: bytes) -> dict[str, Any]:
    return request(config, "POST", "/agent-optimizer/upload", content=zip_bytes)


def launch_job(config: Config, body: dict[str, Any]) -> dict[str, Any]:
    return request(config, "POST", "/agent-optimizer/optimize", json_body=body)


def cancel_job(config: Config, job_id: str) -> dict[str, Any]:
    return request(config, "POST", "/agent-optimizer/cancel", json_body={"job_id": job_id})


def list_training_jobs(config: Config) -> list[dict[str, Any]]:
    return request(config, "GET", "/trainingjobs")


def list_optimized_prompts(config: Config) -> list[dict[str, Any]]:
    return request(config, "GET", "/optimized-prompts")


def get_agent_code(config: Config, agent_id: str, iteration: int | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if iteration is not None:
        params["iteration"] = iteration
    return request(config, "GET", f"/optimized-prompts/{agent_id}/agent-code", params=params)


def infer_agent(config: Config, agent_id: str, inputs: list[str]) -> dict[str, Any]:
    return request(config, "POST", f"/agent-optimizer/{agent_id}/infer", json_body={"inputs": inputs})


def get_infer_status(config: Config, agent_id: str) -> dict[str, Any]:
    return request(config, "GET", f"/agent-optimizer/{agent_id}/infer-status")


def get_judgement(config: Config, agent_id: str, log_id: str) -> dict[str, Any]:
    return request(config, "GET", f"/agent-optimizer/{agent_id}/judgement/{log_id}")


def _print_progress(config: Config, job_id: str) -> str:
    training_jobs = list_training_jobs(config)
    job = next((j for j in training_jobs if j["id"] == job_id), None)
    if job is None:
        typer.echo(f"Job {job_id}: not found")
        return "failed"

    prompts = [p for p in list_optimized_prompts(config) if p["trainingJobId"] == job_id]
    typer.echo(f"Job {job_id}: {job['status']}")
    for p in prompts:
        iterations = p.get("TrainingJob", {}).get("OptimizationIteration", [])
        latest = iterations[-1] if iterations else None
        score = latest.get("score") if latest else None
        iter_num = latest.get("iteration") if latest else None
        typer.echo(f"  agent {p['id']}  model={p['model']}  iteration={iter_num} score={score}")
    return job["status"]


@optimize_app.command()
def run(
    task_id: str = typer.Option(None, "--task-id", help="Launch from an existing Task"),
    input_url: str = typer.Option(None, "--input-url", help="Launch from an already-hosted zip URL (ad hoc, no Task)"),
    input_zip: Path = typer.Option(None, "--input-zip", help="Launch from a local zip file (ad hoc, no Task) — uploaded automatically"),
    target_models: str = typer.Option(..., "--target-models", help="Comma-separated model list (1-5)"),
    n_iterations: int = typer.Option(15, "--n-iterations"),
    overall_timeout: int = typer.Option(3600, "--overall-timeout"),
    llm_call_timeout: int = typer.Option(600, "--llm-call-timeout"),
    sandbox_timeout: int = typer.Option(3600, "--sandbox-timeout"),
    enable_mcp: bool = typer.Option(False, "--enable-mcp"),
    force_baseline: bool = typer.Option(False, "--force-baseline"),
    run_benchmark: bool = typer.Option(False, "--run-benchmark"),
    force_benchmark: bool = typer.Option(False, "--force-benchmark"),
    env_id: str = typer.Option(None, "--env-id", help="Only used with --input-url/--input-zip; Task-based runs use the Task's own environment"),
    team_id: str = typer.Option(None, "--team-id"),
    name: str = typer.Option(None, "--name"),
    description: str = typer.Option(None, "--description"),
    watch: bool = typer.Option(False, "--watch", help="Poll until the job reaches a terminal status"),
):
    """Launch an optimization job against one or more target models. Prints the new job id."""
    if sum([bool(task_id), bool(input_url), bool(input_zip)]) != 1:
        fail(RuntimeError("Provide exactly one of --task-id, --input-url, --input-zip"))

    models = [m.strip() for m in target_models.split(",") if m.strip()]
    if not models:
        fail(RuntimeError("--target-models must contain at least one model"))

    config = get_config()

    if input_zip:
        try:
            uploaded = upload_input(config, read_bytes(input_zip))
        except (ApiError, RuntimeError) as exc:
            fail(exc)
        input_url = uploaded["url"]

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
        result = launch_job(config, body)
    except (ApiError, RuntimeError) as exc:
        fail(exc)

    job_id = result["job_id"]
    typer.echo(f"Job queued: {job_id}")

    if not watch:
        return

    while True:
        try:
            status = _print_progress(config, job_id)
        except (ApiError, RuntimeError) as exc:
            fail(exc)
        if status in TERMINAL_STATUSES:
            break
        time.sleep(15)


@optimize_app.command("list")
def optimize_list():
    """List all your optimization jobs."""
    config = get_config()
    try:
        training_jobs = list_training_jobs(config)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    if not training_jobs:
        typer.echo("No jobs found.")
        return
    for j in sorted(training_jobs, key=lambda x: x.get("createdAt", ""), reverse=True):
        error = f"  error={j['errorMessage']}" if j.get("errorMessage") else ""
        typer.echo(f"{j['id']}  {j.get('status', '')}  {j.get('createdAt', '')}{error}")


@optimize_app.command()
def status(job_id: str):
    """Show a job's status and per-model iteration progress, including each agent's id. JOB_ID is printed by `optimize run`/`optimize list`."""
    config = get_config()
    try:
        _print_progress(config, job_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)


@optimize_app.command()
def cancel(job_id: str):
    """Cancel a queued or running job."""
    config = get_config()
    try:
        result = cancel_job(config, job_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"Cancelled {job_id} ({result['sandboxes_killed']} sandbox(es) killed)")


@optimize_app.command()
def result(
    job_id: str,
    model: str = typer.Option(None, "--model", help="Only show this target model"),
    output_dir: Path = typer.Option(None, "--output-dir", help="Download each model's final agent.py here"),
):
    """Show a job's final results — score, cost, prompt diff, and each agent's id. JOB_ID is printed by `optimize run`/`optimize list`."""
    config = get_config()
    try:
        prompts = [p for p in list_optimized_prompts(config) if p["trainingJobId"] == job_id]
    except (ApiError, RuntimeError) as exc:
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
        typer.echo(f"agent {p['id']}  {model_names}: {metrics}")

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
            code = get_agent_code(config, p["id"], latest["iteration"])
        except (ApiError, RuntimeError) as exc:
            typer.secho(f"  Could not download code for {model_names}: {exc}", fg=typer.colors.RED, err=True)
            continue

        out_path = output_dir / f"{p['id']}_{model_names.replace('/', '_')}.py"
        out_path.write_text(code["content"])
        typer.echo(f"  Saved to {out_path}")


def _ensure_downloaded(config: Config, agent_id: str, iteration: int | None, force: bool) -> Path:
    if not force and iteration is None and cache.is_cached(agent_id):
        return cache.agent_file_path(agent_id)
    try:
        code = get_agent_code(config, agent_id, iteration)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    return cache.write_agent_file(agent_id, code["content"])


@optimize_app.command()
def download(
    agent_id: str,
    iteration: int = typer.Option(None, "--iteration", help="Specific iteration; defaults to the latest"),
    force: bool = typer.Option(False, "--force", help="Re-download even if already cached"),
):
    """Download an agent's code (agent.py) so it can be run locally. AGENT_ID is printed by `optimize result`/`optimize status`."""
    config = get_config()
    path = _ensure_downloaded(config, agent_id, iteration, force)
    typer.echo(f"Downloaded agent code to {path}")


@optimize_app.command("run-local")
def run_local(
    agent_id: str,
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
    """Download (if needed) and run an agent's code locally against a single input. AGENT_ID is printed by `optimize result`/`optimize status`."""
    if not llm_api_key:
        fail(RuntimeError("No LLM API key provided. Pass --llm-api-key or set OPENROUTER_API_KEY."))
    config = get_config()
    path = _ensure_downloaded(config, agent_id, iteration, force_download)
    try:
        predictions = local_exec.run_agent(path, [input], llm_api_key)
    except local_exec.LocalExecError as exc:
        fail(exc)
    for prediction in predictions:
        typer.echo(prediction)


@optimize_app.command()
def infer(
    agent_id: str,
    input: list[str] = typer.Option(..., "--input", help="Input text to run inference on, repeatable (max 10)"),
):
    """Run hosted inference against a completed agent. AGENT_ID is printed by `optimize result`/`optimize status`. Prints a log id per input, for `optimize judgement`."""
    if not input:
        fail(RuntimeError("At least one --input is required"))
    if len(input) > MAX_INFER_INPUTS:
        fail(RuntimeError(f"At most {MAX_INFER_INPUTS} --input values are allowed"))
    config = get_config()
    try:
        result = infer_agent(config, agent_id, input)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"cold_start={result['cold_start']}  elapsed_ms={result['elapsed_ms']}")
    for inp, out, log_id in zip(input, result["outputs"], result["inference_log_ids"]):
        typer.echo(f"log {log_id}")
        typer.echo(f"  input:  {inp}")
        typer.echo(f"  output: {out}")


@optimize_app.command("infer-status")
def infer_status(agent_id: str):
    """Show the hosted inference sandbox status for an agent. AGENT_ID is printed by `optimize result`/`optimize status`."""
    config = get_config()
    try:
        status_result = get_infer_status(config, agent_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"status: {status_result['status']}")


@optimize_app.command()
def judgement(agent_id: str, log_id: str):
    """Show the judge's verdict for one inference call. AGENT_ID is printed by `optimize result`/`optimize status`; LOG_ID is printed by `optimize infer`."""
    config = get_config()
    try:
        result = get_judgement(config, agent_id, log_id)
    except (ApiError, RuntimeError) as exc:
        fail(exc)
    typer.echo(f"verdict: {result['judge_verdict']}")
    typer.echo(f"score: {result['judge_score']}")
    typer.echo(f"reasoning: {result['judge_reasoning']}")
