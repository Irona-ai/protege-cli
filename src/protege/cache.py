import os
from pathlib import Path

CACHE_DIR = Path(os.environ.get("PROTEGE_CACHE_DIR", Path.home() / ".cache" / "protege" / "optimize" / "agents"))


def agent_file_path(agent_id: str) -> Path:
    return CACHE_DIR / agent_id / "agent.py"


def is_cached(agent_id: str) -> bool:
    return agent_file_path(agent_id).exists()


def write_agent_file(agent_id: str, content: str) -> Path:
    path = agent_file_path(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path
