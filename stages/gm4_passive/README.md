# Step 4 — Cohort-wide passive cable simulations

This package implements the first electrophysiological stage after controlled full-dataset reconstruction and validation. It uses the existing `PassiveOPCCell` representation and runs **passive current-injection protocols only**. It does not create synapses and does not run sensitivity sweeps.

## Scientific outputs per cell

- structural NEURON validation and resting-state smoke test;
- somatic current-step trace;
- input resistance (`MΩ`);
- membrane time constant with fit quality;
- soma-to-process attenuation map for every reconstructed segment;
- representative bidirectional soma/terminal transfer measurements;
- optional representative or full transfer-impedance matrix;
- concise cell-level passive summary.

Population outputs include a cell-level table and P10/P20/P50 descriptive summaries.

## Prerequisite

Step 3 must have produced reconstruction JSON files named:

```text
*_reconstruction.json
```

Cells failing Step-3 validation should not be copied into the reconstruction root supplied to Step 4.

## Installation

```bash
python -m pip install -r requirements.txt
```

Confirm NEURON:

```bash
python -c "from neuron import h; print(h.nrnversion())"
```

## Recommended controlled run

First inspect the cohort without simulating:

```bash
python run_step4.py \
  --reconstruction-root /path/to/opc_step3_validation \
  --output-root opc_step4_passive_results \
  --matrix-mode representative \
  --dry-run
```

Then run:

```bash
python run_step4.py \
  --reconstruction-root /path/to/opc_step3_validation \
  --output-root opc_step4_passive_results \
  --matrix-mode representative
```

The default `representative` matrix is deliberately controlled: it uses the soma plus up to eight terminals spanning electrotonic distance. A full all-by-all transfer matrix can be requested with `--matrix-mode full`, but should only be launched after inspecting the representative results.

## Pilot before full cohort

```bash
python run_step4.py \
  --reconstruction-root /path/to/opc_step3_validation \
  --output-root opc_step4_pilot \
  --matrix-mode representative \
  --limit 3
```

## Output tree

```text
opc_step4_passive_results/
  provenance.json
  run_plan.json
  run_summary.json
  population/
    cell_level_passive_metrics.csv
    age_group_summary.csv
    failed_cells.csv
  cells/<CELL_ID>/
    manifest.json
    <CELL_ID>_structural_validation.json
    <CELL_ID>_resting_test.json
    <CELL_ID>_current_step_summary.json
    <CELL_ID>_soma_trace.csv
    <CELL_ID>_attenuation_map.csv
    <CELL_ID>_bidirectional_transfer.csv
    <CELL_ID>_transfer_matrix.csv
    <CELL_ID>_passive_summary.json
```

## Interpretation constraints

The default membrane parameters and uniform process diameter are baseline assumptions, not fitted biological measurements. Step 4 is therefore designed to isolate effects of measured morphology under a common passive parameterisation. Parameter uncertainty belongs to the later sensitivity stage.
