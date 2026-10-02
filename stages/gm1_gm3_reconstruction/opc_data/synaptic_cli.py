from __future__ import annotations

import argparse
import json
from pathlib import Path

from .passive_neuron import PassiveOPCCell, PassiveParameters
from .synaptic_simulation import (
    SimulationParameters,
    SynapseParameters,
    export_results,
    export_trace,
    run_single_synapse,
    select_representative_sites,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run three pilot synaptic simulations.")
    parser.add_argument("--reconstruction", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--diameter", type=float, default=0.30)
    parser.add_argument("--rm", type=float, default=20_000.0)
    parser.add_argument("--ra", type=float, default=150.0)
    parser.add_argument("--cm", type=float, default=1.0)
    parser.add_argument("--rest", type=float, default=-75.0)
    parser.add_argument("--weight", type=float, default=0.00005)
    parser.add_argument("--tau1", type=float, default=0.5)
    parser.add_argument("--tau2", type=float, default=3.0)
    parser.add_argument("--event-time", type=float, default=20.0)
    parser.add_argument("--tstop", type=float, default=80.0)
    parser.add_argument("--dt", type=float, default=0.025)
    args = parser.parse_args()

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    passive = PassiveParameters(
        process_diameter_um=args.diameter,
        rm_ohm_cm2=args.rm,
        ra_ohm_cm=args.ra,
        cm_uF_cm2=args.cm,
        e_pas_mV=args.rest,
    )
    synaptic = SynapseParameters(
        tau1_ms=args.tau1,
        tau2_ms=args.tau2,
        weight_uS=args.weight,
        event_time_ms=args.event_time,
    )
    simulation = SimulationParameters(tstop_ms=args.tstop, dt_ms=args.dt)

    results = []
    site_records = []
    with PassiveOPCCell.from_json(args.reconstruction, passive) as cell:
        validation = cell.validate()
        if not validation["ready_for_simulation"]:
            raise RuntimeError("The passive cell failed its validation checks.")
        sites = select_representative_sites(cell, location=synaptic.location)
        for site in sites:
            result, traces = run_single_synapse(cell, site, synaptic, simulation)
            results.append(result)
            site_records.append(site.__dict__)
            export_trace(output / f"{cell.cell_id}_{site.class_name}_trace.csv", traces)

    export_results(output / f"{results[0].cell_id}_synaptic_results.csv", results)
    (output / f"{results[0].cell_id}_selected_sites.json").write_text(
        json.dumps(site_records, indent=2), encoding="utf-8"
    )
    (output / f"{results[0].cell_id}_synaptic_results.json").write_text(
        json.dumps([result.__dict__ for result in results], indent=2), encoding="utf-8"
    )

    for result in results:
        print(
            f"{result.cell_id} {result.class_name}: segment={result.segment_id}, "
            f"radial={result.radial_distance_um:.3f} um, "
            f"path={result.path_distance_um:.3f} um, "
            f"local={result.local_epsp_mV:.8f} mV, "
            f"soma={result.soma_epsp_mV:.8f} mV, "
            f"attenuation={result.attenuation_ratio:.6f}"
        )


if __name__ == "__main__":
    main()
