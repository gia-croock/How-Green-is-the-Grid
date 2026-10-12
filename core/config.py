import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path = PROJECT_ROOT / "config.toml") -> dict[str, Any]:
    """Read the settings from a TOML file."""
    with path.open("rb") as file:
        return tomllib.load(file)
