
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .passive_neuron import PassiveOPCCell, PassiveParameters


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconstruction", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--diameter", type=float, default=0.30)
    parser.add_argument("--rm", type=float, default=20_000.0)
    parser.add_argument("--ra", type=float, default=150.0)
    parser.add_argument("--cm", type=float, default=1.0)
    parser.add_argument("--rest", type=float, default=-75.0)
    args = parser.parse_args()

    parameters = PassiveParameters(
        process_diameter_um=args.diameter,
        rm_ohm_cm2=args.rm,
        ra_ohm_cm=args.ra,
        cm_uF_cm2=args.cm,
        e_pas_mV=args.rest,
    )

    with PassiveOPCCell.from_json(args.reconstruction, parameters) as cell:
        summary = cell.summary()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    v = summary["validation"]
    s = summary["resting_smoke_test"]
    print(f"Cell: {v['cell_id']}")
    print(f"Process sections: {v['built_process_section_count']}")
    print(f"Total sections: {v['total_section_count_including_soma']}")
    print(f"Total process length: {v['built_total_process_length_um']:.6f} um")
    print(f"Maximum branch order: {v['maximum_branch_order']}")
    print(f"Total nseg: {v['nseg_total']}")
    print(f"Ready for simulation: {v['ready_for_simulation']}")
    print(f"Stable at rest: {s['stable_at_rest']}")


if __name__ == "__main__":
    main()
