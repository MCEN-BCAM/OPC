from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable
import csv
import json
import math

import numpy as np
import matplotlib.pyplot as plt

from .passive_neuron import PassiveOPCCell, PassiveParameters
from .synaptic_simulation import (
    SynapseParameters,
    SimulationParameters,
    SynapticSite,
    SynapticResult,
    run_single_synapse,
)


def select_stratified_sites(
    cell: PassiveOPCCell,
    n_sites: int = 75,
    location: float = 0.5,
    distance: str = "radial",
) -> list[SynapticSite]:
    """Select unique sections spanning the full distance distribution."""
    values: list[tuple[int, float]] = []
    for segment_id, metadata in cell.metadata_by_segment.items():
        value = (
            cell.radial_distance_um(segment_id, location)
            if distance == "radial"
            else cell.path_distance_um(segment_id, location)
        )
        if value is not None and math.isfinite(value):
            values.append((segment_id, float(value)))
    values.sort(key=lambda item: item[1])
    if not values:
        raise ValueError("No valid candidate sections were found.")

    n_sites = min(n_sites, len(values))
    indices = np.linspace(0, len(values) - 1, n_sites)
    chosen_indices = sorted(set(int(round(index)) for index in indices))
    # Rarely, rounding yields fewer sites; fill from unused ranked positions.
    if len(chosen_indices) < n_sites:
        for index in range(len(values)):
            if index not in chosen_indices:
                chosen_indices.append(index)
                if len(chosen_indices) == n_sites:
                    break
        chosen_indices.sort()

    result: list[SynapticSite] = []
    quantiles = np.linspace(0.0, 1.0, len(chosen_indices))
    for rank, index in enumerate(chosen_indices):
        segment_id, _ = values[index]
        metadata = cell.metadata_by_segment[segment_id]
        q = quantiles[rank]
        if q < 1/3:
            class_name = "proximal"
        elif q < 2/3:
            class_name = "intermediate"
        else:
            class_name = "distal"
        result.append(SynapticSite(
            class_name=class_name,
            segment_id=segment_id,
            location=location,
            radial_distance_um=cell.radial_distance_um(segment_id, location),
            path_distance_um=cell.path_distance_um(segment_id, location),
            branch_order=metadata.order,
            tree=metadata.tree,
            terminal_type=metadata.terminal_type,
        ))
    return result


def run_site_set(
    cell: PassiveOPCCell,
    sites: Iterable[SynapticSite],
    synapse: SynapseParameters,
    simulation: SimulationParameters,
) -> list[SynapticResult]:
    results: list[SynapticResult] = []
    for site in sites:
        result, _ = run_single_synapse(cell, site, synapse, simulation)
        results.append(result)
    return results


def result_rows(results: list[SynapticResult], extra: dict | None = None) -> list[dict]:
    rows = []
    for result in results:
        row = result.flat_dict()
        if extra:
            row.update(extra)
        rows.append(row)
    return rows


def write_rows(path: str | Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("No rows to export.")
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def summarise_dense(results: list[SynapticResult]) -> dict:
    attenuation = np.asarray([
        result.attenuation_ratio for result in results
        if result.attenuation_ratio is not None
    ], dtype=float)
    by_class = {}
    for name in ("proximal", "intermediate", "distal"):
        subset = np.asarray([
            result.attenuation_ratio for result in results
            if result.class_name == name and result.attenuation_ratio is not None
        ], dtype=float)
        by_class[name] = {
            "n": int(len(subset)),
            "mean": float(np.mean(subset)),
            "median": float(np.median(subset)),
            "minimum": float(np.min(subset)),
            "maximum": float(np.max(subset)),
        }
    path = np.asarray([result.path_distance_um for result in results], dtype=float)
    radial = np.asarray([result.radial_distance_um for result in results], dtype=float)
    corr_path = float(np.corrcoef(path, attenuation)[0, 1])
    corr_radial = float(np.corrcoef(radial, attenuation)[0, 1])
    return {
        "n_sites": len(results),
        "attenuation_mean": float(np.mean(attenuation)),
        "attenuation_median": float(np.median(attenuation)),
        "attenuation_minimum": float(np.min(attenuation)),
        "attenuation_maximum": float(np.max(attenuation)),
        "correlation_path_attenuation": corr_path,
        "correlation_radial_attenuation": corr_radial,
        "by_radial_class": by_class,
    }


def plot_distance(results: list[SynapticResult], output_dir: str | Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cell_id = results[0].cell_id
    attenuation = [result.attenuation_ratio for result in results]

    fig = plt.figure(figsize=(7, 5))
    plt.scatter([result.path_distance_um for result in results], attenuation)
    plt.xlabel("Cable-path distance to soma (um)")
    plt.ylabel("Attenuation ratio")
    plt.title(f"{cell_id}: attenuation versus path distance")
    plt.tight_layout()
    fig.savefig(output_dir / f"{cell_id}_attenuation_vs_path.png", dpi=180)
    plt.close(fig)

    fig = plt.figure(figsize=(7, 5))
    plt.scatter([result.radial_distance_um for result in results], attenuation)
    plt.xlabel("Radial distance to soma (um)")
    plt.ylabel("Attenuation ratio")
    plt.title(f"{cell_id}: attenuation versus radial distance")
    plt.tight_layout()
    fig.savefig(output_dir / f"{cell_id}_attenuation_vs_radial.png", dpi=180)
    plt.close(fig)

    fig = plt.figure(figsize=(7, 5))
    plt.scatter([result.branch_order for result in results], attenuation)
    plt.xlabel("Branch order")
    plt.ylabel("Attenuation ratio")
    plt.title(f"{cell_id}: attenuation versus branch order")
    plt.tight_layout()
    fig.savefig(output_dir / f"{cell_id}_attenuation_vs_order.png", dpi=180)
    plt.close(fig)


def plot_attenuation_map(
    reconstruction_path: str | Path,
    results: list[SynapticResult],
    output_path: str | Path,
) -> None:
    reconstruction = json.loads(Path(reconstruction_path).read_text(encoding="utf-8"))
    attenuation = {result.segment_id: result.attenuation_ratio for result in results}
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection="3d")
    for segment in reconstruction["segments"]:
        if segment["end"] is None:
            continue
        start, end = segment["start"], segment["end"]
        value = attenuation.get(int(segment["segment_id"]))
        if value is None:
            ax.plot([start[0], end[0]], [start[1], end[1]], [start[2], end[2]], linewidth=0.35, alpha=0.25)
        else:
            ax.scatter(
                [(start[0] + end[0]) / 2],
                [(start[1] + end[1]) / 2],
                [(start[2] + end[2]) / 2],
                c=[value], vmin=0.0, vmax=1.0, s=18,
            )
    centre = reconstruction.get("soma_centroid")
    if centre is not None:
        ax.scatter([centre[0]], [centre[1]], [centre[2]], s=45)
    ax.set_xlabel("X (um)")
    ax.set_ylabel("Y (um)")
    ax.set_zlabel("Z (um)")
    ax.set_title(f"{reconstruction['cell_id']}: sampled attenuation map")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def sensitivity_summary(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[float]] = {}
    for row in rows:
        key = (
            row["cell_id"], row["diameter_um"], row["rm_ohm_cm2"], row["class_name"]
        )
        grouped.setdefault(key, []).append(float(row["attenuation_ratio"]))
    output = []
    for (cell_id, diameter, rm, class_name), values in sorted(grouped.items()):
        output.append({
            "cell_id": cell_id,
            "diameter_um": diameter,
            "rm_ohm_cm2": rm,
            "class_name": class_name,
            "n": len(values),
            "attenuation_mean": float(np.mean(values)),
            "attenuation_median": float(np.median(values)),
            "attenuation_minimum": float(np.min(values)),
            "attenuation_maximum": float(np.max(values)),
        })
    return output
