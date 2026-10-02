# Calibrated passive-cable modelling of oligodendrocyte precursor cells

This repository is the consolidated, reproducible implementation of the OPC modelling pipeline used for the revised article. It converts processed Neurolucida measurements into validated branched cable models, calibrates passive membrane resistance to experimental input resistance, constructs passive and synaptic atlases, and tests sensitivity and robustness.

## Scientific workflow

```text
GM0   dataset inventory and readiness
GM1   workbook parsing
GM2   cell-specific branching reconstruction
GM3   controlled morphological validation
GM4   common-Rm morphology-only passive control
GM4.5 age-specific Rm calibration against experimental Rin
GM5   calibrated passive-electrophysiology atlas
GM6   calibrated conductance-based synaptic-integration atlas
GM7   one-factor-at-a-time sensitivity and robustness analysis
```

GM4 remains an intentional control in which every cell uses the same passive parameters, so its between-age differences isolate reconstructed morphology. GM4.5 then calibrates membrane resistivity separately for P10, P20, and P50. GM5–GM7 use those age-specific calibrated values:

| Age | Calibrated $R_m$ (kΩ·cm²) |
|---|---:|
| P10 | 29.7410 |
| P20 | 10.0944 |
| P50 | 2.39444 |

The calibration used the 11-point sweep 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, and 20 kΩ·cm², plus 24, 26, 28, 30, and 32 kΩ·cm² for P10 because its experimental target lay above the initial range. In total, 445 cell–parameter simulations were analysed.

GM6 uses exact matched-site normalisation for spatial summation. The denominator is the sum of single-synapse responses simulated at the same sites used in the simultaneous condition, so the one-input spatial ratio is exactly 1 by construction.

## Installation

Python 3.10 or later is recommended. NEURON is required for electrical simulations.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python check_installation.py
```

## Safe first run

Inspect the complete command plan without running simulations:

```bash
python run_pipeline.py --dry-run --print-plan
```

The authorised complete processed dataset is already included at
`data/source/MariaDATA/`, which is the default in `config/default.yaml`. To use a
different copy, override the locations:

```bash
python run_pipeline.py \
  --dataset /absolute/path/to/MariaDATA \
  --results /absolute/path/to/results
```

For a pilot, set `execution.limit: 3`. Full electrical simulations are computationally substantial; validated cohort tables are provided under `analysis/reference_outputs/calibrated/` for comparison and rapid figure reproduction.

## Data policy

The pipeline starts from processed Neurolucida outputs, not raw microscopy images. The complete authorised processed dataset is distributed under `data/source/MariaDATA/`: 41 cell identifiers were discovered, of which 35 constitute the validated modelling cohort (P10, n=12; P20, n=12; P50, n=11). The original Igor Pro archive is stored losslessly as `.pxp.gz` to respect GitHub's per-file size limit. See `data/DATA_TERMS.md`, `docs/DATASET.md`, and `docs/DATA_DICTIONARY.md` before redistributing the data.

## Repository map

- `stages/`: preserved scientific implementations for GM0–GM7, including GM4.5
- `src/`: reusable inventory and passive-cable support code
- `config/`: central orchestration configuration
- `analysis/reference_outputs/calibrated/`: compact validated cohort tables
- `analysis/notebooks/`: manuscript-analysis notebooks retained from the earlier release
- `data/source/MariaDATA/`: complete authorised processed experimental dataset
- `data/derived/gm3_validated/`: validated 35-cell reconstruction archive used by Figure 1
- `data/inventory/`: reproducible GM0 dataset inventory and readiness report
- `docs/report/latest/`: latest calibrated LaTeX report and five main figures
- `docs/`: workflow, pipeline, dataset, licensing, and source-provenance documentation
- `tests/`: structural and orchestration checks

## Verification

```bash
pytest -q
python scripts/validate_public_data.py
python run_pipeline.py --dry-run --print-plan
```

These commands check repository structure and configuration, validate the complete public data bundle, and verify the GM0–GM7 calibrated command plan without executing NEURON.

## Regenerate manuscript figures

All five main manuscript figures can be regenerated from the packaged data and validated tables:

```bash
python reproduce_paper.py --mode figures --output results/paper
```

The resulting PDFs are written to `results/paper/figures/`. The command executes the Figure 1 morphology notebook using the included GM3 reconstruction archive and `BasicAnalyses.zip`, then assembles Figures 2–5 from the validated calibrated tables. The exact source data needed for the Figure 4 continuous-distance, temporal, spatial, and representative-trace panels are packaged under `analysis/reference_outputs/calibrated/gm6/figure_source/`.

Citation metadata are in `CITATION.cff`. Before public release, replace its author/repository placeholders and select a software licence with the relevant authors and institutions; see `docs/LICENSING.md`.
