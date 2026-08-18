from typing import Any

import httpx

from ..config import Config

TIMEOUT = 30.0


class ApiError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def _headers(config: Config) -> dict[str, str]:
    return {"Authorization": f"Bearer {config.api_key}"}


def _unwrap(response: httpx.Response) -> Any:
    if response.status_code == 401:
        raise ApiError(401, "Invalid or expired API key. Run `protege login` again.")
    if response.status_code >= 400:
        try:
            message = response.json().get("message", response.text)
        except ValueError:
            message = response.text
        raise ApiError(response.status_code, message)
    return response.json()["data"]


def _request(
    config: Config,
    method: str,
    path: str,
    *,
    json_body: Any = None,
    params: dict[str, Any] | None = None,
    content: bytes | None = None,
) -> Any:
    url = f"{config.base_url.rstrip('/')}/api/v1{path}"
    headers = _headers(config)
    if content is not None:
        headers["Content-Type"] = "application/octet-stream"
    try:
        response = httpx.request(
            method,
            url,
            headers=headers,
            json=json_body,
            params=params,
            content=content,
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise ApiError(0, f"Could not reach {config.base_url}: {exc}") from exc
    return _unwrap(response)



def create_task(
    config: Config,
    zip_bytes: bytes,
    *,
    name: str | None = None,
    description: str | None = None,
    env_id: str | None = None,
) -> dict[str, Any]:
    params = {k: v for k, v in {"name": name, "description": description, "envId": env_id}.items() if v}
    return _request(config, "POST", "/tasks", content=zip_bytes, params=params)


def list_tasks(config: Config) -> list[dict[str, Any]]:
    return _request(config, "GET", "/tasks")


def get_task(config: Config, task_id: str) -> dict[str, Any]:
    return _request(config, "GET", f"/tasks/{task_id}")


def update_task(
    config: Config,
    task_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    env_id: str | None = None,
) -> dict[str, Any]:
    body = {k: v for k, v in {"name": name, "description": description, "envId": env_id}.items() if v is not None}
    return _request(config, "PATCH", f"/tasks/{task_id}", json_body=body)


def update_task_zip(config: Config, task_id: str, zip_bytes: bytes) -> dict[str, Any]:
    return _request(config, "PATCH", f"/tasks/{task_id}/zip", content=zip_bytes)


def update_task_dataset_md(config: Config, task_id: str, content: bytes) -> dict[str, Any]:
    return _request(config, "PATCH", f"/tasks/{task_id}/dataset-md", content=content)


def update_task_task_md(config: Config, task_id: str, content: bytes) -> dict[str, Any]:
    return _request(config, "PATCH", f"/tasks/{task_id}/task-md", content=content)


def delete_task(config: Config, task_id: str) -> None:
    _request(config, "DELETE", f"/tasks/{task_id}")



def create_env(config: Config, env_name: str, keys: dict[str, str]) -> dict[str, Any]:
    return _request(config, "POST", "/envs", json_body={"envName": env_name, "keys": keys})


def list_envs(config: Config) -> list[dict[str, Any]]:
    return _request(config, "GET", "/envs")


def get_env(config: Config, env_id: str) -> dict[str, Any]:
    return _request(config, "GET", f"/envs/{env_id}")


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
    return _request(config, "PATCH", f"/envs/{env_id}", json_body=body)


def delete_env(config: Config, env_id: str) -> None:
    _request(config, "DELETE", f"/envs/{env_id}")



def launch_job(config: Config, body: dict[str, Any]) -> dict[str, Any]:
    return _request(config, "POST", "/agent-optimizer/optimize", json_body=body)


def cancel_job(config: Config, job_id: str) -> dict[str, Any]:
    return _request(config, "POST", "/agent-optimizer/cancel", json_body={"job_id": job_id})


def list_training_jobs(config: Config) -> list[dict[str, Any]]:
    return _request(config, "GET", "/trainingjobs")


def list_optimized_prompts(config: Config) -> list[dict[str, Any]]:
    return _request(config, "GET", "/optimized-prompts")


def get_optimized_prompt(config: Config, optimized_prompt_id: str) -> dict[str, Any]:
    return _request(config, "GET", f"/optimized-prompts/{optimized_prompt_id}")


def get_agent_code(
    config: Config,
    optimized_prompt_id: str,
    iteration: int | None = None,
    *,
    file: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if iteration is not None:
        params["iteration"] = iteration
    if file:
        params["file"] = file
    return _request(
        config,
        "GET",
        f"/optimized-prompts/{optimized_prompt_id}/agent-code",
        params=params,
    )
