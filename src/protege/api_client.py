from typing import Any

import httpx

from .config import Config

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


def request(
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
