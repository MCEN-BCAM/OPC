from __future__ import annotations

from typing import Any


def assess_cell(bundle: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    q = config["quality_control"]
    s = bundle["summary"]
    issues: list[str] = []
    warnings: list[str] = []

    if bundle["manifest"].get("status") != "complete":
        issues.append("step4_manifest_not_complete")
    if not bool(bundle["structural"].get("ready_for_simulation", False)):
        issues.append("structural_validation_failed")
    if q.get("require_resting_stable", True) and not bool(s.get("resting_stable", False)):
        issues.append("unstable_resting_state")

    rin = s.get("input_resistance_MOhm")
    tau = s.get("tau_ms")
    r2 = s.get("tau_fit_r2")
    if rin is None:
        issues.append("missing_input_resistance")
    elif q.get("require_positive_input_resistance", True) and float(rin) <= 0:
        issues.append("nonpositive_input_resistance")
    if tau is None:
        issues.append("missing_tau")
    elif q.get("require_positive_tau", True) and float(tau) <= 0:
        issues.append("nonpositive_tau")
    if r2 is None:
        issues.append("missing_tau_fit_r2")
    elif float(r2) < float(q.get("minimum_tau_fit_r2", 0.95)):
        issues.append("poor_tau_fit")

    att = bundle["attenuation"].get("soma_normalised_attenuation")
    if att is None or att.dropna().empty:
        issues.append("missing_attenuation_values")
    else:
        amin = float(config["attenuation"].get("minimum_normalised_attenuation", 0.0))
        amax = float(config["attenuation"].get("maximum_normalised_attenuation", 1.25))
        outside = int(((att.dropna() < amin) | (att.dropna() > amax)).sum())
        if outside:
            warnings.append(f"attenuation_outside_expected_range:{outside}")

    return {
        "cell_id": bundle["cell_id"],
        "age_group": s.get("age_group", "UNKNOWN"),
        "qc_status": "accepted" if not issues else "excluded",
        "n_errors": len(issues),
        "n_warnings": len(warnings),
        "errors": ";".join(issues),
        "warnings": ";".join(warnings),
    }
