from pathlib import Path

import pytest

from opc_atlas.calibration import age_from_cell_id, load_calibration, rm_ohm_cm2
from opc_atlas.stats import inferential_table


def test_age_from_cell_id():
    assert age_from_cell_id("NX64_2_P10") == "P10"
    assert age_from_cell_id("NX15_26_P20") == "P20"
    assert age_from_cell_id("NX30_16_P50") == "P50"
    with pytest.raises(ValueError):
        age_from_cell_id("unknown")


def test_frozen_calibration():
    path = Path(__file__).parents[1] / "config" / "calibrated_passive_parameters.json"
    config = load_calibration(path)
    assert rm_ohm_cm2("NX64_2_P10", config) == pytest.approx(29741.010083005232)
    assert rm_ohm_cm2("NX15_26_P20", config) == pytest.approx(10094.385601286076)
    assert rm_ohm_cm2("NX30_16_P50", config) == pytest.approx(2394.438696918089)


def test_identical_metric_has_neutral_omnibus_result():
    import pandas as pd
    frame = pd.DataFrame({"age_group": ["P10"] * 3 + ["P20"] * 3 + ["P50"] * 3,
                          "metric": [1.0] * 9})
    omnibus, _ = inferential_table(frame, ["metric"], minimum_n=3)
    assert omnibus.iloc[0]["statistic"] == 0.0
    assert omnibus.iloc[0]["p_value"] == 1.0
