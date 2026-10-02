import json
import subprocess
import sys
from pathlib import Path

import pytest

from opc_gm45.calibration import summarize
from opc_gm45.interpolation import crossing_rm
from opc_gm45.io import discover_cells


def test_inverse_interpolation():
    rm, bracketed = crossing_rm([2, 4, 8], [20, 40, 80], 50)
    assert bracketed and rm == pytest.approx(5)


def test_best_fit_and_neighbours():
    rows = [{"age": age, "rm_kohm_cm2": rm, "rin_mohm": rm * factor}
            for age, factor in (("P10", 100), ("P20", 50), ("P50", 25)) for rm in (2, 3, 4)]
    targets = {age: {"mean_mohm": value, "sem_mohm": 1} for age, value in (("P10", 300), ("P20", 150), ("P50", 75))}
    summary, best, comparison = summarize(rows, targets)
    assert len(summary) == 9 and len(best) == len(comparison) == 3
    assert all(row["best_grid_rm_kohm_cm2"] == 3 for row in best)
    assert all(row["minimum_relative_error"] == 0 for row in best)


def test_gm3_json_discovery_infers_age_from_filename(tmp_path: Path):
    path = tmp_path / "NX64_2_P10_reconstruction.json"
    path.write_text("{}", encoding="utf-8")
    config = {"reconstructions": {"root": str(tmp_path), "glob": "**/*_reconstruction.json"}}
    cells = discover_cells(config, tmp_path / "config.json")
    assert cells[0]["cell_id"] == "NX64_2_P10"
    assert cells[0]["age"] == "P10"


def test_one_cell_cli(tmp_path: Path):
    recon = tmp_path / "recons" / "P10"; recon.mkdir(parents=True)
    (recon / "cell01.swc").write_text("# fixture\n", encoding="utf-8")
    config = {"rm_values_kohm_cm2": [2,3,4,5,6,7,8,10,12,15,20], "expected_cell_count": 35,
              "experimental_rin_mohm": {"P10":{"mean_mohm":2245,"sem_mohm":185.8},
              "P20":{"mean_mohm":588.4,"sem_mohm":45.78}, "P50":{"mean_mohm":179.5,"sem_mohm":11.71}},
              "reconstructions":{"root":str(tmp_path / "recons"),"glob":"**/*.swc"},
              "gm4":{"backend":"python","path":str(Path(__file__).parent),"callable":"fixture_backend:simulate_passive"}}
    config_path = tmp_path / "config.json"; config_path.write_text(json.dumps(config), encoding="utf-8")
    root = Path(__file__).parents[1]
    result = subprocess.run([sys.executable, str(root / "run_gm45.py"), "--config", str(config_path),
                             "--output-root", str(tmp_path / "out"), "--mode", "pilot"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert sum(1 for _ in (tmp_path / "out/population/Rin_vs_Rm.csv").open()) == 12
    assert (tmp_path / "out/figures/Figure1_Model_vs_Experiment.png").is_file()


def test_targeted_extension_merges_without_overwriting_source(tmp_path: Path):
    recon_root = tmp_path / "recons"
    cells = [("cell10", "P10"), ("cell20", "P20"), ("cell50", "P50")]
    for cell, age in cells:
        folder = recon_root / age; folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{cell}.swc").write_text("# fixture\n", encoding="utf-8")
    config = {"rm_values_kohm_cm2": [2,3,4,5,6,7,8,10,12,15,20], "expected_cell_count": 3,
              "experimental_rin_mohm": {"P10":{"mean_mohm":2245,"sem_mohm":185.8},
              "P20":{"mean_mohm":588.4,"sem_mohm":45.78}, "P50":{"mean_mohm":179.5,"sem_mohm":11.71}},
              "reconstructions":{"root":str(recon_root),"glob":"**/*.swc"},
              "gm4":{"backend":"python","path":str(Path(__file__).parent),"callable":"fixture_backend:simulate_passive"}}
    config_path = tmp_path / "config.json"; config_path.write_text(json.dumps(config), encoding="utf-8")
    source = tmp_path / "base.csv"
    source.write_text("cell_id,age,reconstruction_path,rm_kohm_cm2,rin_mohm,tau_ms,steady_state_mv\n" +
        "".join(f"{cell},{age},x,{rm},{rm * 10},,\n" for cell, age in cells for rm in config["rm_values_kohm_cm2"]), encoding="utf-8")
    original = source.read_bytes()
    root = Path(__file__).parents[1]
    result = subprocess.run([sys.executable, str(root / "run_gm45.py"), "--config", str(config_path),
        "--mode", "extend", "--input-csv", str(source), "--ages", "P10",
        "--rm-values", "24", "26", "28", "30", "32", "--output-root", str(tmp_path / "extended")],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert source.read_bytes() == original
    assert sum(1 for _ in (tmp_path / "extended/population/Rin_vs_Rm.csv").open()) == 39
