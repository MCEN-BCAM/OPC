
from __future__ import annotations

import argparse
from pathlib import Path

from .reconstruction import reconstruct_cell, export_reconstruction
from .plot_reconstruction import plot_reconstruction


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell-id", required=True)
    parser.add_argument("--basic-file", required=True)
    parser.add_argument("--segment-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--coordinate-tolerance", type=float, default=0.08)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    result = reconstruct_cell(
        cell_id=args.cell_id,
        basic_path=args.basic_file,
        segment_csv_path=args.segment_csv,
        coordinate_tolerance_um=args.coordinate_tolerance,
    )
    export_reconstruction(result, output_dir)
    plot_reconstruction(
        output_dir / f"{args.cell_id}_reconstruction.json",
        output_dir / f"{args.cell_id}_reconstruction.png",
    )

    d = result.diagnostics
    print(f"Cell: {args.cell_id}")
    print(f"Segments: {d['source_counts']['segments']}")
    print(f"Assigned endpoints: {d['endpoint_assignment']['assigned_endpoints']}")
    print(
        "Missing parents: "
        f"{len(d['topology']['missing_parent_segments'])}"
    )
    print(
        "Ambiguous parents: "
        f"{len(d['topology']['ambiguous_parent_segments'])}"
    )
    print(f"Cycles: {len(d['cycles'])}")
    print(f"Maximum endpoint match cost: {d['endpoint_match_cost']['maximum']}")


if __name__ == "__main__":
    main()
