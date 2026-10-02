# Inventory-driven OPC passive-cable pipeline

This package generalises validated Milestones 1–6 to every OPC marked ready by Milestone 0. The scientific modules in `opc_data/` are copied unchanged from the validated cumulative Milestone 6 package; only orchestration is new.

## Default full sequential run

```bash
python run_pipeline.py --data-root /path/to/MariaDATA --output-root results
```

The default is one worker and the stages run in order for each cell: data import, reconstruction, validation, NEURON model, representative synaptic simulations, dense mapping and sensitivity analysis.

## Useful controlled runs

```bash
# Inspect inventory and planned cells only
python run_pipeline.py --data-root /path/to/MariaDATA --output-root results --dry-run

# Run non-NEURON stages first
python run_pipeline.py --data-root /path/to/MariaDATA --output-root results --stages data,reconstruction,validation

# Pilot one cell
python run_pipeline.py --data-root /path/to/MariaDATA --output-root results --cells NX5_9_P10

# Optional future parallel execution
python run_pipeline.py --data-root /path/to/MariaDATA --output-root results --workers 4
```

Each cell has a resumable `manifest.json`. Completed stages are skipped unless `--force` is supplied. Failed cells do not stop the remaining cells.
