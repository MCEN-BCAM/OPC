# GM6 — Calibrated cohort-wide synaptic integration atlas

GM6 generalises the original three-cell synaptic milestone to every validated OPC reconstruction. It runs matched conductance-based excitatory protocols on each passive NEURON morphology and exports cell-level and P10/P20/P50 summaries.

This edition uses the GM4.5 age-specific passive calibration:

```text
P10  29.741010083005232 kΩ·cm²
P20  10.094385601286076 kΩ·cm²
P50   2.394438696918089 kΩ·cm²
```

Only `Rm` changes by age. Axial resistivity, capacitance, leak reversal, diameter, synaptic kinetics, synaptic weight, placement rules, simulation settings, and the corrected protocols are unchanged.

## Protocols

1. **Single-site efficacy:** one identical Exp2Syn event at proximal, intermediate and distal path-distance quantiles.
2. **Temporal summation:** two distal events separated by 2, 5, 10, 20 or 50 ms.
3. **Spatial summation:** simultaneous activation at 1, 2, 4 or 8 distributed sites. The linear prediction is the sum of isolated EPSPs generated at the exact same selected sites; consequently, the one-input spatial ratio is exactly 1 by construction.

Primary outputs include somatic EPSP amplitude, distal/proximal efficacy, normalised efficacy, peak delay and temporal/spatial summation ratios. The default synaptic strength is deliberately small to remain in the approximately linear passive regime.

## Install

```bash
python -m pip install -r requirements.txt
```

## Folder layout

```text
project/
├── 3-opc_step3_validation/
└── 6-opc_gm6_synaptic_atlas_calibrated/
```

GM4.5 does not need to be present at runtime because its frozen parameters are recorded in `config/default_config.json`.

## Dry run

```bash
python run_gm6.py --reconstruction-root ../3-opc_step3_validation --output-root gm6_calibrated_results --dry-run
```

## Three-cell pilot

```bash
python run_gm6.py --reconstruction-root ../3-opc_step3_validation --output-root gm6_calibrated_pilot --limit 3
```

## Full cohort

```bash
python run_gm6.py --reconstruction-root ../3-opc_step3_validation --output-root gm6_calibrated_results
```

## Validation

```bash
python validate_calibrated_gm6.py --output-root gm6_calibrated_results
```

Expected:

```text
PASS: 35 calibrated cells, 140 spatial rows; P10=12, P20=12, P50=11
```

The validator also checks all 420 protocol rows, age-specific Rm assignments, stored spatial ratios, exact matched-site denominators, and the required one-input ratio of one.

## Output structure

- `cells/<cell_id>/`: selected sites, protocol table, traces, summary, manifest
- `population/cell_level_synaptic_metrics.csv`
- `population/age_group_summary.csv`
- `population/failed_cells.csv`
- `run_plan.json`, `provenance.json`, `run_summary.json`
- Each spatial row also records `linear_prediction_mV`, the selected segment IDs, and the matched isolated component EPSPs used in its denominator.

## Interpretation safeguards

GM6 now tests integration under experimentally calibrated age-specific passive resistance and a shared synaptic parameter set. It does not establish the true biological synaptic conductance or receptor kinetics. Those uncertainties are handled in GM7 sensitivity analysis. Run GM6 only on GM3-accepted reconstructions and inspect failed-cell manifests before population inference.

Keep the original corrected fixed-parameter GM6 results unchanged as the morphology-only comparison.


## Corrected spatial normalisation (2026-08)

Earlier GM6 output approximated the linear spatial prediction by assigning each distributed site the response of the nearest proximal/intermediate/distal reference site. This could make the one-synapse ratio differ slightly from one. The corrected implementation first stimulates every selected distributed site in isolation and then uses

```text
spatial ratio = simultaneous EPSP / sum(exact matched-site isolated EPSPs)
```

Run `python check_spatial_normalisation.py --output-root <GM6_OUTPUT>` after a test or cohort run. It verifies that every one-input spatial ratio equals one within numerical tolerance and that stored ratios match the stored linear predictions.
