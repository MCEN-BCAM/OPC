from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Mapping

from .utils import ensure_dir


def discover_cells(config: dict, config_path: Path) -> list[dict[str, str]]:
    configured_root = Path(config["reconstructions"]["root"])
    root = (configured_root if configured_root.is_absolute()
            else config_path.parent / configured_root).resolve()
    manifest = config["reconstructions"].get("manifest")
    rows: list[dict[str, str]] = []
    if manifest:
        manifest_path = (config_path.parent / manifest).resolve()
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                path = Path(row["path"])
                if not path.is_absolute():
                    path = root / path
                rows.append({"cell_id": row["cell_id"], "age": row["age"], "path": str(path)})
    else:
        pattern = config["reconstructions"].get("glob", "**/*.swc")
        for path in sorted(root.glob(pattern)):
            tokens = [part.upper() for part in path.parts]
            tokens.extend(path.stem.upper().split("_"))
            age = next((token for token in tokens if token in {"P10", "P20", "P50"}), "")
            if not age:
                raise ValueError(f"Cannot infer age (P10/P20/P50) from {path}")
            cell_id = (path.name.removesuffix("_reconstruction.json")
                       if path.name.endswith("_reconstruction.json") else path.stem)
            rows.append({"cell_id": cell_id, "age": age, "path": str(path.resolve())})
    if not rows:
        raise FileNotFoundError(f"No GM3 reconstructions found under {root}")
    invalid = [r for r in rows if r["age"] not in {"P10", "P20", "P50"}]
    if invalid:
        raise ValueError("Manifest ages must be P10, P20, or P50")
    missing = [r["path"] for r in rows if not Path(r["path"]).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing reconstruction: {missing[0]}")
    return rows


def write_csv(path: str | Path, rows: Iterable[Mapping], fieldnames: list[str] | None = None) -> None:
    rows = list(rows)
    if not rows and fieldnames is None:
        raise ValueError(f"Cannot infer columns for empty table {path}")
    ensure_dir(Path(path).parent)
    names = fieldnames or list(rows[0].keys())
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: str | Path, value: object) -> None:
    ensure_dir(Path(path).parent)
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
