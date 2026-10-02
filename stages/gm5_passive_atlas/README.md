# GM5 — Calibrated passive electrophysiology atlas

GM5 converts completed Step-4 cohort simulations into a quality-controlled, browsable electrophysiology atlas. It **does not rerun NEURON** and does not change the simulations. It consumes the saved Step-4 JSON and CSV outputs.

This calibrated edition adds a separate preparation command that calls the original GM4 engine with the age-specific membrane resistivities inferred by GM4.5. The atlas implementation itself remains unchanged.

## Calibrated parameters

```text
P10  29.741010083005232 kΩ·cm²
P20  10.094385601286076 kΩ·cm²
P50   2.394438696918089 kΩ·cm²
```

All other GM4 passive parameters and protocols remain fixed. The exact values and provenance are recorded in `config/calibrated_passive_parameters.json`.

## Scientific products

- explicit per-cell acceptance/exclusion table;
- cell-level passive metrics for P10, P20 and P50;
- input resistance, membrane time constant, cable-distance and attenuation distributions;
- attenuation-versus-distance profiles;
- morphology–electrophysiology relationships;
- descriptive statistics with bootstrap confidence intervals;
- Kruskal–Wallis and Holm-corrected pairwise Mann–Whitney comparisons;
- Cliff's delta effect sizes;
- one HTML report per OPC and one cohort-level atlas index;
- PNG and vector PDF figures for later manuscript assembly.

## Prerequisite

Complete Step 4 locally first. The supplied directory should contain:

```text
STEP4_ROOT/
  cells/<CELL_ID>/
    manifest.json
    <CELL_ID>_passive_summary.json
    <CELL_ID>_structural_validation.json
    <CELL_ID>_resting_test.json
    <CELL_ID>_current_step_summary.json
    <CELL_ID>_soma_trace.csv
    <CELL_ID>_attenuation_map.csv
    <CELL_ID>_bidirectional_transfer.csv
    <CELL_ID>_transfer_matrix.csv
```

## Installation

```bash
cd opc_gm5_passive_atlas
python -m pip install -r requirements.txt
```

## Folder layout

Keep the original repositories beside this one:

```text
project/
├── 3-opc_step3_validation/
├── 4-opc_step4_cohort_passive/
└── 5-opc_gm5_passive_atlas/
```

## Run the calibrated workflow

First check the planned age-specific assignments without simulating:

```bash
python run_calibrated_step4.py \
  --gm4-root ../4-opc_step4_cohort_passive \
  --reconstruction-root ../3-opc_step3_validation \
  --output-root gm4_calibrated_results \
  --dry-run
```

Run a one-cell pilot:

```bash
python run_calibrated_step4.py \
  --gm4-root ../4-opc_step4_cohort_passive \
  --reconstruction-root ../3-opc_step3_validation \
  --output-root gm4_calibrated_pilot \
  --limit 1
```

Run the full 35-cell calibrated GM4 cohort:

```bash
python run_calibrated_step4.py \
  --gm4-root ../4-opc_step4_cohort_passive \
  --reconstruction-root ../3-opc_step3_validation \
  --output-root gm4_calibrated_results
```

Validate the complete calibrated cohort:

```bash
python validate_calibrated_step4.py --step4-root gm4_calibrated_results
```

Expected:

```text
PASS: 35 calibrated cells; P10=12, P20=12, P50=11
```

Finally build the unchanged GM5 atlas from those calibrated outputs:

```bash
python run_gm5.py \
  --step4-root gm4_calibrated_results \
  --output-root gm5_calibrated_atlas_results
```

Then open:

```text
gm5_calibrated_atlas_results/index.html
```

Do not overwrite the original `opc_step4_passive_results` or `opc_gm5_passive_atlas_results` directories. They remain the fixed-parameter morphology-only comparison.

## Quality-control defaults

A cell is accepted when:

- the Step-4 manifest is complete;
- the NEURON structure was ready for simulation;
- the resting state was stable;
- input resistance and time constant are present and positive;
- the exponential time-constant fit has R² ≥ 0.95.

The threshold is configurable in `config/default_atlas_config.json`. Attenuation values outside the expected range are flagged as warnings rather than silently discarded.

## Output tree

```text
GM5_OUTPUT/
  index.html
  atlas_manifest.json
  cells/*.html
  figures/*.png
  figures/*.pdf
  tables/
    cell_quality_control.csv
    accepted_cell_metrics.csv
    all_cell_metrics.csv
    attenuation_long.csv
    descriptive_statistics.csv
    omnibus_tests.csv
    pairwise_tests.csv
    ingestion_failures.csv
```

## Interpretation

The inferential statistics compare cells under a common passive parameterisation. They primarily quantify morphology-driven differences. They should not yet be interpreted as estimates of uncertainty in membrane resistance, capacitance, axial resistivity, diameter or synaptic conductance; those uncertainties belong to the later dense-sensitivity milestone.
