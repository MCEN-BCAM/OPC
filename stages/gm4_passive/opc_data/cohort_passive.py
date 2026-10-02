from __future__ import annotations

import csv
import json
import platform
import sys
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .passive_neuron import PassiveOPCCell, PassiveParameters
from .passive_protocols import CurrentStepProtocol, TransferProtocol, bidirectional_attenuation, current_step, full_transfer_matrix


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields=[]
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer=csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def discover_reconstructions(root: Path) -> list[Path]:
    return sorted(root.rglob("*_reconstruction.json"))


def age_from_cell_id(cell_id: str) -> str:
    for age in ("P10", "P20", "P50"):
        if cell_id.endswith("_" + age):
            return age
    return "UNKNOWN"


def run_one(reconstruction_path: Path, output_root: Path, parameters: PassiveParameters, current_protocol: CurrentStepProtocol, transfer_protocol: TransferProtocol, n_terminals: int, matrix_mode: str) -> dict[str, Any]:
    data=json.loads(reconstruction_path.read_text(encoding="utf-8"))
    cell_id=str(data["cell_id"])
    out=output_root/"cells"/cell_id
    out.mkdir(parents=True, exist_ok=True)
    manifest={"cell_id":cell_id,"age_group":age_from_cell_id(cell_id),"started_at":utcnow(),"reconstruction":str(reconstruction_path),"status":"running"}
    write_json(out/"manifest.json", manifest)
    try:
        with PassiveOPCCell(data, parameters).build() as cell:
            structural=cell.validate()
            if not structural["ready_for_simulation"]:
                raise RuntimeError("Passive NEURON structure failed validation")
            rest=cell.resting_smoke_test()
            step=current_step(cell, current_protocol, record_all=True)
            attenuation=bidirectional_attenuation(cell, n_terminals=n_terminals, protocol=transfer_protocol)
            matrix=[]
            if matrix_mode == "full":
                matrix=full_transfer_matrix(cell, protocol=transfer_protocol)
            elif matrix_mode == "representative":
                selected=sorted({x["target_segment_id"] for x in attenuation if x.get("target_segment_id") is not None})
                matrix=full_transfer_matrix(cell, selected, transfer_protocol)

            write_json(out/f"{cell_id}_structural_validation.json", structural)
            write_json(out/f"{cell_id}_resting_test.json", rest)
            write_json(out/f"{cell_id}_current_step_summary.json", {"protocol":step["protocol"],"soma":step["soma"]})
            write_csv(out/f"{cell_id}_attenuation_map.csv", step["site_rows"])
            write_csv(out/f"{cell_id}_bidirectional_transfer.csv", attenuation)
            write_csv(out/f"{cell_id}_transfer_matrix.csv", matrix)
            write_csv(out/f"{cell_id}_soma_trace.csv", [dict(time_ms=t, soma_mV=v) for t,v in zip(step["trace"]["time_ms"], step["trace"]["soma_mV"])])

            distances=[r["path_distance_um"] for r in step["site_rows"] if r["path_distance_um"] is not None]
            atts=[r["soma_normalised_attenuation"] for r in step["site_rows"] if r["soma_normalised_attenuation"] is not None]
            summary={
                "cell_id":cell_id,"age_group":age_from_cell_id(cell_id),
                "n_segments":structural["source_segment_count"],
                "total_cable_length_um":structural["source_total_cable_length_um"],
                "maximum_branch_order":structural["maximum_branch_order"],
                "n_terminals":structural["terminal_section_count"],
                "input_resistance_MOhm":step["soma"]["input_resistance_MOhm"],
                "tau_ms":step["soma"]["tau_ms"],
                "tau_fit_r2":step["soma"]["tau_fit_r2"],
                "maximum_path_distance_um":max(distances, default=None),
                "mean_soma_normalised_attenuation":sum(atts)/len(atts) if atts else None,
                "minimum_soma_normalised_attenuation":min(atts, default=None),
                "resting_stable":rest["stable_at_rest"],
                "matrix_mode":matrix_mode,
                "n_transfer_rows":len(matrix),
            }
            write_json(out/f"{cell_id}_passive_summary.json", summary)
            manifest.update({"status":"complete","finished_at":utcnow(),"summary":summary})
            write_json(out/"manifest.json", manifest)
            return summary
    except Exception as exc:
        manifest.update({"status":"failed","finished_at":utcnow(),"error":str(exc),"traceback":traceback.format_exc()})
        write_json(out/"manifest.json", manifest)
        return {"cell_id":cell_id,"age_group":age_from_cell_id(cell_id),"status":"failed","error":str(exc)}


def aggregate(results: list[dict[str, Any]], output_root: Path) -> None:
    good=[r for r in results if r.get("status") != "failed"]
    bad=[r for r in results if r.get("status") == "failed"]
    write_csv(output_root/"population"/"cell_level_passive_metrics.csv", good)
    write_csv(output_root/"population"/"failed_cells.csv", bad)
    by_age=[]
    metrics=["input_resistance_MOhm","tau_ms","maximum_path_distance_um","mean_soma_normalised_attenuation","minimum_soma_normalised_attenuation","total_cable_length_um"]
    for age in sorted({r["age_group"] for r in good}):
        subset=[r for r in good if r["age_group"]==age]
        for metric in metrics:
            values=[float(r[metric]) for r in subset if r.get(metric) is not None]
            if not values: continue
            values_sorted=sorted(values)
            n=len(values)
            median=values_sorted[n//2] if n%2 else 0.5*(values_sorted[n//2-1]+values_sorted[n//2])
            mean=sum(values)/n
            sd=(sum((x-mean)**2 for x in values)/(n-1))**0.5 if n>1 else 0.0
            by_age.append({"age_group":age,"metric":metric,"n":n,"mean":mean,"sd":sd,"median":median,"minimum":min(values),"maximum":max(values)})
    write_csv(output_root/"population"/"age_group_summary.csv", by_age)
    write_json(output_root/"run_summary.json", {"finished_at":utcnow(),"n_complete":len(good),"n_failed":len(bad),"results":results})


def provenance(parameters: PassiveParameters, current_protocol: CurrentStepProtocol, transfer_protocol: TransferProtocol) -> dict[str, Any]:
    try:
        from neuron import h
        neuron_version=str(h.nrnversion())
    except Exception as exc:
        neuron_version=f"unavailable: {exc}"
    return {"created_at":utcnow(),"python":sys.version,"platform":platform.platform(),"neuron":neuron_version,"passive_parameters":asdict(parameters),"current_step_protocol":asdict(current_protocol),"transfer_protocol":asdict(transfer_protocol)}
