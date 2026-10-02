#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf tests/synthetic_step4 tests/synthetic_atlas
python tests/make_synthetic_step4.py
python run_gm5.py --step4-root tests/synthetic_step4 --output-root tests/synthetic_atlas
test -f tests/synthetic_atlas/index.html
test -f tests/synthetic_atlas/tables/accepted_cell_metrics.csv
python - <<'PY'
import pandas as pd
x=pd.read_csv('tests/synthetic_atlas/tables/accepted_cell_metrics.csv')
assert len(x)==9, len(x)
print('Smoke test passed with', len(x), 'accepted synthetic cells')
PY
