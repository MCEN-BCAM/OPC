
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import re


@dataclass(frozen=True)
class FileRecord:
    path: str
    filename: str
    family: str
    animal: str
    tracing: str
    age: str | None
    cell_id: str
    subtype: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _normalise_tracing(value: str) -> str:
    value = value.lower().strip("_- ")
    aliases = {"top": "up", "upper": "up"}
    return aliases.get(value, value)


def parse_filename(path: Path) -> FileRecord | None:
    name = path.name
    stem = path.stem
    low = stem.lower()

    family = None
    subtype = None
    if "angles" in low:
        family = "angles"
    elif "_nn_2_5" in low:
        family = "nearest_neighbour"
        subtype = "2_5"
    elif "_nn" in low:
        family = "nearest_neighbour"
        subtype = "standard"
    elif "sholl" in low:
        family = "sholl"
    elif "aligned" in low:
        family = "basic"
    else:
        return None

    match = re.match(r"^(NX\d+)_([^_]+)", stem, flags=re.IGNORECASE)
    if not match:
        return None

    animal = match.group(1).upper()
    tracing = _normalise_tracing(match.group(2))

    age_match = re.search(r"(?:^|_)(p10|p20|p50)(?:_|$)", low)
    age = age_match.group(1).upper() if age_match else None

    # Age is often encoded only in the containing directory for angle/NN files.
    if age is None:
        for part in path.parts:
            if part.lower() in {"p10", "p20", "p50"}:
                age = part.upper()
                break

    cell_id = f"{animal}_{tracing}" + (f"_{age}" if age else "")
    return FileRecord(
        path=str(path),
        filename=name,
        family=family,
        animal=animal,
        tracing=tracing,
        age=age,
        cell_id=cell_id,
        subtype=subtype,
    )


def discover_files(data_dir: str | Path) -> list[FileRecord]:
    data_dir = Path(data_dir)
    records: list[FileRecord] = []
    for path in sorted(data_dir.rglob("*")):
        if path.suffix.lower() not in {".xls", ".xlsx"}:
            continue
        record = parse_filename(path)
        if record is not None:
            records.append(record)
    return records
