
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from collections import defaultdict, Counter
import ast
import csv
import json
import math

import xlrd
from scipy.optimize import linear_sum_assignment


@dataclass
class Point3D:
    x: float
    y: float
    z: float

    def distance(self, other: "Point3D") -> float:
        return math.sqrt(
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        )

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]


@dataclass
class EndpointRecord:
    tree: int
    order: int
    endpoint_type: str
    start: Point3D
    end: Point3D
    final_piece_length_um: float
    length_to_beginning_um: float | None
    source_row: int


@dataclass
class SegmentRecord:
    segment_id: int
    tree: int
    order: int
    length_um: float
    tortuosity: float
    terminal_type: str
    xy_angle_deg: float | None
    z_angle_deg: float | None
    planar_angle_deg: float | None
    start: Point3D
    end: Point3D | None = None
    endpoint_source_row: int | None = None
    endpoint_match_cost: float | None = None
    parent_id: int | None = None
    child_ids: list[int] | None = None

    def __post_init__(self) -> None:
        if self.child_ids is None:
            self.child_ids = []

    @property
    def straight_length_um(self) -> float | None:
        if self.end is None:
            return None
        return self.start.distance(self.end)

    @property
    def expected_straight_length_um(self) -> float:
        if self.tortuosity > 0:
            return self.length_um / self.tortuosity
        return self.length_um

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["start"] = self.start.to_list()
        result["end"] = None if self.end is None else self.end.to_list()
        result["straight_length_um"] = self.straight_length_um
        result["expected_straight_length_um"] = self.expected_straight_length_um
        return result


@dataclass
class ReconstructionResult:
    cell_id: str
    segments: list[SegmentRecord]
    soma_centroid: Point3D | None
    soma_area_um2: float | None
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "soma_centroid": (
                None if self.soma_centroid is None
                else self.soma_centroid.to_list()
            ),
            "soma_area_um2": self.soma_area_um2,
            "diagnostics": self.diagnostics,
            "segments": [segment.to_dict() for segment in self.segments],
        }


def _number(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any) -> int:
    return int(round(float(value)))


def _point_from_tuple_text(value: Any) -> Point3D:
    if isinstance(value, str):
        parsed = ast.literal_eval(value.strip())
    else:
        parsed = value
    return Point3D(float(parsed[0]), float(parsed[1]), float(parsed[2]))


def _angular_difference(a: float, b: float) -> float:
    diff = abs((a - b) % 360.0)
    return min(diff, 360.0 - diff)


def _vector_angles(start: Point3D, end: Point3D) -> tuple[float, float]:
    dx = end.x - start.x
    dy = end.y - start.y
    dz = end.z - start.z
    horizontal = math.sqrt(dx * dx + dy * dy)
    azimuth = math.degrees(math.atan2(dy, dx)) % 360.0
    elevation = math.degrees(math.atan2(dz, horizontal))
    return azimuth, elevation


def _read_legacy_sheet_rows(path: str | Path, sheet_name: str) -> list[list[Any]]:
    book = xlrd.open_workbook(path)
    available = book.sheet_names()
    if sheet_name not in available:
        aliases = {
            'Segment Points-Endings': ['Segment Point-Endings'],
            'Segment Point-Endings': ['Segment Points-Endings'],
        }
        resolved = next((name for name in aliases.get(sheet_name, []) if name in available), None)
        if resolved is None:
            raise ValueError(f'Sheet {sheet_name!r} not found. Available: {available}')
        sheet_name = resolved
    sheet = book.sheet_by_name(sheet_name)
    return [
        [sheet.cell_value(r, c) for c in range(sheet.ncols)]
        for r in range(sheet.nrows)
    ]


def _find_header_row(rows: list[list[Any]], required: tuple[str, ...]) -> int:
    required_low = tuple(x.lower() for x in required)
    for index, row in enumerate(rows):
        text = [str(value).strip().lower() for value in row]
        if all(any(req in item for item in text) for req in required_low):
            return index
    raise ValueError(f"Could not locate header containing {required}.")


def read_endpoint_records(
    basic_path: str | Path,
    sheet_name: str,
    endpoint_type: str,
) -> tuple[list[EndpointRecord], dict[str, Any]]:
    rows = _read_legacy_sheet_rows(basic_path, sheet_name)
    header_index = _find_header_row(rows, ("Tree", "Order", "Start X", "End X"))
    header = [str(value).strip() for value in rows[header_index]]

    def find_column(label: str) -> int:
        for i, value in enumerate(header):
            if value.strip().lower() == label.lower():
                return i
        raise ValueError(f"Missing column {label!r} in {sheet_name}.")

    indices = {
        "tree": find_column("Tree"),
        "order": find_column("Order"),
        "sx": find_column("Start X"),
        "sy": find_column("Start Y"),
        "sz": find_column("Start Z"),
        "ex": find_column("End X"),
        "ey": find_column("End Y"),
        "ez": find_column("End Z"),
    }
    length_index = next(
        (i for i, value in enumerate(header) if "length(" in value.lower()),
        None,
    )
    length_to_beginning_index = next(
        (i for i, value in enumerate(header)
         if "length to beginning" in value.lower()),
        None,
    )

    records: list[EndpointRecord] = []
    skipped = 0
    for source_row, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        try:
            tree = _int(row[indices["tree"]])
            order = _int(row[indices["order"]])
            start = Point3D(
                float(row[indices["sx"]]),
                float(row[indices["sy"]]),
                float(row[indices["sz"]]),
            )
            end = Point3D(
                float(row[indices["ex"]]),
                float(row[indices["ey"]]),
                float(row[indices["ez"]]),
            )
        except (TypeError, ValueError, IndexError):
            skipped += 1
            continue

        records.append(
            EndpointRecord(
                tree=tree,
                order=order,
                endpoint_type=endpoint_type,
                start=start,
                end=end,
                final_piece_length_um=(
                    float(row[length_index])
                    if length_index is not None and row[length_index] != ""
                    else start.distance(end)
                ),
                length_to_beginning_um=(
                    float(row[length_to_beginning_index])
                    if length_to_beginning_index is not None
                    and row[length_to_beginning_index] != ""
                    else None
                ),
                source_row=source_row,
            )
        )
    return records, {
        "sheet": sheet_name,
        "header_row": header_index + 1,
        "records": len(records),
        "skipped_rows": skipped,
    }


def read_segments_from_csv(path: str | Path) -> list[SegmentRecord]:
    rows = list(csv.DictReader(Path(path).open(encoding="utf-8")))
    segments: list[SegmentRecord] = []
    for index, row in enumerate(rows, start=1):
        segments.append(
            SegmentRecord(
                segment_id=index,
                tree=_int(row["tree"]),
                order=_int(row["order"]),
                length_um=float(row["length_um"]),
                tortuosity=float(row["tortuosity"]),
                terminal_type=str(row["terminal_type"]).strip(),
                xy_angle_deg=_number(row.get("xy_angle")),
                z_angle_deg=_number(row.get("z_angle")),
                planar_angle_deg=_number(row.get("planar_angle")),
                start=_point_from_tuple_text(row["base_coordinates"]),
            )
        )
    return segments


def _match_cost(segment: SegmentRecord, endpoint: EndpointRecord) -> float:
    straight = segment.start.distance(endpoint.end)
    expected = max(segment.expected_straight_length_um, 1e-6)
    length_error = abs(straight - expected) / expected

    azimuth, elevation = _vector_angles(segment.start, endpoint.end)
    xy_error = (
        _angular_difference(azimuth, segment.xy_angle_deg) / 180.0
        if segment.xy_angle_deg is not None
        else 0.0
    )
    z_error = (
        abs(elevation - segment.z_angle_deg) / 90.0
        if segment.z_angle_deg is not None
        else 0.0
    )

    # Endpoint's tiny final piece should finish near the calculated endpoint.
    endpoint_piece_error = (
        endpoint.start.distance(endpoint.end)
        - endpoint.final_piece_length_um
    )
    endpoint_piece_error = abs(endpoint_piece_error) / max(
        endpoint.final_piece_length_um, 0.1
    )

    # Angles are highly discriminative in these exports.
    return 3.0 * length_error + 4.0 * xy_error + 4.0 * z_error + 0.2 * endpoint_piece_error


def assign_endpoints(
    segments: list[SegmentRecord],
    nodes: list[EndpointRecord],
    endings: list[EndpointRecord],
) -> dict[str, Any]:
    endpoints_by_type = {
        "branch": nodes,
        "terminal": endings,
    }
    diagnostics: dict[str, Any] = {
        "groups": [],
        "unmatched_segments": [],
        "unmatched_endpoints": [],
    }

    for kind, endpoint_records in endpoints_by_type.items():
        selected_segments = [
            segment for segment in segments
            if (
                (kind == "branch" and segment.terminal_type.lower() == "branch")
                or
                (kind == "terminal" and segment.terminal_type.lower() != "branch")
            )
        ]

        segment_groups: dict[tuple[int, int], list[SegmentRecord]] = defaultdict(list)
        endpoint_groups: dict[tuple[int, int], list[EndpointRecord]] = defaultdict(list)
        for segment in selected_segments:
            segment_groups[(segment.tree, segment.order)].append(segment)
        for endpoint in endpoint_records:
            endpoint_groups[(endpoint.tree, endpoint.order)].append(endpoint)

        all_keys = sorted(set(segment_groups) | set(endpoint_groups))
        for key in all_keys:
            sg = segment_groups.get(key, [])
            eg = endpoint_groups.get(key, [])
            group_info = {
                "kind": kind,
                "tree": key[0],
                "order": key[1],
                "segments": len(sg),
                "endpoints": len(eg),
            }
            if not sg or not eg or len(sg) != len(eg):
                group_info["status"] = "count_mismatch"
                diagnostics["groups"].append(group_info)
                diagnostics["unmatched_segments"].extend(
                    segment.segment_id for segment in sg
                )
                diagnostics["unmatched_endpoints"].extend(
                    endpoint.source_row for endpoint in eg
                )
                continue

            matrix = [
                [_match_cost(segment, endpoint) for endpoint in eg]
                for segment in sg
            ]
            row_indices, column_indices = linear_sum_assignment(matrix)
            costs = []
            for row_i, column_i in zip(row_indices, column_indices):
                segment = sg[row_i]
                endpoint = eg[column_i]
                cost = float(matrix[row_i][column_i])
                segment.end = endpoint.end
                segment.endpoint_source_row = endpoint.source_row
                segment.endpoint_match_cost = cost
                costs.append(cost)

            group_info.update({
                "status": "matched",
                "mean_cost": sum(costs) / len(costs) if costs else None,
                "maximum_cost": max(costs) if costs else None,
            })
            diagnostics["groups"].append(group_info)

    diagnostics["assigned_endpoints"] = sum(
        segment.end is not None for segment in segments
    )
    return diagnostics


def assign_topology(
    segments: list[SegmentRecord],
    coordinate_tolerance_um: float = 0.08,
) -> dict[str, Any]:
    starts_by_tree: dict[int, list[SegmentRecord]] = defaultdict(list)
    for segment in segments:
        starts_by_tree[segment.tree].append(segment)

    ambiguous: list[dict[str, Any]] = []
    missing: list[int] = []
    for segment in segments:
        if segment.order == 1:
            segment.parent_id = None
            continue
        candidates = [
            parent for parent in starts_by_tree[segment.tree]
            if parent.order == segment.order - 1
            and parent.end is not None
            and parent.end.distance(segment.start) <= coordinate_tolerance_um
        ]
        if len(candidates) == 1:
            segment.parent_id = candidates[0].segment_id
            candidates[0].child_ids.append(segment.segment_id)
        elif len(candidates) == 0:
            missing.append(segment.segment_id)
        else:
            candidates.sort(key=lambda parent: parent.end.distance(segment.start))
            segment.parent_id = candidates[0].segment_id
            candidates[0].child_ids.append(segment.segment_id)
            ambiguous.append({
                "segment_id": segment.segment_id,
                "candidate_parent_ids": [x.segment_id for x in candidates],
                "selected_parent_id": candidates[0].segment_id,
            })

    return {
        "coordinate_tolerance_um": coordinate_tolerance_um,
        "missing_parent_segments": missing,
        "ambiguous_parent_segments": ambiguous,
        "root_segments": [
            segment.segment_id for segment in segments if segment.order == 1
        ],
    }


def _detect_cycles(segments: list[SegmentRecord]) -> list[list[int]]:
    by_id = {segment.segment_id: segment for segment in segments}
    cycles: list[list[int]] = []
    for segment in segments:
        seen: list[int] = []
        current = segment
        while current.parent_id is not None:
            if current.segment_id in seen:
                start = seen.index(current.segment_id)
                cycles.append(seen[start:] + [current.segment_id])
                break
            seen.append(current.segment_id)
            current = by_id[current.parent_id]
    unique = []
    signatures = set()
    for cycle in cycles:
        signature = tuple(sorted(set(cycle)))
        if signature not in signatures:
            signatures.add(signature)
            unique.append(cycle)
    return unique


def compute_path_lengths(segments: list[SegmentRecord]) -> dict[int, float]:
    by_id = {segment.segment_id: segment for segment in segments}
    cache: dict[int, float] = {}

    def value(segment: SegmentRecord) -> float:
        if segment.segment_id in cache:
            return cache[segment.segment_id]
        if segment.parent_id is None:
            result = segment.length_um
        else:
            result = value(by_id[segment.parent_id]) + segment.length_um
        cache[segment.segment_id] = result
        return result

    for segment in segments:
        value(segment)
    return cache


def _read_soma(basic_path: str | Path) -> tuple[Point3D | None, float | None]:
    book = xlrd.open_workbook(basic_path)
    area = None
    if "Cell Bodies" in book.sheet_names():
        sheet = book.sheet_by_name("Cell Bodies")
        if sheet.nrows >= 2:
            headers = [str(sheet.cell_value(0, c)).strip().lower() for c in range(sheet.ncols)]
            for c, header in enumerate(headers):
                if "area" in header:
                    try:
                        area = float(sheet.cell_value(1, c))
                    except Exception:
                        pass
                    break

    # The centre exported at the beginning of node/ending sheets is the soma
    # centroid used by the processed analyses.
    centroid = None
    for sheet_name in ("Segment Points-Nodes", "Segment Points-Endings"):
        if sheet_name not in book.sheet_names():
            continue
        sheet = book.sheet_by_name(sheet_name)
        for r in range(min(sheet.nrows, 4)):
            row = [sheet.cell_value(r, c) for c in range(sheet.ncols)]
            if len(row) >= 8:
                try:
                    centroid = Point3D(float(row[5]), float(row[6]), float(row[7]))
                    return centroid, area
                except Exception:
                    pass
    return centroid, area


def reconstruct_cell(
    cell_id: str,
    basic_path: str | Path,
    segment_csv_path: str | Path,
    coordinate_tolerance_um: float = 0.08,
) -> ReconstructionResult:
    segments = read_segments_from_csv(segment_csv_path)
    nodes, node_import = read_endpoint_records(
        basic_path, "Segment Points-Nodes", "branch"
    )
    endings, ending_import = read_endpoint_records(
        basic_path, "Segment Points-Endings", "terminal"
    )

    endpoint_diagnostics = assign_endpoints(segments, nodes, endings)
    topology_diagnostics = assign_topology(
        segments, coordinate_tolerance_um=coordinate_tolerance_um
    )
    path_lengths = compute_path_lengths(segments)
    cycles = _detect_cycles(segments)
    soma_centroid, soma_area = _read_soma(basic_path)

    # Comparison of inferred path length with endpoint table value.
    endpoint_path_errors = []
    endpoints_by_source = {
        endpoint.source_row: endpoint
        for endpoint in nodes + endings
    }
    for segment in segments:
        if segment.endpoint_source_row is None:
            continue
        endpoint = endpoints_by_source[segment.endpoint_source_row]
        if endpoint.length_to_beginning_um is None:
            continue
        endpoint_path_errors.append(
            path_lengths[segment.segment_id] - endpoint.length_to_beginning_um
        )

    branch_segments = [
        segment for segment in segments
        if segment.terminal_type.lower() == "branch"
    ]
    terminal_segments = [
        segment for segment in segments
        if segment.terminal_type.lower() != "branch"
    ]
    child_count_distribution = Counter(len(x.child_ids) for x in segments)

    diagnostics = {
        "node_import": node_import,
        "ending_import": ending_import,
        "source_counts": {
            "segments": len(segments),
            "branch_segments": len(branch_segments),
            "terminal_segments": len(terminal_segments),
            "node_endpoints": len(nodes),
            "terminal_endpoints": len(endings),
        },
        "endpoint_assignment": endpoint_diagnostics,
        "topology": topology_diagnostics,
        "cycles": cycles,
        "total_cable_length_um": sum(x.length_um for x in segments),
        "maximum_branch_order": max(x.order for x in segments),
        "number_of_process_trees": len(set(x.tree for x in segments)),
        "child_count_distribution": dict(sorted(child_count_distribution.items())),
        "endpoint_match_cost": {
            "mean": (
                sum(x.endpoint_match_cost for x in segments if x.endpoint_match_cost is not None)
                / max(1, sum(x.endpoint_match_cost is not None for x in segments))
            ),
            "maximum": max(
                (x.endpoint_match_cost for x in segments if x.endpoint_match_cost is not None),
                default=None,
            ),
        },
        "path_length_error_um": {
            "mean": (
                sum(endpoint_path_errors) / len(endpoint_path_errors)
                if endpoint_path_errors else None
            ),
            "mean_absolute": (
                sum(abs(x) for x in endpoint_path_errors) / len(endpoint_path_errors)
                if endpoint_path_errors else None
            ),
            "maximum_absolute": (
                max((abs(x) for x in endpoint_path_errors), default=None)
            ),
            "n": len(endpoint_path_errors),
        },
    }
    return ReconstructionResult(
        cell_id=cell_id,
        segments=segments,
        soma_centroid=soma_centroid,
        soma_area_um2=soma_area,
        diagnostics=diagnostics,
    )


def export_reconstruction(
    result: ReconstructionResult,
    output_dir: str | Path,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{result.cell_id}_reconstruction.json"
    json_path.write_text(
        json.dumps(result.to_dict(), indent=2),
        encoding="utf-8",
    )

    csv_path = output_dir / f"{result.cell_id}_segments_reconstructed.csv"
    fields = [
        "segment_id", "tree", "order", "parent_id", "child_ids",
        "terminal_type", "length_um", "tortuosity",
        "start_x", "start_y", "start_z",
        "end_x", "end_y", "end_z",
        "straight_length_um", "expected_straight_length_um",
        "xy_angle_deg", "z_angle_deg", "planar_angle_deg",
        "endpoint_source_row", "endpoint_match_cost",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for segment in result.segments:
            writer.writerow({
                "segment_id": segment.segment_id,
                "tree": segment.tree,
                "order": segment.order,
                "parent_id": segment.parent_id,
                "child_ids": ";".join(map(str, segment.child_ids)),
                "terminal_type": segment.terminal_type,
                "length_um": segment.length_um,
                "tortuosity": segment.tortuosity,
                "start_x": segment.start.x,
                "start_y": segment.start.y,
                "start_z": segment.start.z,
                "end_x": None if segment.end is None else segment.end.x,
                "end_y": None if segment.end is None else segment.end.y,
                "end_z": None if segment.end is None else segment.end.z,
                "straight_length_um": segment.straight_length_um,
                "expected_straight_length_um": segment.expected_straight_length_um,
                "xy_angle_deg": segment.xy_angle_deg,
                "z_angle_deg": segment.z_angle_deg,
                "planar_angle_deg": segment.planar_angle_deg,
                "endpoint_source_row": segment.endpoint_source_row,
                "endpoint_match_cost": segment.endpoint_match_cost,
            })

    diagnostics_path = output_dir / f"{result.cell_id}_reconstruction_diagnostics.json"
    diagnostics_path.write_text(
        json.dumps(result.diagnostics, indent=2),
        encoding="utf-8",
    )
