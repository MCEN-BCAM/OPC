from __future__ import annotations

from copy import deepcopy


AGES = ("P10", "P20", "P50")


def age_from_cell_id(cell_id: str) -> str:
    matches = [age for age in AGES if cell_id.endswith("_" + age)]
    if len(matches) != 1:
        raise ValueError(f"Cannot determine P10/P20/P50 age from cell ID: {cell_id}")
    return matches[0]


def validate_calibration(config: dict) -> dict[str, float]:
    mapping = config.get("calibrated_rm_kohm_cm2_by_age", {})
    if set(mapping) != set(AGES):
        raise ValueError("Calibration must define exactly P10, P20 and P50")
    values = {age: float(mapping[age]) for age in AGES}
    if any(value <= 0 for value in values.values()):
        raise ValueError("All calibrated Rm values must be positive")
    multipliers = [float(value) for value in config["one_factor_sweeps"]["rm_multiplier"]]
    if 1.0 not in multipliers or any(value <= 0 for value in multipliers):
        raise ValueError("Rm multiplier sweep must be positive and include 1.0")
    return values


def config_for_age(config: dict, age: str) -> dict:
    mapping = validate_calibration(config)
    if age not in mapping:
        raise ValueError(f"Unsupported age: {age}")
    result = deepcopy(config)
    baseline_rm = mapping[age] * 1000.0
    result["baseline"]["passive"]["rm_ohm_cm2"] = baseline_rm
    multipliers = result["one_factor_sweeps"].pop("rm_multiplier")
    result["one_factor_sweeps"] = {"rm_ohm_cm2": [baseline_rm * float(x) for x in multipliers],
                                    **result["one_factor_sweeps"]}
    factors = result.get("interaction_design", {}).get("factors", {})
    if "rm_multiplier" in factors:
        interaction_multipliers = factors.pop("rm_multiplier")
        result["interaction_design"]["factors"] = {
            "rm_ohm_cm2": [baseline_rm * float(x) for x in interaction_multipliers], **factors}
    result["active_age_group"] = age
    result["active_baseline_rm_kohm_cm2"] = mapping[age]
    return result

