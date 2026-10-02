from __future__ import annotations
import runpy
from pathlib import Path
def main():
    script=Path(__file__).resolve().parents[2]/'run_pipeline.py'
    namespace=runpy.run_path(str(script))
    return namespace['main']()
