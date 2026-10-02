import json
from pathlib import Path

import pytest

from opc_gm6.calibration import age_from_cell_id, validate_rm_mapping


def test_age_selection():
    assert age_from_cell_id("NX64_2_P10") == "P10"
    assert age_from_cell_id("NX15_26_P20") == "P20"
    assert age_from_cell_id("NX30_16_P50") == "P50"
    with pytest.raises(ValueError):
        age_from_cell_id("unknown")


def test_frozen_calibration_and_unchanged_synapse():
    path = Path(__file__).parents[1] / "config/default_config.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    mapping = validate_rm_mapping(config["calibrated_rm_kohm_cm2_by_age"])
    assert mapping == pytest.approx({"P10": 29.741010083005232,
                                     "P20": 10.094385601286076,
                                     "P50": 2.394438696918089})
    assert config["synapse"]["weight_uS"] == 0.00005
    assert config["protocols"]["spatial_counts"] == [1, 2, 4, 8]
