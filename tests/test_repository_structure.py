from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]


def test_required_project_files_exist() -> None:
    required = [
        "README.md",
        "pyproject.toml",
        "CITATION.cff",
        "docs/WORKFLOW.md",
        "stages/gm0_inventory/run_inventory.py",
        "stages/gm4_passive/run_step4.py",
        "stages/gm45_calibration/run_gm45.py",
        "stages/gm5_passive_atlas/run_gm5.py",
        "stages/gm5_passive_atlas/validate_calibrated_step4.py",
        "stages/gm6_synaptic/run_gm6.py",
        "stages/gm6_synaptic/validate_calibrated_gm6.py",
        "stages/gm7_robustness/run_gm7.py",
        "stages/gm7_robustness/validate_calibrated_gm7.py",
        "docs/SOURCE_PROVENANCE.md",
        "docs/report/latest/OPC_passive_pipeline_report_Glia_style_with_references_EPSP.tex",
        "docs/report/latest/OPC_passive_pipeline_report_Glia_style_with_references_EPSP_v12.tex",
        "analysis/scripts/calibrated_figures.py",
        "data/DATA_TERMS.md",
        "data/inventory/readiness_report.md",
        "data/derived/gm3_validated/cells.zip",
    ]
    missing = [item for item in required if not (ROOT / item).exists()]
    assert not missing, f"Missing required repository files: {missing}"


def test_four_figure_notebooks_are_present() -> None:
    notebooks = list((ROOT / "analysis" / "notebooks").glob("Figure[1-4]*_analysis.ipynb"))
    assert len(notebooks) >= 4


def test_five_main_report_figures_are_present() -> None:
    figure_dir = ROOT / "docs" / "report" / "latest" / "figures"
    required = {
        "Figure1_morphological_diversity.pdf",
        "Figure2_Rm_calibration.pdf",
        "Figure3_calibrated_passive_atlas.pdf",
        "Figure4_calibrated_synaptic_atlas.pdf",
        "Figure5_sensitivity_robustness.pdf",
    }
    assert required <= {path.name for path in figure_dir.glob("*.pdf")}


def test_calibrated_figure_source_data_are_present() -> None:
    source = ROOT / "analysis" / "reference_outputs" / "calibrated" / "gm6" / "figure_source"
    assert (source / "all_synaptic_protocols.csv").is_file()
    assert len(list(source.glob("NX16_2_P20_single_*_trace.csv"))) == 3
    with (source / "all_synaptic_protocols.csv").open(newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 420
