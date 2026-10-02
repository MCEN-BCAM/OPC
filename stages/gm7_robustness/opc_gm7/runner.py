from __future__ import annotations
import csv, json, math, platform, traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
from .design import build_objects, one_factor_conditions, interaction_conditions, split_parameters
from .passive_neuron import PassiveOPCCell
from .protocols import run_cell_protocols

def _now(): return datetime.now(timezone.utc).isoformat()
def _write_json(p:Path,x:Any): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,default=str),encoding='utf-8')
def _write_csv(p:Path,rows:list[dict[str,Any]]):
    p.parent.mkdir(parents=True,exist_ok=True)
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def discover(root:Path)->list[Path]:
    paths=[]
    for p in root.rglob('*.json'):
        try:
            d=json.loads(p.read_text(encoding='utf-8'))
            if isinstance(d,dict) and 'cell_id' in d and ('segments' in d or 'reconstruction' in d): paths.append(p)
        except Exception: pass
    return sorted(set(paths))

def infer_age(path:Path,data:dict[str,Any])->str:
    text=' '.join([str(path),str(data.get('age_group','')),str(data.get('group','')),str(data.get('cell_id',''))]).upper()
    for age in ('P10','P20','P50'):
        if age in text: return age
    return 'UNKNOWN'

def _summarise_protocol(rows:list[dict[str,Any]])->dict[str,float]:
    singles={r.get('site_class'):float(r['soma_epsp_mV']) for r in rows if r.get('protocol')=='single'}
    temporal=[r for r in rows if r.get('protocol')=='temporal']
    spatial=[r for r in rows if r.get('protocol')=='spatial']
    return {
      'proximal_epsp_mV':singles.get('proximal',math.nan),
      'intermediate_epsp_mV':singles.get('intermediate',math.nan),
      'distal_epsp_mV':singles.get('distal',math.nan),
      'distal_to_proximal_ratio':singles.get('distal',math.nan)/max(singles.get('proximal',math.nan),1e-12),
      'temporal_ratio_max':max((float(r.get('summation_ratio',math.nan)) for r in temporal),default=math.nan),
      'spatial_ratio_n1':next((float(r.get('summation_ratio',math.nan)) for r in spatial if int(r.get('n_synapses',0))==1),math.nan),
      'spatial_ratio_n8':next((float(r.get('summation_ratio',math.nan)) for r in spatial if int(r.get('n_synapses',0))==8),math.nan)
    }

def run_cell(path:Path,out:Path,cfg:dict[str,Any],conditions:list[dict[str,Any]])->dict[str,Any]:
    data=json.loads(path.read_text(encoding='utf-8')); cell_id=str(data['cell_id']); age=infer_age(path,data)
    cell_dir=out/'cells'/cell_id; cell_dir.mkdir(parents=True,exist_ok=True)
    _,_,sim,grid=build_objects(cfg); qc=cfg['qc']; results=[]; failures=[]
    baseline_summary=None
    for cond in conditions:
        try:
            pp,sp=split_parameters(cond['values']); cell=PassiveOPCCell(data,pp); cell.build()
            rows,sites,_=run_cell_protocols(cell,sp,sim,grid); summary=_summarise_protocol(rows)
            if cond['condition_id']=='baseline': baseline_summary=summary
            row={'cell_id':cell_id,'age_group':age,**{k:v for k,v in cond.items() if k!='values'},**cond['values'],**summary,'status':'complete'}
            if not (qc['minimum_soma_epsp_mV'] <= summary['proximal_epsp_mV'] <= qc['maximum_soma_epsp_mV']): row['qc_warning']='proximal_epsp_out_of_range'
            results.append(row); cell.delete()
        except Exception as e:
            failures.append({'cell_id':cell_id,'age_group':age,'condition_id':cond['condition_id'],'error_type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc()})
    if baseline_summary:
        for r in results:
            for metric,b in baseline_summary.items():
                v=r.get(metric,math.nan); r[f'{metric}_relative_to_baseline']=v/b if math.isfinite(v) and math.isfinite(b) and abs(b)>1e-12 else math.nan
    _write_csv(cell_dir/'sensitivity_results.csv',results); _write_csv(cell_dir/'failed_conditions.csv',failures)
    manifest={'cell_id':cell_id,'age_group':age,'source':str(path),
              'baseline_rm_kohm_cm2':cfg.get('active_baseline_rm_kohm_cm2'),
              'status':'complete' if results else 'failed','n_complete':len(results),'n_failed':len(failures),'created_utc':_now()}
    _write_json(cell_dir/'manifest.json',manifest); return {'manifest':manifest,'rows':results,'failures':failures}

def aggregate(all_results:list[dict[str,Any]],out:Path):
    rows=[x for r in all_results for x in r['rows']]; failures=[x for r in all_results for x in r['failures']]
    _write_csv(out/'population'/'all_sensitivity_results.csv',rows); _write_csv(out/'population'/'failed_conditions.csv',failures)
    summary=[]
    metrics=['proximal_epsp_mV','distal_epsp_mV','distal_to_proximal_ratio','temporal_ratio_max','spatial_ratio_n8']
    groups={}
    for r in rows: groups.setdefault((r['age_group'],r['factor'],r['level']),[]).append(r)
    for (age,factor,level),rs in groups.items():
        item={'age_group':age,'factor':factor,'level':level,'n':len(rs)}
        for m in metrics:
            vals=np.array([float(x[m]) for x in rs if x.get(m) not in ('',None) and math.isfinite(float(x[m]))])
            item[f'{m}_median']=float(np.median(vals)) if vals.size else math.nan
            item[f'{m}_q25']=float(np.quantile(vals,.25)) if vals.size else math.nan
            item[f'{m}_q75']=float(np.quantile(vals,.75)) if vals.size else math.nan
        summary.append(item)
    _write_csv(out/'population'/'age_factor_summary.csv',summary)
    robustness=[]
    for (age,factor),rs in {}.items(): pass
    for age in sorted(set(r['age_group'] for r in rows)):
      for factor in sorted(set(str(r['factor']) for r in rows if r['factor'] not in (None,''))):
        fr=[r for r in rows if r['age_group']==age and str(r['factor'])==factor]
        for m in metrics:
          rel=np.array([float(r.get(f'{m}_relative_to_baseline',math.nan)) for r in fr]); rel=rel[np.isfinite(rel)]
          robustness.append({'age_group':age,'factor':factor,'metric':m,'n':int(rel.size),'median_relative_to_baseline':float(np.median(rel)) if rel.size else math.nan,'min_relative_to_baseline':float(np.min(rel)) if rel.size else math.nan,'max_relative_to_baseline':float(np.max(rel)) if rel.size else math.nan,'robust_within_25_percent':bool(np.all((rel>=.75)&(rel<=1.25))) if rel.size else False})
    _write_csv(out/'population'/'robustness_summary.csv',robustness)
    _write_json(out/'run_summary.json',{'created_utc':_now(),'n_cells':len(all_results),'n_conditions_complete':len(rows),'n_conditions_failed':len(failures)})

def provenance(cfg:dict[str,Any],n_conditions:int)->dict[str,Any]:
    return {'created_utc':_now(),'python':platform.python_version(),'platform':platform.platform(),'n_conditions_per_cell':n_conditions,'configuration':cfg}
