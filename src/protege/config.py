import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE_URL = "https://stg-studio.irona.ai/"

CONFIG_DIR = Path(os.environ.get("PROTEGE_CONFIG_DIR", Path.home() / ".config" / "protege"))
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class Config:
    api_key: str
    base_url: str


def load_config() -> Config | None:
    if not CONFIG_PATH.exists():
        return None
    data = json.loads(CONFIG_PATH.read_text())
    return Config(api_key=data["api_key"], base_url=data["base_url"])


def save_config(config: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"api_key": config.api_key, "base_url": config.base_url}, indent=2))
    os.chmod(CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)


def require_config() -> Config:
    config = load_config()
    if config is None:
        raise RuntimeError(
            "Not logged in. Run `protege login --api-key <your IronLabs API key>` first."
        )
    return config
