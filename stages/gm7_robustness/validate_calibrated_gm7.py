#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

from opc_gm7.calibration import age_from_cell_id, validate_calibration


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate calibrated GM7 one-factor cohort")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "config/default_config.json")
    parser.add_argument("--expected-cells", type=int, default=35)
    parser.add_argument("--expected-conditions", type=int, default=36)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8")); mapping = validate_calibration(config)
    cell_dirs = sorted(p for p in (args.output_root / "cells").iterdir() if p.is_dir())
    errors=[]; all_rows=[]; ages=Counter()
    expected_multipliers=sorted(float(x) for x in config["one_factor_sweeps"]["rm_multiplier"])
    for directory in cell_dirs:
        cell_id=directory.name; age=age_from_cell_id(cell_id); ages[age]+=1
        manifest_path=directory/"manifest.json"; table=directory/"sensitivity_results.csv"; failed=directory/"failed_conditions.csv"
        for path in (manifest_path,table,failed):
            if not path.is_file(): errors.append(f"{cell_id}: missing {path.name}")
        if not manifest_path.is_file() or not table.is_file(): continue
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status")!="complete" or int(manifest.get("n_failed",-1))!=0: errors.append(f"{cell_id}: incomplete/failed manifest")
        if not math.isclose(float(manifest.get("baseline_rm_kohm_cm2",-1)),mapping[age],rel_tol=0,abs_tol=1e-10): errors.append(f"{cell_id}: incorrect baseline Rm")
        with table.open(newline="",encoding="utf-8") as handle: rows=list(csv.DictReader(handle))
        all_rows.extend(rows)
        if len(rows)!=args.expected_conditions: errors.append(f"{cell_id}: {len(rows)} conditions")
        baseline=[r for r in rows if r["condition_id"]=="baseline"]
        if len(baseline)!=1 or not math.isclose(float(baseline[0]["rm_ohm_cm2"]),mapping[age]*1000,rel_tol=0,abs_tol=1e-8): errors.append(f"{cell_id}: invalid baseline row")
        rm_rows=[r for r in rows if r["factor"]=="rm_ohm_cm2"]
        multipliers=sorted(float(r["rm_ohm_cm2"])/(mapping[age]*1000) for r in rm_rows)
        if len(multipliers)!=len(expected_multipliers) or any(not math.isclose(a,b,rel_tol=1e-12) for a,b in zip(multipliers,expected_multipliers)): errors.append(f"{cell_id}: invalid Rm multiplier sweep")
        if any(not math.isclose(float(r["spatial_ratio_n1"]),1.0,rel_tol=1e-10,abs_tol=1e-10) for r in rows): errors.append(f"{cell_id}: spatial N=1 normalization failure")
        if failed.is_file() and failed.stat().st_size>2: errors.append(f"{cell_id}: failed condition table is not empty")
    if len(cell_dirs)!=args.expected_cells: errors.append(f"found {len(cell_dirs)} cells, expected {args.expected_cells}")
    expected_rows=args.expected_cells*args.expected_conditions
    if len(all_rows)!=expected_rows: errors.append(f"found {len(all_rows)} condition rows, expected {expected_rows}")
    if errors: raise ValueError("; ".join(errors[:12]))
    print(f"PASS: {len(cell_dirs)} calibrated cells, {len(all_rows)} condition rows; " + ", ".join(f"{a}={ages[a]}" for a in ('P10','P20','P50')))
    return 0


if __name__=="__main__": raise SystemExit(main())
