import json
from pathlib import Path

import pytest

from opc_gm7.calibration import config_for_age, validate_calibration
from opc_gm7.design import one_factor_conditions


CONFIG = json.loads((Path(__file__).parents[1] / "config/default_config.json").read_text(encoding="utf-8"))


def test_age_specific_baselines_and_relative_rm_sweep():
    mapping = validate_calibration(CONFIG)
    for age, expected in mapping.items():
        config = config_for_age(CONFIG, age)
        assert config["baseline"]["passive"]["rm_ohm_cm2"] == pytest.approx(expected * 1000)
        conditions = one_factor_conditions(config)
        assert len(conditions) == 36
        rm = [condition["level"] for condition in conditions if condition["factor"] == "rm_ohm_cm2"]
        assert rm == pytest.approx([expected * 1000 * multiplier for multiplier in (.5,.75,1,1.5,2)])


def test_non_rm_baselines_unchanged():
    for age in ("P10", "P20", "P50"):
        config = config_for_age(CONFIG, age)
        assert config["baseline"]["passive"]["ra_ohm_cm"] == 150.0
        assert config["baseline"]["synapse"]["weight_uS"] == 0.00005
        assert config["baseline"]["synapse"]["tau1_ms"] == 0.5
        assert config["baseline"]["synapse"]["tau2_ms"] == 3.0
