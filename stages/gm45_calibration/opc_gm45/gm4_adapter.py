from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


class GM4Adapter:
    """Thin bridge to GM4; GM4 remains the sole owner of simulation physics."""

    def __init__(self, config: dict, config_path: Path):
        self.config = config
        self.config_path = config_path
        gm4_path = config.get("path")
        if gm4_path:
            configured_path = Path(gm4_path)
            path = str((configured_path if configured_path.is_absolute()
                        else config_path.parent / configured_path).resolve())
            if path not in sys.path:
                sys.path.insert(0, path)

    def run(self, cell: dict[str, str], rm_kohm_cm2: float) -> dict:
        backend = self.config.get("backend", "python")
        if backend == "python":
            result = self._python(cell, rm_kohm_cm2)
        elif backend == "command":
            result = self._command(cell, rm_kohm_cm2)
        else:
            raise ValueError("gm4.backend must be 'python' or 'command'")
        if "rin_mohm" not in result:
            raise ValueError("GM4 result must contain rin_mohm")
        rin = float(result["rin_mohm"])
        if not (rin > 0):
            raise ValueError(f"Non-positive Rin returned for {cell['cell_id']}")
        return {**result, "rin_mohm": rin}

    def _python(self, cell: dict[str, str], rm: float) -> dict:
        spec = self.config.get("callable", "")
        if ":" not in spec:
            raise ValueError("gm4.callable must be 'module:function'")
        module_name, function_name = spec.split(":", 1)
        function = getattr(importlib.import_module(module_name), function_name)
        return dict(function(reconstruction_path=cell["path"], rm_ohm_cm2=rm * 1000.0))

    def _command(self, cell: dict[str, str], rm: float) -> dict:
        template = self.config.get("command")
        if not isinstance(template, list) or not template:
            raise ValueError("gm4.command must be a JSON list of arguments")
        with tempfile.TemporaryDirectory(prefix="gm45_") as tmp:
            output = Path(tmp) / "result.json"
            values = {"cell_path": cell["path"], "rm_kohm_cm2": rm,
                      "rm_ohm_cm2": rm * 1000.0, "output_json": str(output)}
            command = [str(arg).format(**values) for arg in template]
            completed = subprocess.run(command, cwd=self.config_path.parent, text=True,
                                       capture_output=True, check=False)
            if completed.returncode:
                raise RuntimeError(f"GM4 failed ({completed.returncode}): {completed.stderr.strip()}")
            if not output.is_file():
                raise RuntimeError("GM4 did not write the configured {output_json} file")
            return json.loads(output.read_text(encoding="utf-8"))
