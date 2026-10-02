#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from opc_atlas.calibration import age_from_cell_id, load_calibration


REQUIRED_SUFFIXES = ("passive_summary.json", "structural_validation.json", "resting_test.json",
                     "current_step_summary.json", "soma_trace.csv", "attenuation_map.csv",
                     "bidirectional_transfer.csv", "transfer_matrix.csv")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate calibrated GM4 outputs before GM5")
    parser.add_argument("--step4-root", type=Path, required=True)
    parser.add_argument("--calibration", type=Path,
                        default=Path(__file__).parent / "config" / "calibrated_passive_parameters.json")
    parser.add_argument("--expected-cells", type=int, default=35)
    args = parser.parse_args()
    calibration = load_calibration(args.calibration)
    cell_dirs = sorted(p for p in (args.step4_root / "cells").iterdir() if p.is_dir())
    errors = []
    ages = {"P10": 0, "P20": 0, "P50": 0}
    for directory in cell_dirs:
        cell_id = directory.name; age = age_from_cell_id(cell_id); ages[age] += 1
        for suffix in REQUIRED_SUFFIXES:
            if not (directory / f"{cell_id}_{suffix}").is_file():
                errors.append(f"{cell_id}: missing {suffix}")
        summary_path = directory / f"{cell_id}_passive_summary.json"
        if summary_path.is_file():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            actual = float(summary.get("calibrated_rm_kohm_cm2", -1))
            expected = float(calibration["rm_kohm_cm2_by_age"][age])
            if abs(actual - expected) > 1e-10:
                errors.append(f"{cell_id}: Rm {actual} != {expected}")
    if len(cell_dirs) != args.expected_cells:
        errors.append(f"found {len(cell_dirs)} cells, expected {args.expected_cells}")
    if errors:
        raise ValueError("; ".join(errors[:10]))
    print(f"PASS: {len(cell_dirs)} calibrated cells; " + ", ".join(f"{k}={v}" for k,v in ages.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

