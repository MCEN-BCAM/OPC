#!/usr/bin/env python3
"""Configuration-driven GM0-GM7 orchestration for the calibrated workflow."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
STAGE_CHOICES = ("gm0", "gm1_gm3", "gm4", "gm45", "gm5", "gm6", "gm7")


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def command_plan(
    cfg: dict, dataset: Path, results: Path, dry_run: bool
) -> list[tuple[str, str, list[str]]]:
    """Return ``(logical_stage, display_label, command)`` entries."""
    exe = sys.executable
    execution = cfg.get("execution", {})
    limit = execution.get("limit")
    force = bool(execution.get("force", False))
    workers = int(execution.get("workers", 1))
    passive = cfg.get("passive_control", {})
    protocols = cfg.get("protocols", {})
    calibration = cfg.get("calibration", {})
    recon = results / "gm1_gm3"
    gm4_root = ROOT / "stages/gm4_passive"
    gm45_root = ROOT / "stages/gm45_calibration"
    gm5_root = ROOT / "stages/gm5_passive_atlas"
    plan: list[tuple[str, str, list[str]]] = []

    plan.append((
        "gm0", "gm0",
        [exe, str(ROOT / "stages/gm0_inventory/run_inventory.py"),
         "--data-root", str(dataset), "--output-dir", str(results / "gm0")],
    ))

    command = [
        exe, str(ROOT / "stages/gm1_gm3_reconstruction/run_pipeline.py"),
        "--data-root", str(dataset), "--output-root", str(recon),
        "--workers", str(workers),
    ]
    if dry_run:
        command.append("--dry-run")
    if force:
        command.append("--force")
    if limit:
        command += ["--limit", str(limit)]
    plan.append(("gm1_gm3", "gm1-gm3", command))

    command = [
        exe, str(gm4_root / "run_step4.py"),
        "--reconstruction-root", str(recon),
        "--output-root", str(results / "gm4_morphology_control"),
        "--matrix-mode", str(protocols.get("gm4_matrix_mode", "representative")),
        "--representative-terminals", str(protocols.get("representative_terminals", 8)),
        "--rm", str(passive.get("rm_ohm_cm2", 20000.0)),
        "--ra", str(passive.get("ra_ohm_cm", 150.0)),
        "--cm", str(passive.get("cm_uF_cm2", 1.0)),
        "--diameter", str(passive.get("process_diameter_um", 0.30)),
        "--rest", str(passive.get("e_pas_mV", -75.0)),
    ]
    if dry_run:
        command.append("--dry-run")
    if force:
        command.append("--force")
    if limit:
        command += ["--limit", str(limit)]
    plan.append(("gm4", "gm4-morphology-control", command))

    gm45_common = [
        exe, str(gm45_root / "run_gm45.py"),
        "--config", str(gm45_root / "config/calibration_config.json"),
        "--reconstruction-root", str(recon),
        "--gm4-root", str(gm4_root),
    ]
    cohort_output = results / "gm45_sweep"
    extended_output = results / "gm45_extended"
    plan.append((
        "gm45", "gm45-base-sweep",
        gm45_common + ["--mode", "cohort", "--output-root", str(cohort_output)]
        + (["--force"] if force else []),
    ))
    extension_values = calibration.get("p10_extension_rm_kohm_cm2", [24, 26, 28, 30, 32])
    plan.append((
        "gm45", "gm45-p10-extension",
        gm45_common + [
            "--mode", "extend",
            "--input-csv", str(cohort_output / "population/Rin_vs_Rm.csv"),
            "--ages", "P10",
            "--rm-values", *[str(value) for value in extension_values],
            "--output-root", str(extended_output),
        ] + (["--force"] if force else []),
    ))

    calibrated_gm4 = results / "gm4_calibrated"
    command = [
        exe, str(gm5_root / "run_calibrated_step4.py"),
        "--gm4-root", str(gm4_root),
        "--reconstruction-root", str(recon),
        "--output-root", str(calibrated_gm4),
        "--calibration", str(gm5_root / "config/calibrated_passive_parameters.json"),
        "--matrix-mode", str(protocols.get("gm4_matrix_mode", "representative")),
        "--representative-terminals", str(protocols.get("representative_terminals", 8)),
    ]
    if dry_run:
        command.append("--dry-run")
    if force:
        command.append("--force")
    if limit:
        command += ["--limit", str(limit)]
    plan.append(("gm5", "gm5-calibrated-gm4-preparation", command))
    plan.append((
        "gm5", "gm5-passive-atlas",
        [exe, str(gm5_root / "run_gm5.py"), "--step4-root", str(calibrated_gm4),
         "--output-root", str(results / "gm5")],
    ))

    command = [
        exe, str(ROOT / "stages/gm6_synaptic/run_gm6.py"),
        "--reconstruction-root", str(recon), "--output-root", str(results / "gm6"),
    ]
    if dry_run:
        command.append("--dry-run")
    if limit:
        command += ["--limit", str(limit)]
    plan.append(("gm6", "gm6-synaptic-atlas", command))

    command = [
        exe, str(ROOT / "stages/gm7_robustness/run_gm7.py"),
        "--reconstruction-root", str(recon), "--output-root", str(results / "gm7"),
    ]
    if dry_run:
        command.append("--dry-run")
    if limit:
        command += ["--limit", str(limit)]
    if execution.get("enable_gm7_interactions", False):
        command.append("--enable-interactions")
    plan.append(("gm7", "gm7-robustness", command))
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the calibrated OPC passive-cable workflow from one YAML configuration."
    )
    parser.add_argument("--config", type=Path, default=ROOT / "config/default.yaml")
    parser.add_argument("--dataset", type=Path, help="Override paths.dataset_root")
    parser.add_argument("--results", type=Path, help="Override paths.results_root")
    parser.add_argument("--stages", nargs="+", choices=STAGE_CHOICES)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Plan work and propagate dry-run flags without expensive simulations.",
    )
    parser.add_argument("--print-plan", action="store_true")
    args = parser.parse_args()
    cfg = load_config(args.config)
    dataset = (args.dataset or Path(cfg["paths"]["dataset_root"])).expanduser()
    results = (args.results or Path(cfg["paths"]["results_root"])).expanduser()
    if not dataset.is_absolute():
        dataset = ROOT / dataset
    if not results.is_absolute():
        results = ROOT / results
    selected = args.stages or cfg.get("execution", {}).get("stages", list(STAGE_CHOICES))
    plan = [entry for entry in command_plan(cfg, dataset, results, args.dry_run)
            if entry[0] in selected]
    print(f"Dataset: {dataset}")
    print(f"Results: {results}")
    for _, label, command in plan:
        print(f"[{label}] {' '.join(command)}")
    if args.print_plan or args.dry_run:
        print("Dry run complete: no stage was executed.")
        return 0
    if not dataset.exists():
        print(f"ERROR: dataset root does not exist: {dataset}", file=sys.stderr)
        return 2
    results.mkdir(parents=True, exist_ok=True)
    for _, label, command in plan:
        print(f"\n=== {label} ===", flush=True)
        completed = subprocess.run(command, cwd=ROOT)
        if completed.returncode:
            print(f"{label} failed with exit code {completed.returncode}", file=sys.stderr)
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
