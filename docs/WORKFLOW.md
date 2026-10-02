# Reproducible workflow

The root orchestrator is the recommended interface. The stage commands below are useful for auditing or resuming one module.

## GM0 — inventory

```bash
python stages/gm0_inventory/run_inventory.py \
  --data-root data/source/MariaDATA \
  --output-dir results/gm0
```

## GM1–GM3 — import, reconstruction, and validation

```bash
python stages/gm1_gm3_reconstruction/run_pipeline.py \
  --data-root data/source/MariaDATA \
  --output-root results/gm1_gm3 \
  --stages data,reconstruction,validation
```

Only GM3-accepted reconstruction JSON files should proceed to electrical simulation.

## GM4 — common-Rm morphology control

```bash
python stages/gm4_passive/run_step4.py \
  --reconstruction-root results/gm1_gm3 \
  --output-root results/gm4_morphology_control \
  --rm 20000 --ra 150 --cm 1 --diameter 0.30 --rest -75 \
  --matrix-mode representative --dry-run
```

This control uses identical passive properties in every cell. It remains scientifically useful because its between-age differences isolate reconstructed morphology.

## GM4.5 — membrane-resistivity calibration

Base sweep:

```bash
python stages/gm45_calibration/run_gm45.py \
  --mode cohort \
  --config stages/gm45_calibration/config/calibration_config.json \
  --reconstruction-root results/gm1_gm3 \
  --gm4-root stages/gm4_passive \
  --output-root results/gm45_sweep
```

P10 extension and final analysis:

```bash
python stages/gm45_calibration/run_gm45.py \
  --mode extend \
  --config stages/gm45_calibration/config/calibration_config.json \
  --reconstruction-root results/gm1_gm3 \
  --gm4-root stages/gm4_passive \
  --input-csv results/gm45_sweep/population/Rin_vs_Rm.csv \
  --ages P10 --rm-values 24 26 28 30 32 \
  --output-root results/gm45_extended
```

The resulting calibrated values are P10 29.7410, P20 10.0944, and P50 2.39444 kΩ·cm².

## GM5 — calibrated passive atlas

First generate passive outputs with the age-specific calibration, then analyse them:

```bash
python stages/gm5_passive_atlas/run_calibrated_step4.py \
  --gm4-root stages/gm4_passive \
  --reconstruction-root results/gm1_gm3 \
  --output-root results/gm4_calibrated \
  --calibration stages/gm5_passive_atlas/config/calibrated_passive_parameters.json

python stages/gm5_passive_atlas/run_gm5.py \
  --step4-root results/gm4_calibrated \
  --output-root results/gm5
```

## GM6 — calibrated synaptic atlas

```bash
python stages/gm6_synaptic/run_gm6.py \
  --reconstruction-root results/gm1_gm3 \
  --output-root results/gm6 \
  --dry-run
```

Remove `--dry-run` after inspecting the plan. The supplied default configuration contains the calibrated age-specific `R_m` mapping and exact matched-site spatial normalisation.

## GM7 — calibrated sensitivity and robustness

```bash
python stages/gm7_robustness/run_gm7.py \
  --reconstruction-root results/gm1_gm3 \
  --output-root results/gm7 \
  --dry-run
```

The default screen is one-factor-at-a-time. Use `--enable-interactions` only for a deliberately restricted analysis; it materially expands the scientific design and computational load.

## Reproducibility checkpoints

1. Run a three-cell pilot before the cohort.
2. Preserve every provenance, plan, summary, and cell-manifest file.
3. Do not overwrite validated outputs; use a versioned result directory.
4. Compare regenerated cohort tables with `analysis/reference_outputs/calibrated/`.
5. Record deliberate parameter or code changes in `CHANGELOG.md`.

## Rebuild the manuscript figures

The fastest manuscript-level check uses the packaged validated data products and
does not rerun the computationally expensive NEURON cohort simulations:

```bash
python reproduce_paper.py --mode figures --output results/paper
```

This recreates main Figures 1–5. Use the stage commands above when the objective
is to regenerate the underlying simulation outputs rather than the figures alone.
