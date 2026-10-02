from __future__ import annotations


AGES = ("P10", "P20", "P50")


def age_from_cell_id(cell_id: str) -> str:
    matches = [age for age in AGES if cell_id.endswith("_" + age)]
    if len(matches) != 1:
        raise ValueError(f"Cannot determine P10/P20/P50 age from cell ID: {cell_id}")
    return matches[0]


def validate_rm_mapping(mapping: dict) -> dict[str, float]:
    if set(mapping) != set(AGES):
        raise ValueError("calibrated_rm_kohm_cm2_by_age must define exactly P10, P20 and P50")
    values = {age: float(mapping[age]) for age in AGES}
    if any(value <= 0 for value in values.values()):
        raise ValueError("All calibrated Rm values must be positive")
    return values

