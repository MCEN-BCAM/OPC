#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from opc_gm6.calibration import age_from_cell_id, validate_rm_mapping


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate calibrated GM6 cohort")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "config/default_config.json")
    parser.add_argument("--expected-cells", type=int, default=35)
    parser.add_argument("--tolerance", type=float, default=1e-10)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    mapping = validate_rm_mapping(config["calibrated_rm_kohm_cm2_by_age"])
    cell_dirs = sorted(p for p in (args.output_root / "cells").iterdir() if p.is_dir())
    errors = []; spatial_rows = 0; ages = {"P10": 0, "P20": 0, "P50": 0}
    for directory in cell_dirs:
        cell_id = directory.name; age = age_from_cell_id(cell_id); ages[age] += 1
        summary_path = directory / f"{cell_id}_synaptic_summary.json"
        protocol_path = directory / f"{cell_id}_synaptic_protocols.csv"
        manifest_path = directory / "manifest.json"
        for path in (summary_path, protocol_path, manifest_path):
            if not path.is_file(): errors.append(f"{cell_id}: missing {path.name}")
        if not summary_path.is_file() or not protocol_path.is_file(): continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("status") != "complete": errors.append(f"{cell_id}: incomplete")
        expected = mapping[age]; actual = float(summary.get("calibrated_rm_kohm_cm2", -1))
        if not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-10):
            errors.append(f"{cell_id}: Rm {actual} != {expected}")
        with protocol_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 12: errors.append(f"{cell_id}: {len(rows)} protocol rows, expected 12")
        for row in rows:
            if row.get("protocol") != "spatial": continue
            spatial_rows += 1
            observed=float(row["soma_epsp_mV"]); predicted=float(row["linear_prediction_mV"]); ratio=float(row["summation_ratio"])
            if not math.isclose(ratio, observed/predicted, rel_tol=args.tolerance, abs_tol=args.tolerance):
                errors.append(f"{cell_id}: inconsistent spatial ratio")
            if int(float(row["n_synapses"])) == 1 and not math.isclose(ratio, 1.0, rel_tol=args.tolerance, abs_tol=args.tolerance):
                errors.append(f"{cell_id}: N=1 spatial ratio {ratio}")
    if len(cell_dirs) != args.expected_cells: errors.append(f"found {len(cell_dirs)} cells, expected {args.expected_cells}")
    if spatial_rows != len(cell_dirs)*4: errors.append(f"found {spatial_rows} spatial rows, expected {len(cell_dirs)*4}")
    if errors: raise ValueError("; ".join(errors[:12]))
    print(f"PASS: {len(cell_dirs)} calibrated cells, {spatial_rows} spatial rows; " + ", ".join(f"{k}={v}" for k,v in ages.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
