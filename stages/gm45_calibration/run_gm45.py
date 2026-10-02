#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from opc_gm45.calibration import summarize
from opc_gm45.gm4_adapter import GM4Adapter
from opc_gm45.io import discover_cells, read_csv, write_csv, write_json
from opc_gm45.plotting import make_figures
from opc_gm45.utils import file_sha256, load_config


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="GM4.5 Stage 1 passive Rm calibration")
    result.add_argument("--config", default="config/calibration_config.json")
    result.add_argument("--output-root", default="results")
    result.add_argument("--mode", choices=("pilot", "cohort", "extend", "analyze", "validate"), default="cohort")
    result.add_argument("--input-csv", help="Analyze an existing Rin_vs_Rm.csv without running GM4")
    result.add_argument("--reconstruction-root",
                        help="Override reconstructions.root from the JSON configuration")
    result.add_argument("--gm4-root",
                        help="Override gm4.path from the JSON configuration")
    result.add_argument("--ages", nargs="+", choices=("P10", "P20", "P50"),
                        help="Age groups to simulate in extension mode")
    result.add_argument("--rm-values", nargs="+", type=float,
                        help="Additional Rm values (kOhm cm2) in extension mode")
    result.add_argument("--force", action="store_true", help="Replace an existing Rin_vs_Rm.csv")
    return result


def validate(rows: list[dict], config: dict, expected_cells: int | None = None,
             allow_extensions: bool = True) -> None:
    rms = set(config["rm_values_kohm_cm2"])
    seen = {(r["cell_id"], r["age"], float(r["rm_kohm_cm2"])) for r in rows}
    cells = {(r["cell_id"], r["age"]) for r in rows}
    expected = {(cell, age, rm) for cell, age in cells for rm in rms}
    if len(rows) != len(seen):
        raise ValueError("Duplicate cell/age/Rm rows detected")
    if (not allow_extensions and seen != expected) or (allow_extensions and not expected.issubset(seen)):
        raise ValueError(f"Base 11-point sweep is incomplete: {len(rows)} rows, base requires {len(expected)}")
    if expected_cells is not None and len(cells) != expected_cells:
        raise ValueError(f"Found {len(cells)} cells; configuration requires {expected_cells}")
    ages = {age for _, age in cells}
    if ages != {"P10", "P20", "P50"} and len(cells) > 1:
        raise ValueError(f"Full cohort must include P10, P20, P50; found {sorted(ages)}")


def main() -> int:
    args = parser().parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    if args.reconstruction_root:
        config["reconstructions"]["root"] = str(Path(args.reconstruction_root).resolve())
    if args.gm4_root:
        config["gm4"]["path"] = str(Path(args.gm4_root).resolve())
    output = Path(args.output_root).resolve()
    population, figures = output / "population", output / "figures"
    raw_path = population / "Rin_vs_Rm.csv"
    if args.input_csv:
        raw_path = Path(args.input_csv).resolve()
    if args.mode == "extend":
        if not args.input_csv or not args.ages or not args.rm_values:
            raise ValueError("extend requires --input-csv, --ages, and --rm-values")
        source = Path(args.input_csv).resolve()
        if not source.is_file():
            raise FileNotFoundError(f"No sweep table at {source}")
        existing = read_csv(source)
        validate(existing, config, config.get("expected_cell_count"))
        cells = [cell for cell in discover_cells(config, config_path) if cell["age"] in set(args.ages)]
        if not cells:
            raise ValueError("No reconstructions matched --ages")
        extra_rms = sorted(set(float(value) for value in args.rm_values))
        if any(value <= 0 for value in extra_rms):
            raise ValueError("All extension Rm values must be positive")
        existing_keys = {(r["cell_id"], r["age"], float(r["rm_kohm_cm2"])) for r in existing}
        planned = [(cell, rm) for cell in cells for rm in extra_rms
                   if (cell["cell_id"], cell["age"], rm) not in existing_keys]
        if not planned:
            raise ValueError("All requested extension simulations already exist")
        if raw_path.exists() and raw_path != source and not args.force:
            raise FileExistsError(f"Refusing to overwrite {raw_path}; pass --force")
        adapter = GM4Adapter(config["gm4"], config_path)
        added = []
        for index, (cell, rm) in enumerate(planned, 1):
            print(f"[{index}/{len(planned)}] {cell['age']} {cell['cell_id']} Rm={rm:g}", flush=True)
            result = adapter.run(cell, rm)
            added.append({"cell_id": cell["cell_id"], "age": cell["age"], "reconstruction_path": cell["path"],
                          "rm_kohm_cm2": rm, "rin_mohm": result["rin_mohm"],
                          "tau_ms": result.get("tau_ms", ""), "steady_state_mv": result.get("steady_state_mv", "")})
        rows = existing + added
        raw_path = population / "Rin_vs_Rm.csv"
        if raw_path.resolve() == source.resolve():
            raise ValueError("Extension output must differ from the source; choose a new --output-root")
        write_csv(raw_path, rows)
    elif args.mode in {"pilot", "cohort"} and not args.input_csv:
        cells = discover_cells(config, config_path)
        if args.mode == "pilot":
            cells = cells[:1]
        if raw_path.exists() and not args.force:
            raise FileExistsError(f"Refusing to overwrite {raw_path}; pass --force")
        adapter = GM4Adapter(config["gm4"], config_path)
        rows = []
        total = len(cells) * len(config["rm_values_kohm_cm2"])
        for index, (cell, rm) in enumerate(((c, r) for c in cells for r in config["rm_values_kohm_cm2"]), 1):
            print(f"[{index}/{total}] {cell['age']} {cell['cell_id']} Rm={rm:g}", flush=True)
            result = adapter.run(cell, rm)
            rows.append({"cell_id": cell["cell_id"], "age": cell["age"], "reconstruction_path": cell["path"],
                         "rm_kohm_cm2": rm, "rin_mohm": result["rin_mohm"],
                         "tau_ms": result.get("tau_ms", ""), "steady_state_mv": result.get("steady_state_mv", "")})
        write_csv(raw_path, rows)
    elif not raw_path.is_file():
        raise FileNotFoundError(f"No sweep table at {raw_path}")
    rows = read_csv(raw_path)
    expected_cells = config.get("expected_cell_count") if args.mode in {"cohort", "validate"} else None
    validate(rows, config, expected_cells, allow_extensions=True)
    if args.mode == "validate":
        counts = {}
        for age in ("P10", "P20", "P50"):
            counts[age] = len({float(r["rm_kohm_cm2"]) for r in rows if r["age"] == age})
        print(f"PASS: {len({r['cell_id'] for r in rows})} cells, {len(rows)} rows; "
              + ", ".join(f"{age}={counts[age]} Rm conditions" for age in counts))
        return 0
    summary, best, comparison = summarize(rows, config["experimental_rin_mohm"])
    write_csv(population / "CalibrationSummary.csv", summary)
    write_csv(population / "BestFitParameters.csv", best)
    write_csv(population / "ModelExperimentComparison.csv", comparison)
    make_figures(summary, config["experimental_rin_mohm"], figures)
    write_json(output / "run_metadata.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
               "python": platform.python_version(), "config": str(config_path), "config_sha256": file_sha256(config_path),
               "source_rin_csv": str(raw_path), "n_rows": len(rows), "argv": sys.argv})
    print(f"PASS: wrote calibration tables and figures to {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
