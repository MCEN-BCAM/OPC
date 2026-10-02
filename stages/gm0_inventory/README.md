# OPC Milestone 0 — Dataset inventory and readiness assessment

This package discovers all processed OPC cells in `MariaDATA/NLResults`, associates their file families, identifies incomplete or ambiguous records, and creates a machine-readable catalogue for Milestones 1–6.

## What it considers required

- BasicAnalyses workbook
- Sholl workbook
- Angles workbook
- standard NearestNeighbour workbook (`_NN.xlsx`)

The `_NN_2_5.xlsx` workbook and raw Neurolucida `.DAT` tracing are recorded but are not required for readiness.

## Run

From this folder:

```bash
python run_inventory.py \
  --data-root /path/to/MariaDATA \
  --output-dir inventory_results
```

The parent of `MariaDATA` may also be supplied.

## Outputs

- `dataset_inventory.json`: complete structured catalogue
- `cell_inventory.csv`: one row per discovered cell identifier
- `ready_cells.csv`: cells with every required processed input
- `readiness_report.md`: human-readable QC report

## Design rules

1. Age is taken from the `P10`, `P20`, or `P50` folder, never guessed from a filename alone.
2. Minor spelling variants such as `NX45low` and `NX45_low` are normalised.
3. Biologically ambiguous discrepancies are reported and never silently merged.
4. Raw `.DAT` files are associated conservatively at animal level because their names do not always uniquely encode the processed cell identifier.
5. A future all-cell runner can consume `ready_cells.csv` or `dataset_inventory.json` instead of using a hard-coded cell list.

## Tests

```bash
python -m pytest -q
```
