from __future__ import annotations
from dataclasses import asdict
from itertools import product
from typing import Any, Iterable
from .passive_neuron import PassiveParameters
from .protocols import SynapseParameters, SimulationParameters, ProtocolGrid

PASSIVE_FIELDS = set(PassiveParameters.__dataclass_fields__)
SYNAPTIC_FIELDS = set(SynapseParameters.__dataclass_fields__)

def build_objects(cfg: dict[str, Any]):
    b=cfg['baseline']
    pp=PassiveParameters(**b['passive'])
    sp=SynapseParameters(**b['synapse'])
    sim=SimulationParameters(**b['simulation'])
    p=dict(b['protocols'])
    p['temporal_intervals_ms']=tuple(p['temporal_intervals_ms'])
    p['spatial_counts']=tuple(p['spatial_counts'])
    p['site_quantiles']=tuple(p['site_quantiles'])
    grid=ProtocolGrid(**p)
    return pp,sp,sim,grid

def one_factor_conditions(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    pp,sp,_,_=build_objects(cfg)
    base={**asdict(pp),**asdict(sp)}
    out=[{'condition_id':'baseline','design':'baseline','factor':None,'level':None,'values':base}]
    for factor, levels in cfg['one_factor_sweeps'].items():
        if factor not in base: raise KeyError(f'Unknown factor: {factor}')
        for level in levels:
            values=dict(base); values[factor]=level
            out.append({'condition_id':f'{factor}={level:g}','design':'one_factor','factor':factor,'level':level,'values':values})
    return out

def interaction_conditions(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    design=cfg.get('interaction_design',{})
    if not design.get('enabled',False): return []
    pp,sp,_,_=build_objects(cfg); base={**asdict(pp),**asdict(sp)}
    factors=design['factors']; keys=list(factors)
    out=[]
    for i,levels in enumerate(product(*(factors[k] for k in keys))):
        values=dict(base); values.update(dict(zip(keys,levels)))
        out.append({'condition_id':f'interaction_{i:04d}','design':'interaction','factor':'×'.join(keys),'level':None,'values':values})
    return out

def split_parameters(values: dict[str, Any]) -> tuple[PassiveParameters,SynapseParameters]:
    return PassiveParameters(**{k:v for k,v in values.items() if k in PASSIVE_FIELDS}), SynapseParameters(**{k:v for k,v in values.items() if k in SYNAPTIC_FIELDS})
