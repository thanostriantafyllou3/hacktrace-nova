"""Load config from YAML file. Returns a dict."""

import yaml
from pathlib import Path


def _default_config_path() -> Path:
    """Resolve config.yaml relative to project root (parent of src/)."""
    return Path(__file__).resolve().parent.parent.parent / "config.yaml"


def load_config(path: str | Path | None = None) -> dict:
    """Load config from YAML. If path is None, uses config.yaml in project root."""
    if path is None:
        path = _default_config_path()
    else:
        path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
