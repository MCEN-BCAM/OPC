from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        config = json.load(handle)
    required = {"rm_values_kohm_cm2", "experimental_rin_mohm", "gm4", "reconstructions"}
    missing = required.difference(config)
    if missing:
        raise ValueError(f"Configuration missing: {', '.join(sorted(missing))}")
    values = [float(x) for x in config["rm_values_kohm_cm2"]]
    if values != [2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20]:
        raise ValueError("Stage 1 requires the frozen 11-point Rm sweep")
    config["rm_values_kohm_cm2"] = values
    return config


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_dir(path: str | Path) -> Path:
    result = Path(path)
    result.mkdir(parents=True, exist_ok=True)
    return result

