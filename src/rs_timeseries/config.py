"""Load project configuration from a YAML file and secrets from .env."""

from pathlib import Path
from typing import Optional   # ← add this import
import yaml
from dotenv import load_dotenv
import os

load_dotenv()


def load_config(config_path: str) -> dict:
    """Load configuration from a YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    return config


def get_ee_project() -> Optional[str]:   # ← change str | None to Optional[str]
    """Read the Earth Engine project ID from the environment."""
    return os.getenv("EE_PROJECT_ID")