from __future__ import annotations
import json, traceback, platform, sys
from pathlib import Path
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from .io import write_json,write_csv
from .passive_neuron import PassiveOPCCell,PassiveParameters
from .protocols import SynapseParameters,SimulationParameters,ProtocolGrid,run_cell_protocols

def now(): return datetime.now(timezone.utc).isoformat()
def age(cell_id): return next((a for a in ('P10','P20','P50') if cell_id.endswith('_'+a)),'UNKNOWN')
def discover(root:Path): return sorted(root.rglob('*_reconstruction.json'))

def run_one(path:Path,outroot:Path,pp:PassiveParameters,sp:SynapseParameters,sim:SimulationParameters,grid:ProtocolGrid)->dict[str,Any]:
    data=json.loads(path.read_text()); cid=str(data['cell_id']); out=outroot/'cells'/cid; out.mkdir(parents=True,exist_ok=True)
    manifest={'cell_id':cid,'age_group':age(cid),'status':'running','started_at':now(),'reconstruction':str(path),'passive_parameters':asdict(pp)}; write_json(out/'manifest.json',manifest)
    try:
        with PassiveOPCCell(data,pp).build() as cell:
            structural=cell.validate(); rest=cell.resting_smoke_test()
            if not structural['ready_for_simulation'] or not rest['stable_at_rest']: raise RuntimeError('Structural or resting-state QC failed')
            rows,sites,traces=run_cell_protocols(cell,sp,sim,grid)
            for r in rows: r.update(cell_id=cid,age_group=age(cid))
            write_csv(out/f'{cid}_synaptic_protocols.csv',rows); write_json(out/f'{cid}_selected_sites.json',sites)
            for name,a in traces.items(): write_csv(out/f'{cid}_{name}_trace.csv',[{'time_ms':x,'soma_mV':y} for x,y in a])
            singles={r['site_class']:r['soma_epsp_mV'] for r in rows if r['protocol']=='single'}
            temporal=[r for r in rows if r['protocol']=='temporal']; spatial=[r for r in rows if r['protocol']=='spatial']
            spatial_nontrivial=[r for r in spatial if int(r.get('n_synapses') or 0)>1]
            spatial_n8=next((r['summation_ratio'] for r in spatial if int(r.get('n_synapses') or 0)==8),None)
            summary={
                'cell_id':cid,
                'age_group':age(cid),
                'status':'complete',
                'calibrated_rm_kohm_cm2':pp.rm_ohm_cm2/1000.0,
                'proximal_epsp_mV':singles.get('proximal'),
                'intermediate_epsp_mV':singles.get('intermediate'),
                'distal_epsp_mV':singles.get('distal'),
                'distal_to_proximal_ratio':singles.get('distal')/singles.get('proximal') if singles.get('proximal') else None,
                'max_temporal_summation_ratio':max((r['summation_ratio'] for r in temporal if r['summation_ratio'] is not None),default=None),
                # Retained for backward compatibility.  With exact matched-site
                # normalisation this value is normally 1 because N=1 is included.
                'max_spatial_summation_ratio':max((r['summation_ratio'] for r in spatial if r['summation_ratio'] is not None),default=None),
                'max_spatial_summation_ratio_n_gt_1':max((r['summation_ratio'] for r in spatial_nontrivial if r['summation_ratio'] is not None),default=None),
                'spatial_summation_ratio_n8':spatial_n8,
                'n_protocol_rows':len(rows),
            }
            write_json(out/f'{cid}_synaptic_summary.json',summary); manifest.update(status='complete',finished_at=now(),summary=summary); write_json(out/'manifest.json',manifest); return summary
    except Exception as e:
        manifest.update(status='failed',finished_at=now(),error=str(e),traceback=traceback.format_exc()); write_json(out/'manifest.json',manifest); return {'cell_id':cid,'age_group':age(cid),'status':'failed','error':str(e)}

def aggregate(results:list[dict[str,Any]],root:Path):
    good=[r for r in results if r.get('status')=='complete']; bad=[r for r in results if r.get('status')!='complete']; write_csv(root/'population/cell_level_synaptic_metrics.csv',good); write_csv(root/'population/failed_cells.csv',bad)
    rows=[]
    metrics=['proximal_epsp_mV','intermediate_epsp_mV','distal_epsp_mV','distal_to_proximal_ratio','max_temporal_summation_ratio','max_spatial_summation_ratio','max_spatial_summation_ratio_n_gt_1','spatial_summation_ratio_n8']
    for a in ('P10','P20','P50'):
        ss=[x for x in good if x['age_group']==a]
        for m in metrics:
            v=[float(x[m]) for x in ss if x.get(m) is not None]
            if v:
                import statistics as st
                rows.append({'age_group':a,'metric':m,'n':len(v),'mean':st.mean(v),'sd':st.stdev(v) if len(v)>1 else 0.,'median':st.median(v),'minimum':min(v),'maximum':max(v)})
    write_csv(root/'population/age_group_summary.csv',rows); write_json(root/'run_summary.json',{'finished_at':now(),'n_complete':len(good),'n_failed':len(bad),'results':results})

def provenance(pp,sp,sim,grid):
    try:
        from neuron import h; nv=str(h.nrnversion())
    except Exception as e: nv=f'unavailable: {e}'
    return {'created_at':now(),'python':sys.version,'platform':platform.platform(),'neuron':nv,'passive_parameters':asdict(pp),'synapse_parameters':asdict(sp),'simulation_parameters':asdict(sim),'protocol_grid':asdict(grid)}
