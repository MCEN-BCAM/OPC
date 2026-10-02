
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json
import math

from neuron import h

h.load_file("stdrun.hoc")


@dataclass(frozen=True)
class PassiveParameters:
    rm_ohm_cm2: float = 20_000.0
    ra_ohm_cm: float = 150.0
    cm_uF_cm2: float = 1.0
    e_pas_mV: float = -75.0
    process_diameter_um: float = 0.30
    d_lambda_frequency_Hz: float = 100.0
    d_lambda_fraction: float = 0.10

    @property
    def g_pas_S_cm2(self) -> float:
        if self.rm_ohm_cm2 <= 0:
            raise ValueError("rm_ohm_cm2 must be positive")
        return 1.0 / self.rm_ohm_cm2


@dataclass(frozen=True)
class SegmentMetadata:
    segment_id: int
    tree: int
    order: int
    parent_id: int | None
    child_ids: tuple[int, ...]
    terminal_type: str
    measured_length_um: float
    tortuosity: float
    start_xyz_um: tuple[float, float, float]
    end_xyz_um: tuple[float, float, float]
    radial_start_um: float | None
    radial_end_um: float | None
    cable_path_end_um: float


class PassiveOPCCell:
    """One passive NEURON cell built from one reconstructed experimental OPC."""

    def __init__(
        self,
        reconstruction: dict[str, Any],
        parameters: PassiveParameters | None = None,
    ) -> None:
        self.reconstruction = reconstruction
        self.cell_id = str(reconstruction["cell_id"])
        self.parameters = parameters or PassiveParameters()
        self.soma = None
        self.sections_by_segment: dict[int, Any] = {}
        self.metadata_by_segment: dict[int, SegmentMetadata] = {}
        self._built = False
        self._deleted = False

    @classmethod
    def from_json(
        cls,
        path: str | Path,
        parameters: PassiveParameters | None = None,
    ) -> "PassiveOPCCell":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data, parameters)

    @property
    def all_sections(self) -> list[Any]:
        return ([] if self.soma is None else [self.soma]) + list(
            self.sections_by_segment.values()
        )

    def _insert_passive(self, section: Any) -> None:
        p = self.parameters
        section.Ra = p.ra_ohm_cm
        section.cm = p.cm_uF_cm2
        section.insert("pas")
        for seg in section:
            seg.pas.g = p.g_pas_S_cm2
            seg.pas.e = p.e_pas_mV

    def _assign_nseg(self, section: Any) -> None:
        p = self.parameters
        lam = float(h.lambda_f(p.d_lambda_frequency_Hz, sec=section))
        if lam <= 0:
            section.nseg = 1
            return
        nseg = int((section.L / (p.d_lambda_fraction * lam) + 0.9) / 2.0) * 2 + 1
        section.nseg = max(1, nseg)
        if section.nseg % 2 == 0:
            section.nseg += 1

    def _soma_dimensions(self) -> tuple[float, float]:
        area = self.reconstruction.get("soma_area_um2")
        if area is None or float(area) <= 0:
            return 5.0, 5.0
        dimension = math.sqrt(float(area) / math.pi)
        return dimension, dimension

    def _path_lengths(self) -> dict[int, float]:
        records = {int(x["segment_id"]): x for x in self.reconstruction["segments"]}
        cache: dict[int, float] = {}

        def visit(segment_id: int, active: set[int]) -> float:
            if segment_id in cache:
                return cache[segment_id]
            if segment_id in active:
                raise ValueError(f"Cycle detected at segment {segment_id}")
            active.add(segment_id)
            row = records[segment_id]
            own = float(row["length_um"])
            parent = row.get("parent_id")
            total = own if parent is None else visit(int(parent), active) + own
            active.remove(segment_id)
            cache[segment_id] = total
            return total

        for segment_id in records:
            visit(segment_id, set())
        return cache

    def build(self) -> "PassiveOPCCell":
        if self._built:
            return self
        if self._deleted:
            raise RuntimeError("Deleted cells cannot be rebuilt")

        path_lengths = self._path_lengths()
        centre = self.reconstruction.get("soma_centroid")

        self.soma = h.Section(name=f"{self.cell_id}_soma")
        self.soma.L, self.soma.diam = self._soma_dimensions()
        self._insert_passive(self.soma)
        self._assign_nseg(self.soma)

        for row in self.reconstruction["segments"]:
            sid = int(row["segment_id"])
            sec = h.Section(name=f"{self.cell_id}_seg_{sid}")
            sec.L = float(row["length_um"])
            sec.diam = self.parameters.process_diameter_um
            self._insert_passive(sec)
            self._assign_nseg(sec)
            self.sections_by_segment[sid] = sec

            start = tuple(float(x) for x in row["start"])
            end = tuple(float(x) for x in row["end"])
            if centre is None:
                radial_start = radial_end = None
            else:
                c = tuple(float(x) for x in centre)
                radial_start = math.dist(start, c)
                radial_end = math.dist(end, c)

            self.metadata_by_segment[sid] = SegmentMetadata(
                segment_id=sid,
                tree=int(row["tree"]),
                order=int(row["order"]),
                parent_id=None if row.get("parent_id") is None else int(row["parent_id"]),
                child_ids=tuple(int(x) for x in row.get("child_ids", [])),
                terminal_type=str(row["terminal_type"]),
                measured_length_um=float(row["length_um"]),
                tortuosity=float(row["tortuosity"]),
                start_xyz_um=start,
                end_xyz_um=end,
                radial_start_um=radial_start,
                radial_end_um=radial_end,
                cable_path_end_um=path_lengths[sid],
            )

        for sid, metadata in self.metadata_by_segment.items():
            child = self.sections_by_segment[sid]
            if metadata.parent_id is None:
                child.connect(self.soma(1.0), 0.0)
            else:
                child.connect(self.sections_by_segment[metadata.parent_id](1.0), 0.0)

        self._built = True
        return self

    def roots(self) -> list[int]:
        return [sid for sid, m in self.metadata_by_segment.items() if m.parent_id is None]

    def terminals(self) -> list[int]:
        return [
            sid for sid, m in self.metadata_by_segment.items()
            if m.terminal_type.lower() != "branch"
        ]

    def by_order(self, order: int) -> list[int]:
        return [sid for sid, m in self.metadata_by_segment.items() if m.order == order]

    def path_distance_um(self, segment_id: int, location: float = 0.5) -> float:
        m = self.metadata_by_segment[segment_id]
        return m.cable_path_end_um - (1.0 - location) * m.measured_length_um

    def radial_distance_um(self, segment_id: int, location: float = 0.5) -> float | None:
        m = self.metadata_by_segment[segment_id]
        if m.radial_start_um is None or m.radial_end_um is None:
            return None
        return m.radial_start_um + location * (m.radial_end_um - m.radial_start_um)

    def validate(self) -> dict[str, Any]:
        if not self._built:
            raise RuntimeError("Call build() first")

        source_rows = self.reconstruction["segments"]
        source_ids = {int(x["segment_id"]) for x in source_rows}
        built_ids = set(self.sections_by_segment)
        source_length = sum(float(x["length_um"]) for x in source_rows)
        built_length = sum(float(sec.L) for sec in self.sections_by_segment.values())

        bad_parents: list[int] = []
        for sid, metadata in self.metadata_by_segment.items():
            parent_ref = h.SectionRef(sec=self.sections_by_segment[sid]).parent
            expected = self.soma if metadata.parent_id is None else self.sections_by_segment[metadata.parent_id]
            if parent_ref is None or parent_ref.name() != expected.name():
                bad_parents.append(sid)

        missing_pas = [
            sec.name() for sec in self.all_sections
            if not h.ismembrane("pas", sec=sec)
        ]
        nseg_values = [int(sec.nseg) for sec in self.all_sections]

        target_area = self.reconstruction.get("soma_area_um2")
        neuron_area = sum(float(h.area(seg.x, sec=self.soma)) for seg in self.soma)

        ready = (
            source_ids == built_ids
            and abs(source_length - built_length) < 1e-8
            and not bad_parents
            and not missing_pas
        )

        return {
            "cell_id": self.cell_id,
            "neuron_version": str(h.nrnversion()),
            "parameters": asdict(self.parameters),
            "source_segment_count": len(source_rows),
            "built_process_section_count": len(self.sections_by_segment),
            "total_section_count_including_soma": len(self.all_sections),
            "source_ids_equal_built_ids": source_ids == built_ids,
            "source_total_cable_length_um": source_length,
            "built_total_process_length_um": built_length,
            "absolute_length_error_um": abs(source_length - built_length),
            "root_section_count": len(self.roots()),
            "terminal_section_count": len(self.terminals()),
            "maximum_branch_order": max(m.order for m in self.metadata_by_segment.values()),
            "parent_connection_errors": bad_parents,
            "passive_mechanism_missing": missing_pas,
            "nseg_minimum": min(nseg_values),
            "nseg_maximum": max(nseg_values),
            "nseg_total": sum(nseg_values),
            "soma_length_um": float(self.soma.L),
            "soma_diameter_um": float(self.soma.diam),
            "soma_area_target_um2": target_area,
            "soma_area_neuron_um2": neuron_area,
            "ready_for_simulation": ready,
        }

    def resting_smoke_test(
        self,
        duration_ms: float = 5.0,
        dt_ms: float = 0.025,
    ) -> dict[str, Any]:
        if not self._built:
            raise RuntimeError("Call build() first")

        h.dt = dt_ms
        h.steps_per_ms = 1.0 / dt_ms
        h.tstop = duration_ms
        t = h.Vector().record(h._ref_t)
        soma_v = h.Vector().record(self.soma(0.5)._ref_v)
        sample_id = min(self.sections_by_segment)
        process_v = h.Vector().record(self.sections_by_segment[sample_id](0.5)._ref_v)

        h.finitialize(self.parameters.e_pas_mV)
        h.continuerun(duration_ms)

        soma_values = list(soma_v)
        process_values = list(process_v)
        deviations = [
            abs(v - self.parameters.e_pas_mV)
            for v in soma_values + process_values
        ]
        max_deviation = max(deviations, default=0.0)

        return {
            "duration_ms": duration_ms,
            "dt_ms": dt_ms,
            "samples": len(t),
            "sample_segment_id": sample_id,
            "soma_initial_mV": soma_values[0],
            "soma_final_mV": soma_values[-1],
            "process_initial_mV": process_values[0],
            "process_final_mV": process_values[-1],
            "maximum_resting_deviation_mV": max_deviation,
            "stable_at_rest": max_deviation < 1e-9,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "validation": self.validate(),
            "resting_smoke_test": self.resting_smoke_test(),
            "metadata_examples": [
                asdict(self.metadata_by_segment[sid])
                for sid in sorted(self.metadata_by_segment)[:3]
            ],
        }

    def delete(self) -> None:
        if self._deleted:
            return
        for sec in list(self.all_sections):
            h.delete_section(sec=sec)
        self.soma = None
        self.sections_by_segment.clear()
        self.metadata_by_segment.clear()
        self._built = False
        self._deleted = True

    def __enter__(self) -> "PassiveOPCCell":
        return self.build()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.delete()
