"""Report whether the core OPC modelling environment is usable."""
from __future__ import annotations

import importlib
import platform
import sys

REQUIRED = ["numpy", "pandas", "scipy", "matplotlib", "openpyxl", "networkx", "neuron"]


def main() -> int:
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")
    failed: list[str] = []
    for name in REQUIRED:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", "version unavailable")
            print(f"[OK] {name}: {version}")
        except Exception as exc:  # environment diagnostic
            failed.append(name)
            print(f"[FAIL] {name}: {exc}")
    if failed:
        print("Missing or unusable packages: " + ", ".join(failed))
        return 1
    from neuron import h
    print(f"NEURON: {h.nrnversion()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
