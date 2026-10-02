#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from opc_gm6.calibration import age_from_cell_id, validate_rm_mapping
from opc_gm6.cohort import aggregate, discover, provenance, run_one
from opc_gm6.io import write_json
from opc_gm6.passive_neuron import PassiveParameters
from opc_gm6.protocols import ProtocolGrid, SimulationParameters, SynapseParameters


def main() -> int:
    parser = argparse.ArgumentParser(description="GM6 calibrated cohort-wide OPC synaptic integration atlas")
    parser.add_argument("--reconstruction-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--config", default=str(Path(__file__).parent / "config/default_config.json"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ages", nargs="*", choices=("P10", "P20", "P50"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    rm_by_age = validate_rm_mapping(config["calibrated_rm_kohm_cm2_by_age"])
    common_passive = dict(config["passive"])
    common_passive.pop("rm_ohm_cm2", None)
    synapse = SynapseParameters(**config["synapse"])
    simulation = SimulationParameters(**config["simulation"])
    protocol_config = config["protocols"]
    grid = ProtocolGrid(**{**protocol_config,
        "temporal_intervals_ms": tuple(protocol_config["temporal_intervals_ms"]),
        "spatial_counts": tuple(protocol_config["spatial_counts"]),
        "site_quantiles": tuple(protocol_config["site_quantiles"])})

    paths = discover(Path(args.reconstruction_root))
    if args.ages:
        selected = set(args.ages)
        paths = [path for path in paths if age_from_cell_id(path.name.removesuffix("_reconstruction.json")) in selected]
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be positive")
        paths = paths[:args.limit]
    if not paths:
        raise FileNotFoundError("No GM3 reconstructions selected")

    output = Path(args.output_root); output.mkdir(parents=True, exist_ok=True)
    plan = []
    for path in paths:
        cell_id = path.name.removesuffix("_reconstruction.json")
        age = age_from_cell_id(cell_id)
        plan.append({"cell_id": cell_id, "age_group": age, "path": str(path.resolve()),
                     "rm_kohm_cm2": rm_by_age[age]})
    write_json(output / "run_plan.json", {"n_reconstructions": len(paths), "cells": plan, "config": config})
    base_parameters = PassiveParameters(rm_ohm_cm2=rm_by_age["P10"] * 1000.0, **common_passive)
    prov = provenance(base_parameters, synapse, simulation, grid)
    prov["calibration_source"] = config["calibration_source"]
    prov["calibrated_rm_kohm_cm2_by_age"] = rm_by_age
    prov["fixed_passive_parameters"] = common_passive
    prov.pop("passive_parameters", None)
    write_json(output / "provenance.json", prov)
    for row in plan:
        print(f"{row['cell_id']}: Rm={row['rm_kohm_cm2']:.6g} kOhm cm2")
    if args.dry_run:
        print(f"Dry run: {len(paths)} reconstructions")
        return 0

    results = []
    for path in paths:
        cell_id = path.name.removesuffix("_reconstruction.json")
        age = age_from_cell_id(cell_id)
        passive = PassiveParameters(rm_ohm_cm2=rm_by_age[age] * 1000.0, **common_passive)
        results.append(run_one(path, output, passive, synapse, simulation, grid))
    aggregate(results, output)
    complete = sum(result.get("status") == "complete" for result in results)
    failed = len(results) - complete
    print(f"GM6 complete: {complete} succeeded, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

