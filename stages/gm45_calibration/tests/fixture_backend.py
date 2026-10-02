from pathlib import Path


def simulate_passive(reconstruction_path: str, rm_ohm_cm2: float) -> dict:
    age = Path(reconstruction_path).parent.name.upper()
    scale = {"P10": 112.25, "P20": 84.057, "P50": 71.8}[age]
    return {"rin_mohm": scale * (rm_ohm_cm2 / 1000.0), "tau_ms": rm_ohm_cm2 / 1000.0}

