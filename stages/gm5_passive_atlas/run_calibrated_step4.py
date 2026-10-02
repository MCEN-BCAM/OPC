#!/usr/bin/env python3
"""Run the original GM4 engine with the GM4.5 age-specific Rm calibration."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from opc_atlas.calibration import age_from_cell_id, load_calibration, rm_ohm_cm2


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate calibrated GM4 outputs for the GM5 atlas")
    parser.add_argument("--gm4-root", type=Path, required=True,
                        help="Original 4-opc_step4_cohort_passive directory")
    parser.add_argument("--reconstruction-root", type=Path, required=True,
                        help="Validated GM3 root containing *_reconstruction.json")
    parser.add_argument("--output-root", type=Path, default=Path("gm4_calibrated_results"))
    parser.add_argument("--calibration", type=Path,
                        default=Path(__file__).parent / "config" / "calibrated_passive_parameters.json")
    parser.add_argument("--cells", nargs="*")
    parser.add_argument("--ages", nargs="*", choices=("P10", "P20", "P50"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--matrix-mode", choices=("none", "representative", "full"), default="representative")
    parser.add_argument("--representative-terminals", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    gm4_root = args.gm4_root.resolve()
    if not (gm4_root / "opc_data" / "cohort_passive.py").is_file():
        raise FileNotFoundError(f"Original GM4 engine not found at {gm4_root}")
    sys.path.insert(0, str(gm4_root))
    from opc_data.cohort_passive import aggregate, discover_reconstructions, run_one, write_json
    from opc_data.passive_neuron import PassiveParameters
    from opc_data.passive_protocols import CurrentStepProtocol, TransferProtocol

    calibration = load_calibration(args.calibration)
    paths = discover_reconstructions(args.reconstruction_root.resolve())
    if args.cells:
        selected = set(args.cells)
        paths = [p for p in paths if p.name.removesuffix("_reconstruction.json") in selected]
    if args.ages:
        selected_ages = set(args.ages)
        paths = [p for p in paths if age_from_cell_id(p.name.removesuffix("_reconstruction.json")) in selected_ages]
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be positive")
        paths = paths[:args.limit]
    if not paths:
        raise FileNotFoundError("No GM3 reconstructions selected")

    args.output_root.mkdir(parents=True, exist_ok=True)
    plan = []
    for path in paths:
        cell_id = path.name.removesuffix("_reconstruction.json")
        age = age_from_cell_id(cell_id)
        plan.append({"cell_id": cell_id, "age_group": age,
                     "rm_kohm_cm2": calibration["rm_kohm_cm2_by_age"][age],
                     "reconstruction": str(path.resolve())})
    write_json(args.output_root / "calibration_provenance.json", {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "gm4_root": str(gm4_root), "reconstruction_root": str(args.reconstruction_root.resolve()),
        "calibration_file": str(args.calibration.resolve()), "calibration": calibration,
        "matrix_mode": args.matrix_mode, "representative_terminals": args.representative_terminals,
        "n_cells": len(plan), "cells": plan,
    })
    print(f"Selected {len(paths)} reconstructions")
    for row in plan:
        print(f"  {row['cell_id']}: {row['rm_kohm_cm2']:.6g} kOhm cm2")
    if args.dry_run:
        return 0

    current, transfer, results = CurrentStepProtocol(), TransferProtocol(), []
    fixed = calibration["fixed_parameters"]
    for index, path in enumerate(paths, 1):
        cell_id = path.name.removesuffix("_reconstruction.json")
        age = age_from_cell_id(cell_id)
        rm = rm_ohm_cm2(cell_id, calibration)
        summary_path = args.output_root / "cells" / cell_id / f"{cell_id}_passive_summary.json"
        if summary_path.exists() and not args.force:
            result = json.loads(summary_path.read_text(encoding="utf-8"))
            print(f"[{index}/{len(paths)}] {cell_id}: cached")
        else:
            print(f"[{index}/{len(paths)}] {cell_id}: Rm={rm:.6g} ohm cm2", flush=True)
            params = PassiveParameters(rm_ohm_cm2=rm, ra_ohm_cm=float(fixed["ra_ohm_cm"]),
                cm_uF_cm2=float(fixed["cm_uF_cm2"]), e_pas_mV=float(fixed["e_pas_mV"]),
                process_diameter_um=float(fixed["process_diameter_um"]))
            result = run_one(path, args.output_root, params, current, transfer,
                             args.representative_terminals, args.matrix_mode)
        if result.get("status") != "failed":
            result["calibrated_rm_kohm_cm2"] = float(calibration["rm_kohm_cm2_by_age"][age])
            result["calibration_source"] = calibration["calibration_source"]
            write_json(summary_path, result)
        results.append(result)
    aggregate(results, args.output_root)
    failed = [r for r in results if r.get("status") == "failed"]
    print(f"Complete: {len(results)-len(failed)}; failed: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)

