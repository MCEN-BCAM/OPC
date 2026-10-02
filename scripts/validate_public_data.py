#!/usr/bin/env python3
"""Validate the public data bundle without modifying it."""
from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GITHUB_FILE_LIMIT = 100 * 1024 * 1024


def main() -> int:
    required = [
        DATA / "source/MariaDATA/NLResults/BasicAnalyses",
        DATA / "source/MariaDATA/NLTracings",
        DATA / "source/MariaDATA/MorphologyStats",
        DATA / "source/MariaDATA/MorphologyPlots/Morphology_Graphs_New.pxp.gz",
        DATA / "derived/gm3_validated/cells.zip",
        DATA / "inventory/ready_cells.csv",
    ]
    missing = [path.relative_to(ROOT) for path in required if not path.exists()]
    if missing:
        print("Missing required data paths:", *missing, sep="\n  - ", file=sys.stderr)
        return 1

    oversized = [
        path.relative_to(ROOT)
        for path in DATA.rglob("*")
        if path.is_file() and path.stat().st_size >= GITHUB_FILE_LIMIT
    ]
    if oversized:
        print("Files at or above GitHub's 100 MiB limit:", *oversized, sep="\n  - ", file=sys.stderr)
        return 1

    with (DATA / "inventory/ready_cells.csv").open(newline="", encoding="utf-8-sig") as handle:
        ready_rows = list(csv.DictReader(handle))
    if len(ready_rows) != 35:
        print(f"Expected 35 ready cells, found {len(ready_rows)}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(DATA / "derived/gm3_validated/cells.zip") as archive:
        cells = {
            name.split("/")[1]
            for name in archive.namelist()
            if name.startswith("cells/") and len(name.split("/")) > 2
        }
    if len(cells) != 35:
        print(f"Expected 35 GM3 cell directories, found {len(cells)}", file=sys.stderr)
        return 1

    file_count = sum(path.is_file() for path in (DATA / "source/MariaDATA").rglob("*"))
    print(f"Public data validation passed: {file_count} source files, 35 ready cells, 35 GM3 cells.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
