from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable
import math

import numpy as np
from scipy.optimize import curve_fit
from neuron import h


@dataclass(frozen=True)
class CurrentStepProtocol:
    delay_ms: float = 20.0
    duration_ms: float = 80.0
    amplitude_nA: float = -0.01
    tstop_ms: float = 130.0
    dt_ms: float = 0.025
    baseline_window_ms: float = 10.0
    steady_window_ms: float = 10.0


@dataclass(frozen=True)
class TransferProtocol:
    delay_ms: float = 10.0
    duration_ms: float = 40.0
    amplitude_nA: float = -0.005
    tstop_ms: float = 65.0
    dt_ms: float = 0.025
    steady_window_ms: float = 8.0


def _record(section: Any, location: float = 0.5) -> Any:
    return h.Vector().record(section(location)._ref_v)


def _run(tstop_ms: float, dt_ms: float, v_init_mV: float) -> np.ndarray:
    h.dt = dt_ms
    h.steps_per_ms = 1.0 / dt_ms
    h.tstop = tstop_ms
    t = h.Vector().record(h._ref_t)
    h.finitialize(v_init_mV)
    h.continuerun(tstop_ms)
    return np.asarray(t, dtype=float)


def _window_mean(t: np.ndarray, y: np.ndarray, start: float, stop: float) -> float:
    mask = (t >= start) & (t <= stop)
    if not np.any(mask):
        raise ValueError(f"Empty averaging window [{start}, {stop}] ms")
    return float(np.mean(y[mask]))


def _fit_tau(t: np.ndarray, v: np.ndarray, delay: float, duration: float, baseline: float) -> tuple[float | None, float | None]:
    mask = (t >= delay) & (t <= delay + min(duration, 5.0 * duration))
    tt = t[mask] - delay
    yy = v[mask]
    if len(tt) < 10:
        return None, None

    def model(x: np.ndarray, v_inf: float, tau: float) -> np.ndarray:
        return v_inf + (baseline - v_inf) * np.exp(-x / tau)

    try:
        p0 = [float(np.mean(yy[-max(3, len(yy)//10):])), max(0.1, duration / 5.0)]
        popt, _ = curve_fit(model, tt, yy, p0=p0, bounds=([-200.0, 1e-4], [100.0, 1e5]), maxfev=20000)
        pred = model(tt, *popt)
        ss_res = float(np.sum((yy - pred) ** 2))
        ss_tot = float(np.sum((yy - np.mean(yy)) ** 2))
        r2 = None if ss_tot <= 0 else 1.0 - ss_res / ss_tot
        return float(popt[1]), r2
    except Exception:
        return None, None


def current_step(cell: Any, protocol: CurrentStepProtocol | None = None, record_all: bool = True) -> dict[str, Any]:
    p = protocol or CurrentStepProtocol()
    stim = h.IClamp(cell.soma(0.5))
    stim.delay = p.delay_ms
    stim.dur = p.duration_ms
    stim.amp = p.amplitude_nA

    soma_vec = _record(cell.soma, 0.5)
    site_vecs: dict[int, Any] = {}
    if record_all:
        for sid, sec in cell.sections_by_segment.items():
            site_vecs[sid] = _record(sec, 0.5)

    t = _run(p.tstop_ms, p.dt_ms, cell.parameters.e_pas_mV)
    soma = np.asarray(soma_vec, dtype=float)
    baseline = _window_mean(t, soma, p.delay_ms - p.baseline_window_ms, p.delay_ms)
    steady = _window_mean(t, soma, p.delay_ms + p.duration_ms - p.steady_window_ms, p.delay_ms + p.duration_ms)
    dv = steady - baseline
    rin = None if abs(p.amplitude_nA) < 1e-15 else dv / p.amplitude_nA
    tau, tau_r2 = _fit_tau(t, soma, p.delay_ms, p.duration_ms, baseline)

    site_rows = []
    for sid, vec in site_vecs.items():
        vv = np.asarray(vec, dtype=float)
        vb = _window_mean(t, vv, p.delay_ms - p.baseline_window_ms, p.delay_ms)
        vs = _window_mean(t, vv, p.delay_ms + p.duration_ms - p.steady_window_ms, p.delay_ms + p.duration_ms)
        local_dv = vs - vb
        attenuation = None if abs(dv) < 1e-15 else local_dv / dv
        meta = cell.metadata_by_segment[sid]
        site_rows.append({
            "segment_id": sid,
            "tree": meta.tree,
            "order": meta.order,
            "terminal_type": meta.terminal_type,
            "path_distance_um": cell.path_distance_um(sid),
            "radial_distance_um": cell.radial_distance_um(sid),
            "baseline_mV": vb,
            "steady_mV": vs,
            "delta_v_mV": local_dv,
            "soma_normalised_attenuation": attenuation,
        })

    del stim
    return {
        "protocol": asdict(p),
        "soma": {
            "baseline_mV": baseline,
            "steady_mV": steady,
            "delta_v_mV": dv,
            "input_resistance_MOhm": rin,
            "tau_ms": tau,
            "tau_fit_r2": tau_r2,
        },
        "site_rows": site_rows,
        "trace": {"time_ms": t.tolist(), "soma_mV": soma.tolist()},
    }


def _steady_deflection(t: np.ndarray, v: np.ndarray, delay: float, duration: float, window: float) -> float:
    base = _window_mean(t, v, max(0.0, delay-window), delay)
    steady = _window_mean(t, v, delay+duration-window, delay+duration)
    return steady-base


def transfer_measurement(cell: Any, source_sid: int | None, target_sids: Iterable[int | None], protocol: TransferProtocol | None = None) -> list[dict[str, Any]]:
    p = protocol or TransferProtocol()
    source_sec = cell.soma if source_sid is None else cell.sections_by_segment[source_sid]
    stim = h.IClamp(source_sec(0.5))
    stim.delay, stim.dur, stim.amp = p.delay_ms, p.duration_ms, p.amplitude_nA

    targets = list(target_sids)
    vectors = {}
    for target_sid in targets:
        target_sec = cell.soma if target_sid is None else cell.sections_by_segment[target_sid]
        vectors[target_sid] = _record(target_sec, 0.5)

    t = _run(p.tstop_ms, p.dt_ms, cell.parameters.e_pas_mV)
    rows=[]
    for target_sid, vec in vectors.items():
        dv = _steady_deflection(t, np.asarray(vec, dtype=float), p.delay_ms, p.duration_ms, p.steady_window_ms)
        z = None if abs(p.amplitude_nA) < 1e-15 else dv / p.amplitude_nA
        rows.append({
            "source_segment_id": source_sid,
            "target_segment_id": target_sid,
            "source_label": "soma" if source_sid is None else str(source_sid),
            "target_label": "soma" if target_sid is None else str(target_sid),
            "transfer_impedance_MOhm": z,
            "delta_v_mV": dv,
        })
    del stim
    return rows


def representative_terminal_ids(cell: Any, n: int = 8) -> list[int]:
    terminals = cell.terminals()
    if len(terminals) <= n:
        return sorted(terminals)
    ranked = sorted(terminals, key=lambda sid: cell.path_distance_um(sid))
    idx = np.linspace(0, len(ranked)-1, n).round().astype(int)
    return [ranked[i] for i in sorted(set(idx.tolist()))]


def bidirectional_attenuation(cell: Any, n_terminals: int = 8, protocol: TransferProtocol | None = None) -> list[dict[str, Any]]:
    terminals = representative_terminal_ids(cell, n=n_terminals)
    rows=[]
    soma_to = transfer_measurement(cell, None, terminals, protocol)
    for row in soma_to:
        row["direction"] = "soma_to_terminal"
        rows.append(row)
    for sid in terminals:
        local = transfer_measurement(cell, sid, [None, sid], protocol)
        self_z = next(x["transfer_impedance_MOhm"] for x in local if x["target_segment_id"] == sid)
        for row in local:
            if row["target_segment_id"] is None:
                row["direction"] = "terminal_to_soma"
                row["local_input_impedance_MOhm"] = self_z
                row["transfer_ratio"] = None if self_z in (None, 0) else row["transfer_impedance_MOhm"] / self_z
                rows.append(row)
    return rows


def full_transfer_matrix(cell: Any, segment_ids: list[int] | None = None, protocol: TransferProtocol | None = None) -> list[dict[str, Any]]:
    ids = sorted(cell.sections_by_segment) if segment_ids is None else sorted(segment_ids)
    targets: list[int | None] = [None] + ids
    rows=[]
    for source in [None] + ids:
        rows.extend(transfer_measurement(cell, source, targets, protocol))
    return rows
