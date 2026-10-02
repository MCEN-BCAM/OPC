from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .io import discover_cell_directories, load_cell_bundle, read_json, write_csv, write_json
from .plots import attenuation_by_distance, cell_attenuation_map, metric_distribution, morphology_electrophysiology, soma_trace
from .qc import assess_cell
from .report import write_cell_report, write_index
from .stats import descriptive_table, inferential_table

METRICS = [
    "input_resistance_MOhm", "tau_ms", "maximum_path_distance_um",
    "mean_soma_normalised_attenuation", "minimum_soma_normalised_attenuation",
    "total_cable_length_um", "maximum_branch_order", "n_terminals", "n_segments"
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_atlas(step4_root: Path, output_root: Path, config_path: Path) -> dict:
    config = read_json(config_path)
    output_root.mkdir(parents=True, exist_ok=True)
    dirs = discover_cell_directories(step4_root)
    qc_rows, metric_rows, attenuation_rows = [], [], []
    bundles = []
    failures = []
    for cell_dir in dirs:
        try:
            bundle = load_cell_bundle(cell_dir)
            bundles.append(bundle)
            qc = assess_cell(bundle, config)
            qc_rows.append(qc)
            row = dict(bundle["summary"])
            row["qc_status"] = qc["qc_status"]
            metric_rows.append(row)
            att = bundle["attenuation"].copy()
            att["cell_id"] = bundle["cell_id"]
            att["age_group"] = row.get("age_group", "UNKNOWN")
            attenuation_rows.append(att)
        except Exception as exc:
            failures.append({"cell_id": cell_dir.name, "error": str(exc)})

    qc_frame = pd.DataFrame(qc_rows)
    metrics = pd.DataFrame(metric_rows)
    attenuation = pd.concat(attenuation_rows, ignore_index=True) if attenuation_rows else pd.DataFrame()
    accepted_ids = set(qc_frame.loc[qc_frame.qc_status == "accepted", "cell_id"]) if not qc_frame.empty else set()
    accepted = metrics.loc[metrics.cell_id.isin(accepted_ids)].copy() if not metrics.empty else metrics
    accepted_att = attenuation.loc[attenuation.cell_id.isin(accepted_ids)].copy() if not attenuation.empty else attenuation

    if not accepted_att.empty:
        width = float(config["attenuation"]["distance_bin_um"])
        accepted_att["distance_bin_centre_um"] = (np.floor(accepted_att["path_distance_um"] / width) + .5) * width

    descriptive = descriptive_table(accepted, [m for m in METRICS if m in accepted.columns], config) if not accepted.empty else pd.DataFrame()
    omnibus, pairwise = inferential_table(accepted, [m for m in METRICS if m in accepted.columns], int(config["quality_control"]["minimum_cells_per_age_for_inference"])) if not accepted.empty else (pd.DataFrame(), pd.DataFrame())

    tables = output_root / "tables"
    write_csv(tables / "cell_quality_control.csv", qc_frame)
    write_csv(tables / "accepted_cell_metrics.csv", accepted)
    write_csv(tables / "all_cell_metrics.csv", metrics)
    write_csv(tables / "attenuation_long.csv", accepted_att)
    write_csv(tables / "descriptive_statistics.csv", descriptive)
    write_csv(tables / "omnibus_tests.csv", omnibus)
    write_csv(tables / "pairwise_tests.csv", pairwise)
    write_csv(tables / "ingestion_failures.csv", pd.DataFrame(failures))

    figures = output_root / "figures"
    if not accepted.empty:
        metric_distribution(accepted, "input_resistance_MOhm", "Input resistance (MΩ)", figures / "input_resistance", config)
        metric_distribution(accepted, "tau_ms", "Membrane time constant (ms)", figures / "tau", config)
        metric_distribution(accepted, "mean_soma_normalised_attenuation", "Mean soma-normalised attenuation", figures / "mean_attenuation", config)
        metric_distribution(accepted, "maximum_path_distance_um", "Maximum path distance (µm)", figures / "maximum_path_distance", config)
        morphology_electrophysiology(accepted, "total_cable_length_um", "input_resistance_MOhm", figures / "cable_length_vs_rin", config)
    if not accepted_att.empty:
        attenuation_by_distance(accepted_att, figures / "attenuation_by_distance", config)

    for bundle in bundles:
        qc = next((r for r in qc_rows if r["cell_id"] == bundle["cell_id"]), None)
        if qc is None:
            continue
        soma_trace(bundle["trace"], bundle["cell_id"], figures / f"{bundle['cell_id']}_soma_trace", config)
        cell_attenuation_map(bundle["attenuation"], bundle["cell_id"], figures / f"{bundle['cell_id']}_attenuation", config)
        write_cell_report(output_root / "cells" / f"{bundle['cell_id']}.html", bundle["cell_id"], bundle["summary"], qc)

    write_index(output_root / "index.html", qc_frame, descriptive, omnibus, pairwise, len(dirs), len(accepted_ids))
    provenance = {
        "created_at": _utcnow(), "python": sys.version, "platform": platform.platform(),
        "step4_root": str(step4_root.resolve()), "config": config,
        "n_cell_directories": len(dirs), "n_loaded": len(bundles), "n_accepted": len(accepted_ids),
        "n_excluded": int((qc_frame.qc_status == "excluded").sum()) if not qc_frame.empty else 0,
        "n_ingestion_failures": len(failures),
    }
    write_json(output_root / "atlas_manifest.json", provenance)
    return provenance
