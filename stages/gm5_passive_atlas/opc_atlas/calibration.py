from __future__ import annotations

import json
from pathlib import Path


AGES = ("P10", "P20", "P50")


def age_from_cell_id(cell_id: str) -> str:
    matches = [age for age in AGES if cell_id.endswith("_" + age)]
    if len(matches) != 1:
        raise ValueError(f"Cannot determine P10/P20/P50 age from cell ID: {cell_id}")
    return matches[0]


def load_calibration(path: str | Path) -> dict:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    mapping = config.get("rm_kohm_cm2_by_age", {})
    if set(mapping) != set(AGES):
        raise ValueError("Calibration must define exactly P10, P20, and P50")
    if any(float(mapping[age]) <= 0 for age in AGES):
        raise ValueError("All calibrated Rm values must be positive")
    return config


def rm_ohm_cm2(cell_id: str, calibration: dict) -> float:
    return 1000.0 * float(calibration["rm_kohm_cm2_by_age"][age_from_cell_id(cell_id)])

