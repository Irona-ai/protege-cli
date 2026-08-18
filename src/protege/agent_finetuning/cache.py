import os
from pathlib import Path

CACHE_DIR = Path(os.environ.get("PROTEGE_CACHE_DIR", Path.home() / ".cache" / "protege" / "agent-finetuning" / "agents"))


def agent_file_path(optimized_prompt_id: str) -> Path:
    return CACHE_DIR / optimized_prompt_id / "agent.py"


def is_cached(optimized_prompt_id: str) -> bool:
    return agent_file_path(optimized_prompt_id).exists()


def write_agent_file(optimized_prompt_id: str, content: str) -> Path:
    path = agent_file_path(optimized_prompt_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path
