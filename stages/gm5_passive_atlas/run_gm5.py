from __future__ import annotations

import argparse
from pathlib import Path

from opc_atlas.atlas import run_atlas


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the GM5 OPC passive electrophysiology atlas from completed Step-4 outputs.")
    parser.add_argument("--step4-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "config" / "default_atlas_config.json")
    args = parser.parse_args()
    summary = run_atlas(args.step4_root, args.output_root, args.config)
    print(f"GM5 atlas complete: {summary['n_accepted']} accepted / {summary['n_cell_directories']} inspected")
    print(f"Open: {args.output_root / 'index.html'}")


if __name__ == "__main__":
    main()
