from pathlib import Path

from opc_inventory.inventory import _canonical_cell, build_inventory


def test_safe_aliases():
    assert _canonical_cell("NX45low") == "NX45_low"
    assert _canonical_cell("NX93top") == "NX93_up"
    assert _canonical_cell("NX6_4") == "NX6_4"


def test_missing_root(tmp_path: Path):
    try:
        build_inventory(tmp_path)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError")
