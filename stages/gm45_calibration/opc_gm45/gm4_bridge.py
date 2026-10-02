"""Adapter for the original ``4-opc_step4_cohort_passive`` package."""
from __future__ import annotations


def simulate_passive(reconstruction_path: str, rm_ohm_cm2: float) -> dict:
    """Run GM4's unchanged somatic current-step protocol for one GM3 cell."""
    from opc_data.passive_neuron import PassiveOPCCell, PassiveParameters
    from opc_data.passive_protocols import CurrentStepProtocol, current_step

    parameters = PassiveParameters(
        rm_ohm_cm2=float(rm_ohm_cm2),
        ra_ohm_cm=150.0,
        cm_uF_cm2=1.0,
        e_pas_mV=-75.0,
        process_diameter_um=0.30,
    )
    with PassiveOPCCell.from_json(reconstruction_path, parameters).build() as cell:
        structural = cell.validate()
        if not structural["ready_for_simulation"]:
            raise RuntimeError("GM4 structural validation failed")
        result = current_step(cell, CurrentStepProtocol(), record_all=False)
    soma = result["soma"]
    return {
        "rin_mohm": soma["input_resistance_MOhm"],
        "tau_ms": soma["tau_ms"],
        "steady_state_mv": soma["steady_mV"],
    }

