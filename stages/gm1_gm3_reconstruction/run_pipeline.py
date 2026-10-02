#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, json, os, traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opc_inventory import build_inventory, write_reports

STAGES = ("data", "reconstruction", "validation", "neuron", "synaptic", "dense")

def utcnow() -> str: return datetime.now(timezone.utc).isoformat()
def dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def ready_records(inventory: dict, ages: set[str] | None, cells: set[str] | None) -> list[dict]:
    records=[]
    for r in inventory["cells"]:
        cid=f"{r['cell_id']}_{r['age_group']}"
        if r["status"] not in {"complete", "complete_with_warnings"}: continue
        if ages and r["age_group"] not in ages: continue
        if cells and cid not in cells and r["cell_id"] not in cells: continue
        rr=dict(r); rr["pipeline_cell_id"]=cid; records.append(rr)
    return sorted(records, key=lambda r:(r["age_group"], r["cell_id"]))

def find_one(folder: Path, patterns: list[str]) -> Path:
    hits=[]
    for p in patterns: hits.extend(folder.glob(p))
    hits=sorted(set(hits))
    if not hits: raise FileNotFoundError(f"No file matching {patterns} in {folder}")
    return hits[0]

def stage_data(record: dict, data_root: Path, cell_root: Path) -> dict:
    from opc_data.dataset import Dataset
    cid=record["pipeline_cell_id"]; out=cell_root/"01_data"
    ds=Dataset.discover(data_root)
    if cid not in ds.cells: raise KeyError(f"{cid} not found by validated Dataset.discover")
    ds.cells={cid:ds.cells[cid]}; ds.load_all(verbose=False); ds.export_all(out)
    return {"output_dir":str(out), "summary":str(out/cid/f"{cid}_summary.json")}

def stage_reconstruction(record: dict, cell_root: Path, tolerance: float) -> dict:
    from opc_data.reconstruction import reconstruct_cell, export_reconstruction
    from opc_data.plot_reconstruction import plot_reconstruction
    cid=record["pipeline_cell_id"]; data_dir=cell_root/"01_data"/cid; out=cell_root/"02_reconstruction"
    segment=find_one(data_dir,[f"{cid}_basic_Segment_Dendrites.csv",f"{cid}_basic*_Segment_Dendrites.csv"])
    result=reconstruct_cell(cid, record["basic_analysis"], segment, coordinate_tolerance_um=tolerance)
    export_reconstruction(result,out); plot_reconstruction(out/f"{cid}_reconstruction.json",out/f"{cid}_reconstruction.png")
    return {"output_dir":str(out),"reconstruction":str(out/f"{cid}_reconstruction.json"),"diagnostics":result.diagnostics}

def stage_validation(record: dict, cell_root: Path) -> dict:
    from opc_data.validation import validate_cell
    cid=record["pipeline_cell_id"]; data=cell_root/"01_data"/cid; recon=cell_root/"02_reconstruction"/f"{cid}_reconstruction.json"; out=cell_root/"03_validation"
    result=validate_cell(recon,
      find_one(data,[f"{cid}_sholl_Sholl_Dendrite.csv"]),
      find_one(data,[f"{cid}_sholl_Sholl_Branch_Order_Dendrite.csv"]),
      find_one(data,[f"{cid}_nearest_neighbour*_Sheet1.csv"]),
      find_one(data,[f"{cid}_angles_Sheet1.csv"]))
    dump(out/f"{cid}_validation.json",result)
    return {"output_dir":str(out),"validation":str(out/f"{cid}_validation.json")}

def passive_params(cfg:dict):
    from opc_data.passive_neuron import PassiveParameters
    return PassiveParameters(process_diameter_um=cfg["diameter"],rm_ohm_cm2=cfg["rm"],ra_ohm_cm=cfg["ra"],cm_uF_cm2=cfg["cm"],e_pas_mV=cfg["rest"])

def stage_neuron(record:dict,cell_root:Path,cfg:dict)->dict:
    from opc_data.passive_neuron import PassiveOPCCell
    cid=record["pipeline_cell_id"]; recon=cell_root/"02_reconstruction"/f"{cid}_reconstruction.json"; out=cell_root/"04_neuron"
    with PassiveOPCCell.from_json(recon,passive_params(cfg)) as cell: summary=cell.summary()
    dump(out/f"{cid}_neuron_summary.json",summary); return {"output_dir":str(out),"summary":summary}

def stage_synaptic(record:dict,cell_root:Path,cfg:dict)->dict:
    from opc_data.passive_neuron import PassiveOPCCell
    from opc_data.synaptic_simulation import (SimulationParameters, SynapseParameters, export_results, export_trace, run_single_synapse, select_representative_sites)
    cid=record["pipeline_cell_id"]; recon=cell_root/"02_reconstruction"/f"{cid}_reconstruction.json"; out=cell_root/"05_synaptic"; out.mkdir(parents=True,exist_ok=True)
    syn=SynapseParameters(tau1_ms=cfg["tau1"],tau2_ms=cfg["tau2"],weight_uS=cfg["weight"],event_time_ms=cfg["event_time"])
    sim=SimulationParameters(tstop_ms=cfg["tstop"],dt_ms=cfg["dt"])
    results=[]; sites_out=[]
    with PassiveOPCCell.from_json(recon,passive_params(cfg)) as cell:
        if not cell.validate()["ready_for_simulation"]: raise RuntimeError("Passive cell failed validation")
        for site in select_representative_sites(cell,location=syn.location):
            result,traces=run_single_synapse(cell,site,syn,sim); results.append(result); sites_out.append(asdict(site)); export_trace(out/f"{cid}_{site.class_name}_trace.csv",traces)
    export_results(out/f"{cid}_synaptic_results.csv",results); dump(out/f"{cid}_selected_sites.json",sites_out); dump(out/f"{cid}_synaptic_results.json",[asdict(r) for r in results])
    return {"output_dir":str(out),"n_sites":len(results)}

def stage_dense(record:dict,cell_root:Path,cfg:dict)->dict:
    from opc_data.passive_neuron import PassiveOPCCell
    from opc_data.synaptic_simulation import SimulationParameters, SynapseParameters
    from opc_data.dense_analysis import (select_stratified_sites, run_site_set, result_rows, write_rows, summarise_dense, plot_distance, plot_attenuation_map, sensitivity_summary)
    cid=record["pipeline_cell_id"]; recon=cell_root/"02_reconstruction"/f"{cid}_reconstruction.json"; out=cell_root/"06_dense"; out.mkdir(parents=True,exist_ok=True)
    syn=SynapseParameters(tau1_ms=cfg["tau1"],tau2_ms=cfg["tau2"],reversal_mV=0.0,weight_uS=cfg["weight"],event_time_ms=cfg["event_time"],location=0.5)
    sim=SimulationParameters(tstop_ms=cfg["dense_tstop"],dt_ms=cfg["dense_dt"],baseline_end_ms=cfg["event_time"]-1.0)
    with PassiveOPCCell.from_json(recon,passive_params(cfg)) as cell:
        sites=select_stratified_sites(cell,n_sites=cfg["dense_sites"],location=0.5,distance="radial"); results=run_site_set(cell,sites,syn,sim)
    rows=result_rows(results,{"diameter_um":cfg["diameter"],"rm_ohm_cm2":cfg["rm"]}); write_rows(out/f"{cid}_dense_results.csv",rows); summary=summarise_dense(results); dump(out/f"{cid}_dense_summary.json",summary); plot_distance(results,out); plot_attenuation_map(recon,results,out/f"{cid}_attenuation_map.png")
    sensitivity=[]
    with PassiveOPCCell.from_json(recon,passive_params(cfg)) as cell: fixed=select_stratified_sites(cell,n_sites=cfg["sensitivity_sites"],location=0.5,distance="radial")
    for diameter,rm in cfg["parameter_sets"]:
        local=dict(cfg,diameter=diameter,rm=rm)
        with PassiveOPCCell.from_json(recon,passive_params(local)) as cell: rr=run_site_set(cell,fixed,syn,sim)
        sensitivity.extend(result_rows(rr,{"diameter_um":diameter,"rm_ohm_cm2":rm}))
    write_rows(out/f"{cid}_sensitivity_results.csv",sensitivity); write_rows(out/f"{cid}_sensitivity_summary.csv",sensitivity_summary(sensitivity))
    return {"output_dir":str(out),"dense_summary":summary,"n_sensitivity_rows":len(sensitivity)}

def run_cell(record:dict,data_root:str,output_root:str,stages:list[str],force:bool,cfg:dict)->dict:
    cid=record["pipeline_cell_id"]; root=Path(output_root)/"cells"/cid; root.mkdir(parents=True,exist_ok=True); manifest_path=root/"manifest.json"
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {"cell_id":cid,"inventory_status":record["status"],"started_at":utcnow(),"stages":{}}
    funcs={"data":lambda:stage_data(record,Path(data_root),root),"reconstruction":lambda:stage_reconstruction(record,root,cfg["coordinate_tolerance"]),"validation":lambda:stage_validation(record,root),"neuron":lambda:stage_neuron(record,root,cfg),"synaptic":lambda:stage_synaptic(record,root,cfg),"dense":lambda:stage_dense(record,root,cfg)}
    for stage in stages:
        if not force and manifest["stages"].get(stage,{}).get("status")=="complete": continue
        manifest["stages"][stage]={"status":"running","started_at":utcnow()}; dump(manifest_path,manifest)
        try:
            detail=funcs[stage](); manifest["stages"][stage]={"status":"complete","finished_at":utcnow(),"detail":detail}
        except Exception as exc:
            manifest["stages"][stage]={"status":"failed","finished_at":utcnow(),"error":str(exc),"traceback":traceback.format_exc()}; dump(manifest_path,manifest); return {"cell_id":cid,"status":"failed","stage":stage,"error":str(exc)}
        dump(manifest_path,manifest)
    manifest["finished_at"]=utcnow(); dump(manifest_path,manifest); return {"cell_id":cid,"status":"complete"}

def main()->int:
    p=argparse.ArgumentParser(description="Inventory-driven OPC passive-cable pipeline")
    p.add_argument("--data-root",required=True); p.add_argument("--output-root",default="pipeline_results"); p.add_argument("--stages",default=",".join(STAGES)); p.add_argument("--cells",nargs="*"); p.add_argument("--ages",nargs="*",choices=["P10","P20","P50"]); p.add_argument("--workers",type=int,default=1); p.add_argument("--force",action="store_true"); p.add_argument("--dry-run",action="store_true"); p.add_argument("--limit",type=int)
    args=p.parse_args(); stages=[s.strip() for s in args.stages.split(",") if s.strip()]; unknown=set(stages)-set(STAGES)
    if unknown: p.error(f"Unknown stages: {sorted(unknown)}")
    out=Path(args.output_root); out.mkdir(parents=True,exist_ok=True); inv=build_inventory(args.data_root); write_reports(inv,out/"inventory")
    records=ready_records(inv,set(args.ages) if args.ages else None,set(args.cells) if args.cells else None)
    if args.limit: records=records[:args.limit]
    plan={"created_at":utcnow(),"data_root":inv["dataset_root"],"stages":stages,"workers":args.workers,"sequential_default":args.workers==1,"n_ready_cells":len(records),"cells":[r["pipeline_cell_id"] for r in records]}; dump(out/"run_plan.json",plan)
    print(f"Inventory: {inv['summary']}"); print(f"Selected ready cells: {len(records)}; workers={args.workers}")
    if args.dry_run: return 0
    cfg={"coordinate_tolerance":0.08,"diameter":0.30,"rm":20000.0,"ra":150.0,"cm":1.0,"rest":-75.0,"weight":0.00005,"tau1":0.5,"tau2":3.0,"event_time":20.0,"tstop":80.0,"dt":0.025,"dense_tstop":50.0,"dense_dt":0.05,"dense_sites":25,"sensitivity_sites":5,"parameter_sets":[[0.20,20000.0],[0.30,10000.0],[0.30,20000.0],[0.30,40000.0],[0.50,20000.0]]}
    results=[]
    if args.workers==1:
        for i,r in enumerate(records,1): print(f"[{i}/{len(records)}] {r['pipeline_cell_id']}",flush=True); results.append(run_cell(r,inv["dataset_root"],str(out),stages,args.force,cfg))
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futs={ex.submit(run_cell,r,inv["dataset_root"],str(out),stages,args.force,cfg):r for r in records}
            for fut in as_completed(futs): results.append(fut.result()); print(results[-1],flush=True)
    dump(out/"run_summary.json",{"finished_at":utcnow(),"results":results}); failed=[r for r in results if r["status"]!="complete"]
    print(f"Complete: {len(results)-len(failed)}; failed: {len(failed)}"); return 1 if failed else 0
if __name__=="__main__": raise SystemExit(main())
