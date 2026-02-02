"""Load (claim, truth) pairs from CSV."""

import csv
from pathlib import Path
import random


def _project_root() -> Path:
    """Project root (parent of src/)."""
    return Path(__file__).resolve().parent.parent.parent


def load_pairs(config: dict) -> list[dict[str, str]]:
    """
    Load claim/truth pairs from CSV based on config.

    Returns:
        List of {"claim": str, "truth": str}
    """
    data_cfg = config.get("data", {})
    source = data_cfg.get("source", "")
    path = _project_root() / source
    claim_col = data_cfg.get("claim_col", "claim")
    truth_col = data_cfg.get("truth_col", "truth")
    pair_ids = data_cfg.get("pair_ids", "random-5")
    seed = data_cfg.get("seed", 42)

    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if isinstance(pair_ids, list):
        pass
    elif isinstance(pair_ids, str):
        if pair_ids.startswith("random-"):
            n = int(pair_ids.split("-")[1])
            n = min(n, len(rows))
            print(f"Sampling {n} pairs from {len(rows)} pairs")
            random.seed(seed)
            pair_ids = random.sample(list(range(len(rows))), n)
        elif pair_ids.strip().lower() == "all":
            pair_ids = list(range(len(rows)))
        else:
            raise ValueError(f"Invalid pair_ids: {pair_ids}")

    result = []
    for i in pair_ids:
        if i >= len(rows):
            raise IndexError(f"pair_ids index {i} out of range (max {len(rows) - 1})")
        result.append({"id": i, "claim": rows[i][claim_col], "truth": rows[i][truth_col]})
    return result
