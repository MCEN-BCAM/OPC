#!/usr/bin/env bash
set -euo pipefail
DATA_ROOT="${1:-data/raw/MariaDATA}"
OUT_ROOT="${2:-data/interim/dry_run}"
python stages/gm0_inventory/run_inventory.py --data-root "$DATA_ROOT" --output-dir "$OUT_ROOT/gm0"
python stages/gm1_gm3_reconstruction/run_pipeline.py --data-root "$DATA_ROOT" --output-root "$OUT_ROOT/gm1_gm3" --dry-run
printf '\nGM4–GM7 dry runs require a completed GM3 reconstruction root. See docs/WORKFLOW.md.\n'
