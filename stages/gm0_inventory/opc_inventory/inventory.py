from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

AGE_RE = re.compile(r"^P(10|20|50)$", re.IGNORECASE)
CELL_RE = re.compile(r"^(NX\d+)(?:_?)([A-Za-z]+|\d+)$", re.IGNORECASE)
NX_RE = re.compile(r"NX\d+", re.IGNORECASE)

# Safe spelling-only normalisations. Biological identity is not inferred here.
SAFE_ALIASES = {
    "NX45LOW": "NX45_low",
    "NX45UP": "NX45_up",
    "NX93LOW": "NX93_low",
    "NX93UP": "NX93_up",
    "NX93TOP": "NX93_up",
}

@dataclass
class CellRecord:
    cell_id: str
    animal_id: str
    cell_label: str
    age_group: str
    basic_analysis: str = ""
    sholl: str = ""
    angles: str = ""
    nearest_neighbour: str = ""
    nearest_neighbour_2_5: str = ""
    tracing_candidates: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    status: str = ""

    def finalise(self) -> None:
        required = {
            "basic_analysis": self.basic_analysis,
            "sholl": self.sholl,
            "angles": self.angles,
            "nearest_neighbour": self.nearest_neighbour,
        }
        self.missing_required = [name for name, value in required.items() if not value]
        if self.missing_required:
            self.status = "incomplete"
        elif self.warnings:
            self.status = "complete_with_warnings"
        else:
            self.status = "complete"


def _age_from_path(path: Path) -> str | None:
    for part in path.parts:
        if AGE_RE.match(part):
            return part.upper()
    return None


def _canonical_cell(raw: str) -> str | None:
    token = raw.strip().replace("-", "_")
    upper = token.upper().replace("_", "")
    if upper in SAFE_ALIASES:
        return SAFE_ALIASES[upper]
    match = CELL_RE.match(token)
    if not match:
        return None
    animal = match.group(1).upper()
    label = match.group(2).lower() if match.group(2).isalpha() else match.group(2)
    return f"{animal}_{label}"


def _cell_from_filename(path: Path, family: str) -> str | None:
    name = path.stem
    patterns = {
        "basic_analysis": r"^(.*?)_p(?:10|20|50)_0aligned(?:1|_xx)$",
        "sholl": r"^(.*?)_Sholl2_5(?:_STree)?$",
        "angles": r"^(.*?)_angles$",
        "nearest_neighbour_2_5": r"^(.*?)_NN_2_5$",
        "nearest_neighbour": r"^(.*?)_NN$",
    }
    match = re.match(patterns[family], name, flags=re.IGNORECASE)
    return _canonical_cell(match.group(1)) if match else None


def _animal_and_label(cell_id: str) -> tuple[str, str]:
    animal, label = cell_id.split("_", 1)
    return animal, label


def _collect_files(data_root: Path) -> tuple[dict[tuple[str, str], dict[str, list[Path]]], list[dict]]:
    results_root = data_root / "NLResults"
    families = {
        "basic_analysis": results_root / "BasicAnalyses",
        "sholl": results_root / "Sholl",
        "angles": results_root / "Angles",
        "nearest_neighbour": results_root / "NearestNeighbour",
    }
    found: dict[tuple[str, str], dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    unparsed: list[dict] = []

    for base_family, folder in families.items():
        if not folder.exists():
            unparsed.append({"family": base_family, "path": str(folder), "reason": "folder_missing"})
            continue
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.name.startswith(".") or "__MACOSX" in path.parts:
                continue
            if path.suffix.lower() not in {".xls", ".xlsx"}:
                continue
            if "Unused" in path.parts:
                continue
            family = base_family
            if base_family == "nearest_neighbour" and path.stem.lower().endswith("_nn_2_5"):
                family = "nearest_neighbour_2_5"
            age = _age_from_path(path)
            cell = _cell_from_filename(path, family)
            if not age or not cell:
                unparsed.append({"family": family, "path": str(path.relative_to(data_root)), "reason": "name_or_age_unparsed"})
                continue
            found[(age, cell)][family].append(path.relative_to(data_root))
    return found, unparsed


def _collect_tracings(data_root: Path) -> dict[tuple[str, str], list[str]]:
    tracing_root = data_root / "NLTracings"
    by_animal: dict[tuple[str, str], list[str]] = defaultdict(list)
    if not tracing_root.exists():
        return by_animal
    for path in sorted(tracing_root.rglob("*.DAT")):
        age = _age_from_path(path)
        animal_match = NX_RE.search(path.name)
        if age and animal_match:
            animal = animal_match.group(0).upper()
            by_animal[(age, animal)].append(str(path.relative_to(data_root)))
    return by_animal


def build_inventory(data_root: Path | str) -> dict:
    root = Path(data_root).expanduser().resolve()
    if root.name != "MariaDATA" and (root / "MariaDATA").is_dir():
        root = root / "MariaDATA"
    if not (root / "NLResults").is_dir():
        raise FileNotFoundError(f"Could not find NLResults below {root}")

    found, unparsed = _collect_files(root)
    tracings = _collect_tracings(root)
    records: list[CellRecord] = []

    for (age, cell_id), families in sorted(found.items()):
        animal, label = _animal_and_label(cell_id)
        record = CellRecord(cell_id=cell_id, animal_id=animal, cell_label=label, age_group=age)
        for family in ("basic_analysis", "sholl", "angles", "nearest_neighbour", "nearest_neighbour_2_5"):
            paths = families.get(family, [])
            if len(paths) == 1:
                setattr(record, family, str(paths[0]))
            elif len(paths) > 1:
                setattr(record, family, str(paths[0]))
                record.warnings.append(f"duplicate_{family}:{len(paths)}")
        candidates = tracings.get((age, animal), [])
        record.tracing_candidates = candidates
        if not candidates:
            record.warnings.append("no_tracing_candidate")
        elif len(candidates) > 1:
            record.warnings.append(f"multiple_tracing_candidates:{len(candidates)}")
        record.finalise()
        records.append(record)

    # Cross-family anomaly detection: files whose animal exists but cell label differs.
    index_by_age_animal: dict[tuple[str, str], list[CellRecord]] = defaultdict(list)
    for rec in records:
        index_by_age_animal[(rec.age_group, rec.animal_id)].append(rec)
    anomalies: list[dict] = []
    for rec in records:
        if rec.status == "incomplete":
            siblings = index_by_age_animal[(rec.age_group, rec.animal_id)]
            same_label = [
                other for other in records
                if other.age_group == rec.age_group
                and other.cell_label == rec.cell_label
                and other.cell_id != rec.cell_id
                and other.status == "incomplete"
            ]
            for missing in rec.missing_required:
                donors = [s for s in siblings if getattr(s, missing) and s.cell_id != rec.cell_id]
                candidates = donors[:]
                # A second conservative heuristic catches likely animal-number typos
                # such as NX80_16 versus NX89_16, but only reports them.
                candidates.extend(
                    s for s in same_label
                    if getattr(s, missing) and s not in candidates
                )
                if candidates:
                    anomalies.append({
                        "cell_id": rec.cell_id,
                        "age_group": rec.age_group,
                        "missing_family": missing,
                        "same_animal_candidates": [d.cell_id for d in candidates],
                        "note": "Possible filename mismatch; manual confirmation required.",
                    })

    counts = Counter(rec.status for rec in records)
    by_age = defaultdict(Counter)
    for rec in records:
        by_age[rec.age_group][rec.status] += 1
        by_age[rec.age_group]["total"] += 1

    return {
        "schema_version": "1.0",
        "dataset_root": str(root),
        "required_families": ["basic_analysis", "sholl", "angles", "nearest_neighbour"],
        "optional_families": ["nearest_neighbour_2_5", "tracing_candidates"],
        "summary": {
            "total_cells": len(records),
            "complete": counts["complete"],
            "complete_with_warnings": counts["complete_with_warnings"],
            "incomplete": counts["incomplete"],
            "by_age": {age: dict(values) for age, values in sorted(by_age.items())},
        },
        "cells": [asdict(rec) for rec in records],
        "unparsed_files": unparsed,
        "potential_name_mismatches": anomalies,
    }


def _flatten_record(rec: dict) -> dict:
    row = dict(rec)
    row["tracing_candidates"] = " | ".join(rec["tracing_candidates"])
    row["missing_required"] = " | ".join(rec["missing_required"])
    row["warnings"] = " | ".join(rec["warnings"])
    return row


def write_reports(inventory: dict, output_dir: Path | str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dataset_inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    rows = [_flatten_record(rec) for rec in inventory["cells"]]
    if rows:
        with (out / "cell_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    ready = [row for row in rows if row["status"] in {"complete", "complete_with_warnings"}]
    if ready:
        with (out / "ready_cells.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(ready[0].keys()))
            writer.writeheader()
            writer.writerows(ready)

    summary = inventory["summary"]
    lines = [
        "# OPC dataset readiness report",
        "",
        f"Dataset root: `{inventory['dataset_root']}`",
        "",
        "## Overall",
        "",
        f"- Total discovered cell identifiers: **{summary['total_cells']}**",
        f"- Complete without warnings: **{summary['complete']}**",
        f"- Complete with warnings: **{summary['complete_with_warnings']}**",
        f"- Incomplete: **{summary['incomplete']}**",
        "",
        "## By developmental age",
        "",
        "| Age | Total | Complete | Complete with warnings | Incomplete |",
        "|---|---:|---:|---:|---:|",
    ]
    for age, values in summary["by_age"].items():
        lines.append(
            f"| {age} | {values.get('total', 0)} | {values.get('complete', 0)} | "
            f"{values.get('complete_with_warnings', 0)} | {values.get('incomplete', 0)} |"
        )
    lines.extend(["", "## Incomplete cells", ""])
    incomplete = [r for r in inventory["cells"] if r["status"] == "incomplete"]
    if incomplete:
        lines.extend(["| Age | Cell | Missing | Warnings |", "|---|---|---|---|"])
        for rec in incomplete:
            lines.append(
                f"| {rec['age_group']} | {rec['cell_id']} | {', '.join(rec['missing_required'])} | "
                f"{', '.join(rec['warnings']) or '—'} |"
            )
    else:
        lines.append("None.")
    lines.extend(["", "## Potential filename mismatches", ""])
    anomalies = inventory["potential_name_mismatches"]
    if anomalies:
        for item in anomalies:
            lines.append(
                f"- `{item['cell_id']}` ({item['age_group']}), missing `{item['missing_family']}`; "
                f"same-animal candidate(s): {', '.join(item['same_animal_candidates'])}."
            )
    else:
        lines.append("None detected.")
    lines.extend(["", "## Notes", "", "- Neurolucida `.DAT` tracings are treated as provenance candidates, not required inputs.", "- Multiple tracing candidates are expected when an animal contributed more than one recorded cell.", "- The software never silently merges biologically ambiguous identifiers.", ""])
    (out / "readiness_report.md").write_text("\n".join(lines), encoding="utf-8")
