#!/usr/bin/env python3
"""Generate synthetic GM4-like outputs for a downstream GM5 smoke test."""
from __future__ import annotations
import runpy, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'stages/gm5_passive_atlas/tests/make_synthetic_step4.py'
target=ROOT/'data/example_dataset/synthetic_gm4_outputs'
namespace=runpy.run_path(str(source))
generated=source.parent/'synthetic_step4'
if target.exists(): shutil.rmtree(target)
shutil.copytree(generated,target)
print(f'Synthetic example written to {target}')
