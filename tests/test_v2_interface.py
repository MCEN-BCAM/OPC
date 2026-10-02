from pathlib import Path
import subprocess,sys,yaml
ROOT=Path(__file__).resolve().parents[1]
def test_data_layout():
    assert (ROOT/'data/example_dataset/P10').is_dir()
    assert (ROOT/'data/source/MariaDATA/NLResults/BasicAnalyses').is_dir()
    assert (ROOT/'data/source/MariaDATA/NLTracings').is_dir()
    assert (ROOT/'data/derived/gm3_validated/cells.zip').is_file()
    assert (ROOT/'data/inventory/ready_cells.csv').is_file()
def test_config_loads():
    cfg=yaml.safe_load((ROOT/'config/default.yaml').read_text())
    assert cfg['passive_control']['rm_ohm_cm2']>0
    assert 'gm0' in cfg['execution']['stages']
    assert 'gm45' in cfg['execution']['stages']
    assert cfg['calibration']['calibrated_rm_kohm_cm2_by_age']['P10'] > 20
def test_runner_print_plan():
    p=subprocess.run([sys.executable,str(ROOT/'run_pipeline.py'),'--print-plan','--dry-run'],cwd=ROOT,capture_output=True,text=True)
    assert p.returncode==0
    assert '[gm0]' in p.stdout and '[gm45-base-sweep]' in p.stdout and '[gm7-robustness]' in p.stdout
    assert 'gm5-calibrated-gm4-preparation' in p.stdout


def test_public_data_bundle():
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/validate_public_data.py')],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert '35 ready cells, 35 GM3 cells' in result.stdout
