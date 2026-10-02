from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def discover_cell_directories(step4_root: Path) -> list[Path]:
    cells = step4_root / "cells"
    if not cells.is_dir():
        raise FileNotFoundError(f"Step-4 cells directory not found: {cells}")
    return sorted(p for p in cells.iterdir() if p.is_dir())


def load_cell_bundle(cell_dir: Path) -> dict[str, Any]:
    cell_id = cell_dir.name
    required = {
        "manifest": cell_dir / "manifest.json",
        "summary": cell_dir / f"{cell_id}_passive_summary.json",
        "structural": cell_dir / f"{cell_id}_structural_validation.json",
        "rest": cell_dir / f"{cell_id}_resting_test.json",
        "step": cell_dir / f"{cell_id}_current_step_summary.json",
        "trace": cell_dir / f"{cell_id}_soma_trace.csv",
        "attenuation": cell_dir / f"{cell_id}_attenuation_map.csv",
        "bidirectional": cell_dir / f"{cell_id}_bidirectional_transfer.csv",
        "matrix": cell_dir / f"{cell_id}_transfer_matrix.csv",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing Step-4 outputs:\n" + "\n".join(missing))
    return {
        "cell_id": cell_id,
        "manifest": read_json(required["manifest"]),
        "summary": read_json(required["summary"]),
        "structural": read_json(required["structural"]),
        "rest": read_json(required["rest"]),
        "step": read_json(required["step"]),
        "trace": pd.read_csv(required["trace"]),
        "attenuation": pd.read_csv(required["attenuation"]),
        "bidirectional": pd.read_csv(required["bidirectional"]),
        "matrix": pd.read_csv(required["matrix"]),
    }
