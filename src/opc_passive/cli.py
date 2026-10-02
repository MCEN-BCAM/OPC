
from __future__ import annotations

import argparse
from pathlib import Path

from .dataset import Dataset


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import processed Neurolucida tables cell by cell."
    )
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    dataset = Dataset.discover(args.data_dir)
    if not dataset.cells:
        raise SystemExit("No recognised OPC files were found.")

    dataset.load_all(verbose=True)
    dataset.export_all(args.output_dir)

    print(f"\nImported {len(dataset.cells)} cells.")
    print(f"Outputs written to: {Path(args.output_dir).resolve()}")


if __name__ == "__main__":
    main()
