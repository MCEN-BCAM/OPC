import json
from pathlib import Path
cfg=json.loads((Path(__file__).parents[1]/'config/default_config.json').read_text())
assert cfg['baseline']['synapse']['tau1_ms'] < cfg['baseline']['synapse']['tau2_ms']
assert all(v > 0 for levels in cfg['one_factor_sweeps'].values() for v in levels)
assert 1 + sum(len(v) for v in cfg['one_factor_sweeps'].values()) == 36
assert 1.0 in cfg['one_factor_sweeps']['rm_multiplier']
assert cfg['baseline']['passive']['ra_ohm_cm'] in cfg['one_factor_sweeps']['ra_ohm_cm']
assert cfg['baseline']['passive']['cm_uF_cm2'] in cfg['one_factor_sweeps']['cm_uF_cm2']
assert cfg['baseline']['passive']['process_diameter_um'] in cfg['one_factor_sweeps']['process_diameter_um']
assert cfg['baseline']['synapse']['weight_uS'] in cfg['one_factor_sweeps']['weight_uS']
print('configuration checks passed: 36 calibrated conditions per cell')
