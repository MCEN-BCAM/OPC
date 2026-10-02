from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import math, gc
import numpy as np
from neuron import h
from .passive_neuron import PassiveOPCCell
h.load_file('stdrun.hoc')

@dataclass(frozen=True)
class SynapseParameters:
    tau1_ms: float=0.5; tau2_ms: float=3.0; reversal_mV: float=0.0; weight_uS: float=0.00005
@dataclass(frozen=True)
class SimulationParameters:
    dt_ms: float=0.025; tstop_ms: float=120.0; v_init_mV: float=-75.0; baseline_end_ms: float=19.0
@dataclass(frozen=True)
class ProtocolGrid:
    single_event_ms: float=20.0
    temporal_intervals_ms: tuple[float,...]=(2.0,5.0,10.0,20.0,50.0)
    spatial_counts: tuple[int,...]=(1,2,4,8)
    site_quantiles: tuple[float,...]=(0.15,0.50,0.85)
    max_candidate_sites: int=12


def _path_sites(cell: PassiveOPCCell, quantiles: tuple[float,...], x: float=0.5)->list[dict[str,Any]]:
    vals=[]
    for sid,m in cell.metadata_by_segment.items():
        d=cell.path_distance_um(sid,x)
        if d is not None and math.isfinite(d): vals.append((sid,float(d)))
    if not vals: raise ValueError('No process sites with finite path distance')
    vals.sort(key=lambda z:z[1]); arr=np.array([v for _,v in vals])
    used=set(); out=[]; names=['proximal','intermediate','distal']
    for name,q in zip(names,quantiles):
        target=float(np.quantile(arr,q)); sid,d=min((z for z in vals if z[0] not in used), key=lambda z:abs(z[1]-target))
        used.add(sid); m=cell.metadata_by_segment[sid]
        out.append({'class_name':name,'segment_id':sid,'location':x,'path_distance_um':d,'radial_distance_um':cell.radial_distance_um(sid,x),'branch_order':m.order,'tree':m.tree,'terminal_type':m.terminal_type})
    return out

def _run(cell:PassiveOPCCell, sites:list[dict[str,Any]], event_times:list[list[float]], syn:SynapseParameters, sim:SimulationParameters)->dict[str,Any]:
    objects=[]
    scheduled_events=[]
    tvec=h.Vector().record(h._ref_t); svec=h.Vector().record(cell.soma(0.5)._ref_v)
    local_vectors=[]
    for site,times in zip(sites,event_times):
        sec=cell.sections_by_segment[int(site['segment_id'])]; target=sec(float(site['location']))
        pp=h.Exp2Syn(target); pp.tau1=syn.tau1_ms; pp.tau2=syn.tau2_ms; pp.e=syn.reversal_mV

        # Use a source-less NetCon and schedule events explicitly. This is
        # equivalent to VecStim for arbitrary event-time lists, while relying
        # only on standard NEURON mechanisms.
        nc=h.NetCon(None,pp); nc.delay=0.; nc.weight[0]=syn.weight_uS
        scheduled_events.append((nc,[float(t) for t in times]))

        lv=h.Vector().record(target._ref_v); local_vectors.append(lv)
        objects.extend([pp,nc])

    h.cvode_active(0); h.dt=sim.dt_ms; h.steps_per_ms=1./sim.dt_ms; h.tstop=sim.tstop_ms
    h.finitialize(sim.v_init_mV)

    # Schedule events after initialization, because finitialize() can clear
    # pending events from NEURON's event queue.
    for nc,times in scheduled_events:
        for event_time in times:
            nc.event(event_time)

    h.continuerun(sim.tstop_ms)
    t=np.asarray(tvec); soma=np.asarray(svec); locals_=[np.asarray(v) for v in local_vectors]
    base_mask=t<=sim.baseline_end_ms; b=float(np.mean(soma[base_mask])); post=t>=min(min(x) for x in event_times)
    peak=float(np.max(soma[post])); peak_i=np.where(post)[0][int(np.argmax(soma[post]))]
    result={'soma_baseline_mV':b,'soma_peak_mV':peak,'soma_epsp_mV':peak-b,'soma_peak_time_ms':float(t[peak_i]),'time_ms':t,'soma_mV':soma,'local_mV':locals_}
    del objects,scheduled_events,tvec,svec,local_vectors; gc.collect(); return result

def run_cell_protocols(cell:PassiveOPCCell, syn:SynapseParameters, sim:SimulationParameters, grid:ProtocolGrid)->tuple[list[dict[str,Any]],list[dict[str,Any]],dict[str,np.ndarray]]:
    sites=_path_sites(cell,grid.site_quantiles)
    rows=[]; traces={}
    singles={}
    for site in sites:
        r=_run(cell,[site],[[grid.single_event_ms]],syn,sim); amp=r['soma_epsp_mV']; singles[site['class_name']]=amp
        rows.append({'protocol':'single','site_class':site['class_name'],**site,'n_synapses':1,'n_events':1,'interval_ms':None,'soma_epsp_mV':amp,'normalised_to_proximal':None,'summation_ratio':1.0,'peak_time_ms':r['soma_peak_time_ms']})
        traces[f"single_{site['class_name']}"]=np.column_stack([r['time_ms'],r['soma_mV']])
    prox=max(singles.get('proximal',0),1e-12)
    for row in rows: row['normalised_to_proximal']=row['soma_epsp_mV']/prox
    distal=next(s for s in sites if s['class_name']=='distal')
    for isi in grid.temporal_intervals_ms:
        times=[grid.single_event_ms,grid.single_event_ms+isi]
        r=_run(cell,[distal],[times],syn,sim); single=max(singles['distal'],1e-12)
        rows.append({'protocol':'temporal','site_class':'distal',**distal,'n_synapses':1,'n_events':2,'interval_ms':isi,'soma_epsp_mV':r['soma_epsp_mV'],'normalised_to_proximal':r['soma_epsp_mV']/prox,'summation_ratio':r['soma_epsp_mV']/(2*single),'peak_time_ms':r['soma_peak_time_ms']})
    candidates=[]
    for sid,m in cell.metadata_by_segment.items():
        d=cell.path_distance_um(sid,0.5)
        if d is not None: candidates.append({'class_name':'distributed','segment_id':sid,'location':0.5,'path_distance_um':float(d),'radial_distance_um':cell.radial_distance_um(sid,0.5),'branch_order':m.order,'tree':m.tree,'terminal_type':m.terminal_type})
    candidates=sorted(candidates,key=lambda s:s['path_distance_um'])
    if len(candidates)>grid.max_candidate_sites:
        idx=np.linspace(0,len(candidates)-1,grid.max_candidate_sites).round().astype(int); candidates=[candidates[i] for i in sorted(set(idx))]
    # The spatial prediction must use isolated EPSPs from the exact same sites
    # activated simultaneously. This is the validated GM6 correction.
    candidate_single_epsps: dict[int,float] = {}
    candidate_single_peaks: dict[int,float] = {}
    for site in candidates:
        isolated = _run(cell,[site],[[grid.single_event_ms]],syn,sim)
        sid = int(site['segment_id'])
        candidate_single_epsps[sid] = float(isolated['soma_epsp_mV'])
        candidate_single_peaks[sid] = float(isolated['soma_peak_time_ms'])
    for n in grid.spatial_counts:
        chosen=candidates[:min(n,len(candidates))]
        if not chosen: continue
        component_ids=[int(s['segment_id']) for s in chosen]
        component_epsps=[candidate_single_epsps[sid] for sid in component_ids]
        denom=float(sum(component_epsps))
        if len(chosen)==1:
            observed=float(component_epsps[0]); peak_time=float(candidate_single_peaks[component_ids[0]])
        else:
            simultaneous=_run(cell,chosen,[[grid.single_event_ms] for _ in chosen],syn,sim)
            observed=float(simultaneous['soma_epsp_mV']); peak_time=float(simultaneous['soma_peak_time_ms'])
        rows.append({'protocol':'spatial','site_class':'distributed','segment_id':None,'location':0.5,
            'path_distance_um':float(np.mean([s['path_distance_um'] for s in chosen])),
            'radial_distance_um':None,'branch_order':None,'tree':None,'terminal_type':'mixed',
            'n_synapses':len(chosen),'n_events':len(chosen),'interval_ms':0.0,
            'soma_epsp_mV':observed,'linear_prediction_mV':denom,
            'component_segment_ids':';'.join(str(sid) for sid in component_ids),
            'component_single_epsps_mV':';'.join(f'{amp:.12g}' for amp in component_epsps),
            'normalised_to_proximal':observed/prox,
            'summation_ratio':observed/denom if denom>0 else None,'peak_time_ms':peak_time})
    return rows,sites,traces
