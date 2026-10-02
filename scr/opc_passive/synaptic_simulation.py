from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
import csv
import gc
import math

import numpy as np
from neuron import h

from .passive_neuron import PassiveOPCCell

h.load_file("stdrun.hoc")


@dataclass(frozen=True)
class SynapseParameters:
    tau1_ms: float = 0.5
    tau2_ms: float = 3.0
    reversal_mV: float = 0.0
    weight_uS: float = 0.00005
    event_time_ms: float = 20.0
    location: float = 0.5


@dataclass(frozen=True)
class SimulationParameters:
    tstop_ms: float = 80.0
    dt_ms: float = 0.025
    baseline_end_ms: float = 19.0


@dataclass(frozen=True)
class SynapticSite:
    class_name: str
    segment_id: int
    location: float
    radial_distance_um: float | None
    path_distance_um: float
    branch_order: int
    tree: int
    terminal_type: str


@dataclass
class SynapticResult:
    cell_id: str
    class_name: str
    segment_id: int
    location: float
    radial_distance_um: float | None
    path_distance_um: float
    branch_order: int
    tree: int
    terminal_type: str
    local_baseline_mV: float
    soma_baseline_mV: float
    local_peak_mV: float
    soma_peak_mV: float
    local_epsp_mV: float
    soma_epsp_mV: float
    attenuation_ratio: float | None
    local_peak_time_ms: float
    soma_peak_time_ms: float
    peak_delay_ms: float
    synapse_parameters: dict[str, Any]
    simulation_parameters: dict[str, Any]

    def flat_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row.pop("synapse_parameters")
        row.pop("simulation_parameters")
        row.update({f"syn_{k}": v for k, v in self.synapse_parameters.items()})
        row.update({f"sim_{k}": v for k, v in self.simulation_parameters.items()})
        return row


def _nearest_unique(values: list[tuple[int, float]], targets: Iterable[float]) -> list[int]:
    available = set(segment_id for segment_id, _ in values)
    selected: list[int] = []
    for target in targets:
        candidates = [item for item in values if item[0] in available]
        if not candidates:
            break
        segment_id, _ = min(candidates, key=lambda item: abs(item[1] - target))
        selected.append(segment_id)
        available.remove(segment_id)
    return selected


def select_representative_sites(cell: PassiveOPCCell, location: float = 0.5) -> list[SynapticSite]:
    """Select pilot sites at the 15th, 50th, and 85th radial quantiles."""
    measured: list[tuple[int, float]] = []
    for segment_id in cell.metadata_by_segment:
        radial = cell.radial_distance_um(segment_id, location)
        if radial is not None and math.isfinite(radial):
            measured.append((segment_id, float(radial)))
    if len(measured) < 3:
        raise ValueError("At least three segments with radial distances are required.")

    distances = np.asarray([value for _, value in measured], dtype=float)
    targets = np.quantile(distances, [0.15, 0.50, 0.85]).tolist()
    chosen = _nearest_unique(measured, targets)
    names = ["proximal", "intermediate", "distal"]

    sites: list[SynapticSite] = []
    for name, segment_id in zip(names, chosen):
        metadata = cell.metadata_by_segment[segment_id]
        sites.append(SynapticSite(
            class_name=name,
            segment_id=segment_id,
            location=location,
            radial_distance_um=cell.radial_distance_um(segment_id, location),
            path_distance_um=cell.path_distance_um(segment_id, location),
            branch_order=metadata.order,
            tree=metadata.tree,
            terminal_type=metadata.terminal_type,
        ))
    return sites


def _baseline(values: np.ndarray, times: np.ndarray, end_ms: float) -> float:
    mask = times <= end_ms
    return float(np.mean(values[mask])) if np.any(mask) else float(values[0])


def run_single_synapse(
    cell: PassiveOPCCell,
    site: SynapticSite,
    synapse: SynapseParameters | None = None,
    simulation: SimulationParameters | None = None,
) -> tuple[SynapticResult, dict[str, np.ndarray]]:
    if not cell.sections_by_segment:
        raise RuntimeError("The NEURON cell must be built before simulation.")

    synapse = synapse or SynapseParameters(location=site.location)
    simulation = simulation or SimulationParameters()
    if synapse.tau1_ms <= 0 or synapse.tau2_ms <= synapse.tau1_ms:
        raise ValueError("Require 0 < tau1_ms < tau2_ms.")

    section = cell.sections_by_segment[site.segment_id]
    target = section(site.location)

    point_process = h.Exp2Syn(target)
    point_process.tau1 = synapse.tau1_ms
    point_process.tau2 = synapse.tau2_ms
    point_process.e = synapse.reversal_mV

    stimulus = h.NetStim()
    stimulus.number = 1
    stimulus.start = synapse.event_time_ms
    stimulus.interval = 1.0
    stimulus.noise = 0.0

    connection = h.NetCon(stimulus, point_process)
    connection.delay = 0.0
    connection.weight[0] = synapse.weight_uS

    t_vector = h.Vector().record(h._ref_t)
    local_vector = h.Vector().record(target._ref_v)
    soma_vector = h.Vector().record(cell.soma(0.5)._ref_v)

    h.cvode_active(0)
    h.dt = simulation.dt_ms
    h.steps_per_ms = 1.0 / simulation.dt_ms
    h.tstop = simulation.tstop_ms
    h.finitialize(cell.parameters.e_pas_mV)
    h.continuerun(simulation.tstop_ms)

    times = np.asarray(t_vector, dtype=float)
    local = np.asarray(local_vector, dtype=float)
    soma = np.asarray(soma_vector, dtype=float)
    local_baseline = _baseline(local, times, simulation.baseline_end_ms)
    soma_baseline = _baseline(soma, times, simulation.baseline_end_ms)

    post_indices = np.where(times >= synapse.event_time_ms)[0]
    local_index = int(post_indices[np.argmax(local[post_indices])])
    soma_index = int(post_indices[np.argmax(soma[post_indices])])
    local_peak = float(local[local_index])
    soma_peak = float(soma[soma_index])
    local_epsp = local_peak - local_baseline
    soma_epsp = soma_peak - soma_baseline
    attenuation = soma_epsp / local_epsp if local_epsp > 0 else None

    result = SynapticResult(
        cell_id=cell.cell_id,
        class_name=site.class_name,
        segment_id=site.segment_id,
        location=site.location,
        radial_distance_um=site.radial_distance_um,
        path_distance_um=site.path_distance_um,
        branch_order=site.branch_order,
        tree=site.tree,
        terminal_type=site.terminal_type,
        local_baseline_mV=local_baseline,
        soma_baseline_mV=soma_baseline,
        local_peak_mV=local_peak,
        soma_peak_mV=soma_peak,
        local_epsp_mV=local_epsp,
        soma_epsp_mV=soma_epsp,
        attenuation_ratio=attenuation,
        local_peak_time_ms=float(times[local_index]),
        soma_peak_time_ms=float(times[soma_index]),
        peak_delay_ms=float(times[soma_index] - times[local_index]),
        synapse_parameters=asdict(synapse),
        simulation_parameters=asdict(simulation),
    )
    traces = {"time_ms": times, "local_mV": local, "soma_mV": soma}

    del connection, stimulus, point_process
    del t_vector, local_vector, soma_vector
    gc.collect()
    return result, traces


def export_trace(path: str | Path, traces: dict[str, np.ndarray]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_ms", "local_mV", "soma_mV"])
        writer.writerows(zip(traces["time_ms"], traces["local_mV"], traces["soma_mV"]))


def export_results(path: str | Path, results: list[SynapticResult]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [result.flat_dict() for result in results]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
