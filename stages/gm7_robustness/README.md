# GM7 — Calibrated sensitivity and robustness analysis

GM7 generalises the original dense three-cell sensitivity milestone to every GM3-accepted OPC. It asks whether the GM5/GM6 conclusions remain stable when uncertain passive and synaptic parameters are varied.

The baseline is now the GM4.5 calibration:

```text
P10  29.741010083005232 kΩ·cm²
P20  10.094385601286076 kΩ·cm²
P50   2.394438696918089 kΩ·cm²
```

The (R_m) sensitivity levels are 0.5×, 0.75×, 1×, 1.5× and 2× each age-specific baseline. This gives every age the same proportional perturbation and ensures its calibrated value is included. All other parameter sweeps retain their original absolute levels.

GM7 also incorporates the validated GM6 spatial-normalization correction: simultaneous inputs are divided by the sum of isolated EPSPs measured at those exact same sites, and the one-input spatial ratio is one by construction.

## Default design

The default run uses a baseline plus one-factor-at-a-time sweeps of:

- membrane resistance `Rm` relative to the calibrated age-specific baseline;
- axial resistivity `Ra`;
- membrane capacitance `Cm`;
- process diameter;
- synaptic conductance;
- synaptic rise time;
- synaptic decay time.

There are 36 conditions per cell (one baseline plus 35 perturbations). Each condition repeats the GM6 single-input, temporal-summation and spatial-summation protocols. An optional four-factor interaction grid is available for a deliberately restricted representative subset; it is disabled by default because it is much more expensive.

## Install

```bash
python -m pip install -r requirements.txt
```

## Inspect the workload

```bash
python run_gm7.py \
  --reconstruction-root ../3-opc_step3_validation \
  --output-root gm7_calibrated_results \
  --dry-run
```

## Pilot

```bash
python run_gm7.py \
  --reconstruction-root ../3-opc_step3_validation \
  --output-root gm7_calibrated_pilot \
  --limit 3
```

## Full one-factor cohort screen

```bash
python run_gm7.py \
  --reconstruction-root ../3-opc_step3_validation \
  --output-root gm7_calibrated_results
```

## Validate

```bash
python validate_calibrated_gm7.py --output-root gm7_calibrated_results
```

Expected:

```text
PASS: 35 calibrated cells, 1260 condition rows; P10=12, P20=12, P50=11
```

The validator checks condition completeness, zero failures, each cell's calibrated baseline, the proportional Rm sweep, and exact one-input spatial normalization in every condition.

## Optional interaction design

The interaction design remains disabled by default and is not required for the calibrated paper analysis. Use it only after the one-factor screen and only on an explicitly selected subset:

```bash
python run_gm7.py \
  --reconstruction-root /path/to/representative/reconstructions \
  --output-root gm7_interactions \
  --enable-interactions
```

## Outputs

- `cells/<cell_id>/sensitivity_results.csv`
- `cells/<cell_id>/failed_conditions.csv`
- `cells/<cell_id>/manifest.json`
- `population/all_sensitivity_results.csv`
- `population/age_factor_summary.csv`
- `population/robustness_summary.csv`
- `population/failed_conditions.csv`
- `run_plan.json`, `run_summary.json`, `provenance.json`

The primary robustness table reports each metric relative to that cell's baseline, thereby separating between-cell morphology variation from parameter perturbations.

## Interpretation

This stage establishes whether qualitative developmental conclusions are robust over plausible parameter ranges. It does not identify the true biological values of the passive or synaptic parameters. Parameter ranges are explicit in `config/default_config.json` and should be revised when experimental estimates become available.

Keep the original `gm7_results` unchanged as the fixed-parameter morphology-only sensitivity analysis. Use a new `gm7_calibrated_results` directory for this run. GM4.5 does not need to be present at runtime because the calibrated values and provenance are frozen in the configuration.
