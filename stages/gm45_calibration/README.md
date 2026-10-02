# GM4.5 Stage 1 — passive membrane calibration

GM4.5 calibrates specific passive membrane resistance (`Rm`) against age-resolved experimental input resistance while leaving the validated GM3 morphologies and all GM4 stimulation/model settings unchanged. It is an orchestration and analysis layer: **GM4 remains the only simulation engine**.

## Frozen scientific scope

- Rm sweep: 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20 kΩ·cm²
- Cohort: 35 validated GM3 reconstructions (385 simulations)
- Experimental Rin (mean ± SEM): P10 2245.0 ± 185.8 MΩ; P20 588.4 ± 45.78 MΩ; P50 179.5 ± 11.71 MΩ
- No active conductances, optimization, or changes to other passive/model settings

## Layout

```text
GM45/
├── run_gm45.py
├── opc_gm45/
├── config/calibration_config.json
├── tests/
├── README.md
└── requirements.txt
```

Results are written under the chosen output root:

```text
population/Rin_vs_Rm.csv
population/CalibrationSummary.csv
population/BestFitParameters.csv
population/ModelExperimentComparison.csv
figures/Figure1_Model_vs_Experiment.{png,pdf}
figures/Figure2_Relative_Calibration_Error.{png,pdf}
run_metadata.json
```

`BestFitParameters.csv` reports the best tested grid point, inverse-linear interpolated Rm, whether the target was bracketed, minimum relative error, and the neighbouring grid values/errors. Interpolation is descriptive; it does not launch extra simulations.

## Installation

Use the same Python environment as GM4, then install the small analysis dependency set:

```bash
python -m pip install -r requirements.txt
```

Place `GM45` beside the original `4-opc_step4_cohort_passive` and `3-opc_step3_validation` folders, or edit the two paths in `config/calibration_config.json`:

```text
project/
├── 3-opc_step3_validation/
├── 4-opc_step4_cohort_passive/
└── GM45/
```

## Connection to the existing GM4 engine

The default configuration is already connected to the supplied original GM4 package. `opc_gm45.gm4_bridge` imports GM4's `PassiveOPCCell`, `PassiveParameters`, `CurrentStepProtocol`, and `current_step` directly. The bridge changes only `rm_ohm_cm2`; it preserves GM4's original values for Ra, Cm, leak reversal, process diameter, and the complete somatic current-step protocol.

No modification to the GM4 folder is required.

Alternatively, select `"backend": "command"` and provide an argument list in the config. Placeholders are substituted without invoking a shell:

```json
"gm4": {
  "backend": "command",
  "command": [
    "python", "../GM4/run_gm4.py",
    "--reconstruction", "{cell_path}",
    "--rm", "{rm_ohm_cm2}",
    "--json-output", "{output_json}"
  ]
}
```

The command must write a JSON object containing `rin_mohm` to `{output_json}`. This adapter avoids assumptions about an unavailable GM4 codebase while preserving GM4 as the source of model physics.

By default, GM4.5 discovers GM3's `*_reconstruction.json` files and extracts age from cell identifiers such as `NX64_2_P10`. A CSV manifest is also supported; add its path as `reconstructions.manifest`:

```csv
cell_id,age,path
NX64_2_P10,P10,NX64_2_P10_reconstruction.json
```

Paths are relative to `reconstructions.root`. Age values must be P10, P20, or P50.

## Run and validate

From the `GM45` directory:

```bash
# One reconstruction × 11 conditions
python run_gm45.py --mode pilot --output-root pilot_results

# All 35 reconstructions × 11 conditions
python run_gm45.py --mode cohort --output-root results

# Structural audit of the completed 385-row sweep
python run_gm45.py --mode validate --output-root results
```

Expected full validation message:

```text
PASS: 35 cells x 11 Rm conditions = 385 rows
```

## Targeted P10 extension

The initial cohort showed that P20 and P50 were bracketed but the P10 experimental target lay above the original grid. Reuse all 385 existing rows and run only 60 additional simulations (12 P10 cells × 5 values):

```bash
python run_gm45.py --mode extend \
  --input-csv results/population/Rin_vs_Rm.csv \
  --ages P10 \
  --rm-values 24 26 28 30 32 \
  --output-root results_extended
```

The original `results` directory is not modified. The combined 445-row dataset, updated tables, and updated figures are written to `results_extended`. Validate it with:

```bash
python run_gm45.py --mode validate --output-root results_extended
```

Expected result:

```text
PASS: 35 cells, 445 rows; P10=16 Rm conditions, P20=11 Rm conditions, P50=11 Rm conditions
```

Existing GM4 output can be analyzed without rerunning simulations after it has been normalized to the `Rin_vs_Rm.csv` schema (`cell_id, age, rm_kohm_cm2, rin_mohm`):

```bash
python run_gm45.py --mode analyze --input-csv /path/to/Rin_vs_Rm.csv --output-root results
```

Existing raw sweep data are never overwritten unless `--force` is supplied. The run metadata records the configuration checksum and source paths.

## Automated tests

```bash
python -m pytest -q
```

The end-to-end test uses a clearly isolated deterministic fixture backend. It validates orchestration, table generation, interpolation, and plotting; it is **not** a scientific validation of GM4 or NEURON. Scientific validation requires the real GM3 cohort and GM4 engine, first in pilot mode and then as the complete 385-row cohort.
