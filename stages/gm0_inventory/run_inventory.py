#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from opc_inventory import build_inventory, write_reports


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Milestone 0 OPC dataset inventory.")
    parser.add_argument("--data-root", required=True, help="Path to MariaDATA or its parent directory.")
    parser.add_argument("--output-dir", default="inventory_results", help="Directory for CSV/JSON/Markdown reports.")
    args = parser.parse_args()

    inventory = build_inventory(Path(args.data_root))
    write_reports(inventory, Path(args.output_dir))
    summary = inventory["summary"]
    print(f"Discovered {summary['total_cells']} cell identifiers")
    print(f"Complete: {summary['complete']}")
    print(f"Complete with warnings: {summary['complete_with_warnings']}")
    print(f"Incomplete: {summary['incomplete']}")
    print(f"Reports written to {Path(args.output_dir).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
