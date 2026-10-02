# Step 3 controlled full-dataset validation — run status

## Scope executed

Requested stages only:

1. data import
2. reconstruction
3. validation

No NEURON, synaptic, dense-mapping, or sensitivity stages were launched.

## Inventory result

- Total discovered cells: 41
- Ready for controlled validation: 35
- Incomplete and skipped: 6
- P10 ready: 12
- P20 ready: 12
- P50 ready: 11

## Execution result in hosted runtime

All 35 ready cells reached the data-import stage. Each stopped at the same environment-level dependency error:

```
ModuleNotFoundError: No module named 'xlrd'
```

The source data contain genuine legacy binary `.xls` workbooks, for which the validated reader imports `xlrd`. The hosted package index did not provide this dependency. Consequently, no reconstruction or morphology validation result should be interpreted as having been produced here.

## Command to resume locally

From the pipeline directory, install the dependencies and run:

```bash
python -m pip install -r requirements.txt
python run_pipeline.py \
  --data-root /path/to/MariaDATA/MariaDATA \
  --output-root opc_step3_validation \
  --stages data,reconstruction,validation \
  --force
```

The `--force` option is needed because the manifests record the hosted-runtime import failures. The pipeline remains sequential by default and will not launch the later simulation stages.
