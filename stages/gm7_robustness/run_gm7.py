#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from opc_gm7.calibration import age_from_cell_id, config_for_age, validate_calibration
from opc_gm7.design import interaction_conditions, one_factor_conditions
from opc_gm7.runner import _write_json, aggregate, discover, provenance, run_cell


def main() -> int:
    parser = argparse.ArgumentParser(description="GM7 calibrated OPC sensitivity and robustness analysis")
    parser.add_argument("--reconstruction-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--config", default=str(Path(__file__).parent / "config/default_config.json"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ages", nargs="*", choices=("P10", "P20", "P50"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--enable-interactions", action="store_true")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    rm_by_age = validate_calibration(config)
    if args.enable_interactions:
        config.setdefault("interaction_design", {})["enabled"] = True

    paths = discover(Path(args.reconstruction_root))
    if args.ages:
        selected = set(args.ages)
        paths = [path for path in paths if age_from_cell_id(path.name.removesuffix("_reconstruction.json")) in selected]
    if args.limit is not None:
        if args.limit <= 0: raise ValueError("--limit must be positive")
        paths = paths[:args.limit]
    if not paths: raise FileNotFoundError("No GM3 reconstructions selected")

    plans = []
    for path in paths:
        cell_id = path.name.removesuffix("_reconstruction.json")
        age = age_from_cell_id(cell_id)
        age_config = config_for_age(config, age)
        conditions = one_factor_conditions(age_config) + interaction_conditions(age_config)
        for condition in conditions:
            condition["age_specific_baseline_rm_kohm_cm2"] = rm_by_age[age]
            if condition.get("factor") == "rm_ohm_cm2":
                condition["level_relative_to_age_baseline"] = float(condition["level"]) / (rm_by_age[age] * 1000.0)
        plans.append({"path": path, "cell_id": cell_id, "age_group": age,
                      "baseline_rm_kohm_cm2": rm_by_age[age], "config": age_config,
                      "conditions": conditions})
    counts = {len(plan["conditions"]) for plan in plans}
    if len(counts) != 1: raise ValueError("All selected cells must have the same condition count")
    n_conditions = counts.pop()
    output = Path(args.output_root); output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "run_plan.json", {
        "n_reconstructions": len(plans), "n_conditions_per_cell": n_conditions,
        "estimated_cell_condition_runs": len(plans) * n_conditions,
        "calibrated_rm_kohm_cm2_by_age": rm_by_age,
        "cells": [{"cell_id": p["cell_id"], "age_group": p["age_group"],
                   "baseline_rm_kohm_cm2": p["baseline_rm_kohm_cm2"],
                   "path": str(p["path"].resolve())} for p in plans]})
    prov = provenance(config, n_conditions)
    prov["calibration_source"] = config["calibration_source"]
    prov["calibrated_rm_kohm_cm2_by_age"] = rm_by_age
    prov["rm_sensitivity_design"] = "multipliers relative to each age-specific calibrated baseline"
    prov["spatial_normalisation"] = "exact matched-site isolated EPSP denominator"
    _write_json(output / "provenance.json", prov)
    for plan in plans:
        print(f"{plan['cell_id']}: baseline Rm={plan['baseline_rm_kohm_cm2']:.6g} kOhm cm2")
    if args.dry_run:
        print(f"Dry run: {len(plans)} cells x {n_conditions} conditions = {len(plans)*n_conditions} cell-condition runs")
        return 0
    results = [run_cell(plan["path"], output, plan["config"], plan["conditions"]) for plan in plans]
    aggregate(results, output)
    failed = sum(len(result["failures"]) for result in results)
    print(f"GM7 complete: {len(results)} cells processed; {failed} failed conditions")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
