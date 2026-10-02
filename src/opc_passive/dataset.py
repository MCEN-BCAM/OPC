
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import csv
from collections import defaultdict

from .discovery import FileRecord, discover_files
from .readers import WorkbookData, read_workbook
from .utils import first_number


@dataclass
class CellData:
    cell_id: str
    animal: str
    tracing: str
    age: str | None
    files: list[FileRecord] = field(default_factory=list)
    workbooks: dict[str, list[WorkbookData]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def load(self) -> None:
        grouped: dict[str, list[WorkbookData]] = defaultdict(list)
        for record in self.files:
            grouped[record.family].append(read_workbook(record.path))
        self.workbooks = dict(grouped)
        self._quality_checks()

    def _quality_checks(self) -> None:
        families = {record.family for record in self.files}
        for required in ("basic", "sholl", "angles"):
            if required not in families:
                self.warnings.append(f"Missing {required} workbook.")
        nn_subtypes = {
            record.subtype for record in self.files
            if record.family == "nearest_neighbour"
        }
        if "standard" not in nn_subtypes:
            self.warnings.append("Missing standard nearest-neighbour workbook.")
        if "2_5" not in nn_subtypes:
            self.warnings.append("Missing 2.5-um nearest-neighbour workbook.")

    def workbook(self, family: str, index: int = 0) -> WorkbookData | None:
        items = self.workbooks.get(family, [])
        return items[index] if index < len(items) else None

    def sheet(self, family: str, sheet_name: str) -> Any:
        for workbook in self.workbooks.get(family, []):
            if sheet_name in workbook.sheets:
                return workbook.sheets[sheet_name]
        return None

    def _basic_summary(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        wb = self.workbook("basic")
        if wb is None:
            return result

        seg = wb.sheets.get("Segment-Dendrites")
        if seg:
            lengths = [
                first_number(row, ("length_um", "length"))
                for row in seg.rows
            ]
            lengths = [x for x in lengths if x is not None]
            orders = [
                first_number(row, ("order",))
                for row in seg.rows
            ]
            orders = [int(x) for x in orders if x is not None]
            result.update({
                "segment_rows": len(seg.rows),
                "segment_length_sum_um": sum(lengths),
                "segment_length_mean_um": (
                    sum(lengths) / len(lengths) if lengths else None
                ),
                "maximum_branch_order": max(orders) if orders else None,
                "branch_orders_present": sorted(set(orders)),
            })

        nodes = wb.sheets.get("Segment Points-Nodes")
        endings = (
            wb.sheets.get("Segment Points-Endings")
            or wb.sheets.get("Segment Point-Endings")
        )
        bodies = wb.sheets.get("Cell Bodies")
        if nodes:
            result["node_rows"] = len(nodes.rows)
        if endings:
            result["ending_rows"] = len(endings.rows)
        if bodies:
            result["cell_body_rows"] = len(bodies.rows)
            result["cell_body_first_record"] = bodies.rows[0] if bodies.rows else None

        summary = wb.sheets.get("Neuron Summary")
        if summary:
            result["neuron_summary_rows"] = summary.rows
        totals = wb.sheets.get("Individual Totals-Dendrite")
        if totals:
            result["individual_totals_rows"] = totals.rows
        return result

    def _sholl_summary(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        wb = self.workbook("sholl")
        if wb is None:
            return result
        sheet = wb.sheets.get("Sholl-Dendrite")
        if sheet:
            radii = [first_number(row, ("radius_um", "radius")) for row in sheet.rows]
            radii = [x for x in radii if x is not None]
            result.update({
                "sholl_rows": len(sheet.rows),
                "maximum_radius_um": max(radii) if radii else None,
                "headers": sheet.headers,
            })
        order = wb.sheets.get("Sholl Branch Order-Dendrite")
        if order:
            result["branch_order_sholl_rows"] = len(order.rows)
            result["branch_order_sholl_headers"] = order.headers
        return result

    def _angles_summary(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        wb = self.workbook("angles")
        if wb is None:
            return result
        sheet = next(iter(wb.sheets.values()), None)
        if sheet:
            result.update({
                "angle_rows": len(sheet.rows),
                "headers": sheet.headers,
            })
        return result

    def _nn_summary(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for record, wb in zip(
            [r for r in self.files if r.family == "nearest_neighbour"],
            self.workbooks.get("nearest_neighbour", []),
        ):
            sheet = next(iter(wb.sheets.values()), None)
            if sheet:
                result[record.subtype or "unknown"] = {
                    "rows": len(sheet.rows),
                    "headers": sheet.headers,
                }
        return result

    def summary(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "animal": self.animal,
            "tracing": self.tracing,
            "age": self.age,
            "warnings": self.warnings,
            "basic": self._basic_summary(),
            "sholl": self._sholl_summary(),
            "nearest_neighbour": self._nn_summary(),
            "angles": self._angles_summary(),
        }

    def inventory(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "files": [asdict(x) for x in self.files],
            "warnings": self.warnings,
        }

    def workbook_metadata(self) -> dict[str, Any]:
        return {
            family: [workbook.metadata() for workbook in workbooks]
            for family, workbooks in self.workbooks.items()
        }

    def export(self, output_dir: str | Path) -> None:
        output_dir = Path(output_dir)
        cell_dir = output_dir / self.cell_id
        cell_dir.mkdir(parents=True, exist_ok=True)

        (cell_dir / f"{self.cell_id}_inventory.json").write_text(
            json.dumps(self.inventory(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (cell_dir / f"{self.cell_id}_summary.json").write_text(
            json.dumps(self.summary(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (cell_dir / f"{self.cell_id}_sheets.json").write_text(
            json.dumps(self.workbook_metadata(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        diagnostic_lines = [
            f"Cell: {self.cell_id}",
            f"Animal: {self.animal}",
            f"Tracing: {self.tracing}",
            f"Age: {self.age}",
            "",
            "Files:",
        ]
        diagnostic_lines.extend(f"  - {r.family}: {r.filename}" for r in self.files)
        diagnostic_lines.append("")
        diagnostic_lines.append("Warnings:")
        diagnostic_lines.extend(
            [f"  - {warning}" for warning in self.warnings]
            or ["  - none"]
        )
        diagnostic_lines.append("")
        diagnostic_lines.append("Summary:")
        diagnostic_lines.append(json.dumps(self.summary(), indent=2, ensure_ascii=False))
        (cell_dir / f"{self.cell_id}_diagnostics.txt").write_text(
            "\n".join(diagnostic_lines),
            encoding="utf-8",
        )

        # Export every parsed worksheet to CSV. This makes the imported data
        # directly inspectable without requiring Python.
        for family, workbooks in self.workbooks.items():
            for wb_index, workbook in enumerate(workbooks, start=1):
                suffix = "" if len(workbooks) == 1 else f"_{wb_index}"
                for sheet_name, sheet in workbook.sheets.items():
                    safe_sheet = "".join(
                        ch if ch.isalnum() else "_"
                        for ch in sheet_name
                    ).strip("_")
                    filename = (
                        f"{self.cell_id}_{family}{suffix}_{safe_sheet}.csv"
                    )
                    with (cell_dir / filename).open(
                        "w", newline="", encoding="utf-8"
                    ) as handle:
                        writer = csv.DictWriter(handle, fieldnames=sheet.headers)
                        writer.writeheader()
                        writer.writerows(sheet.rows)


@dataclass
class Dataset:
    cells: dict[str, CellData]

    @classmethod
    def discover(cls, data_dir: str | Path) -> "Dataset":
        records = discover_files(data_dir)

        # Files such as Angles, Sholl, and NearestNeighbour may not encode age
        # in the filename when copied into one flat directory. Infer age from
        # the matching BasicAnalyses workbook for the same animal/tracing.
        age_by_key: dict[tuple[str, str], str] = {}
        for record in records:
            if record.age is not None:
                age_by_key[(record.animal, record.tracing)] = record.age

        resolved: list[FileRecord] = []
        for record in records:
            if record.age is None:
                inferred = age_by_key.get((record.animal, record.tracing))
                if inferred is not None:
                    record = FileRecord(
                        path=record.path,
                        filename=record.filename,
                        family=record.family,
                        animal=record.animal,
                        tracing=record.tracing,
                        age=inferred,
                        cell_id=f"{record.animal}_{record.tracing}_{inferred}",
                        subtype=record.subtype,
                    )
            resolved.append(record)

        grouped: dict[tuple[str, str, str | None], list[FileRecord]] = defaultdict(list)
        for record in resolved:
            grouped[(record.animal, record.tracing, record.age)].append(record)

        cells: dict[str, CellData] = {}
        for (animal, tracing, age), files in grouped.items():
            cell_id = f"{animal}_{tracing}" + (f"_{age}" if age else "")
            cells[cell_id] = CellData(
                cell_id=cell_id,
                animal=animal,
                tracing=tracing,
                age=age,
                files=sorted(files, key=lambda x: (x.family, x.subtype or "")),
            )
        return cls(cells)

    def load_all(self, verbose: bool = True) -> None:
        for cell_id in sorted(self.cells):
            if verbose:
                print(f"\n{'=' * 72}\nReading {cell_id}\n{'=' * 72}")
            cell = self.cells[cell_id]
            for record in cell.files:
                if verbose:
                    subtype = f" ({record.subtype})" if record.subtype else ""
                    print(f"  Reading {record.family}{subtype}: {record.filename}")
            cell.load()
            if verbose:
                summary = cell.summary()
                basic = summary.get("basic", {})
                print(
                    "  Imported: "
                    f"{basic.get('segment_rows', 'n/a')} segments; "
                    f"{basic.get('node_rows', 'n/a')} node rows; "
                    f"{basic.get('ending_rows', 'n/a')} ending rows; "
                    f"{basic.get('segment_length_sum_um', 'n/a')} um cable"
                )
                for warning in cell.warnings:
                    print(f"  WARNING: {warning}")

    def export_all(self, output_dir: str | Path) -> None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for cell in self.cells.values():
            cell.export(output_dir)
