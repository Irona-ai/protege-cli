import asyncio
import importlib.util
from pathlib import Path


class LocalExecError(RuntimeError):
    pass


def _load_agent_module(agent_path: Path):
    spec = importlib.util.spec_from_file_location("agent", agent_path)
    if spec is None or spec.loader is None:
        raise LocalExecError(f"Could not load agent module from {agent_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_agent(agent_path: Path, inputs: list[str], llm_api_key: str) -> list[str]:
    module = _load_agent_module(agent_path)
    if not hasattr(module, "run_batch"):
        raise LocalExecError(
            f"{agent_path} does not define run_batch(inputs, api_key) — cannot run it."
        )

    result = asyncio.run(module.run_batch(inputs, llm_api_key))
    predictions = result[0] if isinstance(result, tuple) else result
    return list(predictions)
