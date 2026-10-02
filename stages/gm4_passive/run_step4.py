#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

from opc_data.cohort_passive import aggregate, discover_reconstructions, provenance, run_one, write_json
from opc_data.passive_neuron import PassiveParameters
from opc_data.passive_protocols import CurrentStepProtocol, TransferProtocol


def main() -> int:
    p=argparse.ArgumentParser(description="Step 4: cohort-wide passive OPC cable simulations")
    p.add_argument("--reconstruction-root", required=True, help="Step-3 output root containing *_reconstruction.json files")
    p.add_argument("--output-root", default="opc_step4_passive_results")
    p.add_argument("--cells", nargs="*", help="Optional full cell IDs, e.g. NX5_9_P10")
    p.add_argument("--ages", nargs="*", choices=["P10","P20","P50"])
    p.add_argument("--limit", type=int)
    p.add_argument("--matrix-mode", choices=["none","representative","full"], default="representative")
    p.add_argument("--representative-terminals", type=int, default=8)
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--rm", type=float, default=20000.0)
    p.add_argument("--ra", type=float, default=150.0)
    p.add_argument("--cm", type=float, default=1.0)
    p.add_argument("--diameter", type=float, default=0.30)
    p.add_argument("--rest", type=float, default=-75.0)
    args=p.parse_args()

    root=Path(args.reconstruction_root)
    out=Path(args.output_root); out.mkdir(parents=True, exist_ok=True)
    paths=discover_reconstructions(root)
    if args.cells:
        selected=set(args.cells); paths=[x for x in paths if x.name.replace("_reconstruction.json","") in selected]
    if args.ages:
        paths=[x for x in paths if any(x.name.startswith("") and ("_"+age+"_reconstruction.json") in x.name for age in args.ages)]
    if args.limit: paths=paths[:args.limit]

    params=PassiveParameters(rm_ohm_cm2=args.rm,ra_ohm_cm=args.ra,cm_uF_cm2=args.cm,e_pas_mV=args.rest,process_diameter_um=args.diameter)
    current=CurrentStepProtocol(); transfer=TransferProtocol()
    write_json(out/"provenance.json", provenance(params,current,transfer))
    write_json(out/"run_plan.json", {"reconstruction_root":str(root.resolve()),"output_root":str(out.resolve()),"n_cells":len(paths),"cells":[x.name.replace("_reconstruction.json","") for x in paths],"matrix_mode":args.matrix_mode,"representative_terminals":args.representative_terminals})
    print(f"Selected {len(paths)} reconstructions")
    if args.dry_run: return 0

    results=[]
    for i,path in enumerate(paths,1):
        cell_id=path.name.replace("_reconstruction.json","")
        summary_path=out/"cells"/cell_id/f"{cell_id}_passive_summary.json"
        if summary_path.exists() and not args.force:
            import json
            results.append(json.loads(summary_path.read_text(encoding="utf-8")))
            print(f"[{i}/{len(paths)}] {cell_id}: cached")
            continue
        print(f"[{i}/{len(paths)}] {cell_id}", flush=True)
        results.append(run_one(path,out,params,current,transfer,args.representative_terminals,args.matrix_mode))
    aggregate(results,out)
    failed=[r for r in results if r.get("status")=="failed"]
    print(f"Complete: {len(results)-len(failed)}; failed: {len(failed)}")
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
