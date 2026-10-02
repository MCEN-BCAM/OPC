import json
from pathlib import Path
p=Path(__file__).parents[1]/'config/default_config.json'
c=json.loads(p.read_text())
assert 0<c['synapse']['tau1_ms']<c['synapse']['tau2_ms']
assert c['protocols']['site_quantiles']==sorted(c['protocols']['site_quantiles'])
assert all(x>0 for x in c['protocols']['temporal_intervals_ms'])
print('configuration checks passed')
