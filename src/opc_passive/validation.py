
from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import json
import math
from collections import defaultdict

import numpy as np


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _distance(a: list[float], b: list[float]) -> float:
    return math.dist(a, b)


def _sphere_crossings(
    start: np.ndarray,
    end: np.ndarray,
    centre: np.ndarray,
    radius: float,
    eps: float = 1e-9,
) -> list[float]:
    """Return line-segment parameters t in (0,1] crossing a sphere."""
    direction = end - start
    rel = start - centre
    aa = float(np.dot(direction, direction))
    if aa <= eps:
        return []
    bb = 2.0 * float(np.dot(rel, direction))
    cc = float(np.dot(rel, rel) - radius * radius)
    discriminant = bb * bb - 4.0 * aa * cc
    if discriminant < -eps:
        return []
    discriminant = max(0.0, discriminant)
    root = math.sqrt(discriminant)
    values = [(-bb - root) / (2.0 * aa), (-bb + root) / (2.0 * aa)]
    result: list[float] = []
    for value in values:
        if eps < value <= 1.0 + eps:
            value = min(1.0, max(0.0, value))
            if not result or abs(value - result[-1]) > 1e-7:
                result.append(value)
    return sorted(result)


def _segment_shell_fractions(
    start: np.ndarray,
    end: np.ndarray,
    centre: np.ndarray,
    shell_edges: list[float],
) -> list[float]:
    """
    Fraction of the straight chord in each radial shell.

    The measured cable length is later distributed according to these fractions,
    so total measured segment length is preserved despite tortuosity.
    """
    direction = end - start
    chord = float(np.linalg.norm(direction))
    if chord == 0:
        radius = float(np.linalg.norm(start - centre))
        fractions = [0.0] * (len(shell_edges) - 1)
        for k in range(1, len(shell_edges)):
            if shell_edges[k - 1] <= radius < shell_edges[k]:
                fractions[k - 1] = 1.0
                break
        return fractions

    ts = [0.0, 1.0]
    for radius in shell_edges[1:-1]:
        ts.extend(_sphere_crossings(start, end, centre, radius))
    ts = sorted(set(round(t, 12) for t in ts))

    fractions = [0.0] * (len(shell_edges) - 1)
    for left, right in zip(ts[:-1], ts[1:]):
        if right <= left:
            continue
        midpoint = start + (0.5 * (left + right)) * direction
        radial = float(np.linalg.norm(midpoint - centre))
        for k in range(1, len(shell_edges)):
            lower, upper = shell_edges[k - 1], shell_edges[k]
            if lower <= radial < upper or (
                k == len(shell_edges) - 1 and math.isclose(radial, upper)
            ):
                fractions[k - 1] += right - left
                break
    return fractions


def recompute_sholl(
    reconstruction: dict[str, Any],
    measured_rows: list[dict[str, str]],
) -> list[dict[str, float]]:
    radii = [
        value for value in (_num(row.get("radius_um")) for row in measured_rows)
        if value is not None
    ]
    radii = sorted(set(radii))
    if not radii:
        return []
    spacing = min(
        (b - a for a, b in zip(radii[:-1], radii[1:]) if b > a),
        default=2.5,
    )
    shell_edges = [max(0.0, radii[0] - spacing)] + radii
    centre = np.asarray(reconstruction["soma_centroid"], dtype=float)

    result = {
        radius: {
            "radius_um": radius,
            "intersections_reconstructed": 0.0,
            "length_reconstructed_um": 0.0,
            "nodes_reconstructed": 0.0,
            "endings_reconstructed": 0.0,
        }
        for radius in radii
    }

    for segment in reconstruction["segments"]:
        if segment["end"] is None:
            continue
        start = np.asarray(segment["start"], dtype=float)
        end = np.asarray(segment["end"], dtype=float)
        length = float(segment["length_um"])
        fractions = _segment_shell_fractions(start, end, centre, shell_edges)
        for index, fraction in enumerate(fractions):
            result[radii[index]]["length_reconstructed_um"] += length * fraction

        for radius in radii:
            result[radius]["intersections_reconstructed"] += len(
                _sphere_crossings(start, end, centre, radius)
            )

        endpoint_radius = float(np.linalg.norm(end - centre))
        target_radius = next((r for r in radii if endpoint_radius <= r + 1e-9), None)
        if target_radius is not None:
            if str(segment["terminal_type"]).lower() == "branch":
                result[target_radius]["nodes_reconstructed"] += 1.0
            else:
                result[target_radius]["endings_reconstructed"] += 1.0

    measured_by_radius = {}
    for row in measured_rows:
        radius = _num(row.get("radius_um"))
        if radius is None:
            continue
        measured_by_radius[radius] = {
            "intersections_measured": _num(row.get("intersections")) or 0.0,
            "length_measured_um": _num(row.get("length_um")) or 0.0,
            "nodes_measured": _num(row.get("nodes")) or 0.0,
            "endings_measured": _num(row.get("endings")) or 0.0,
        }

    output = []
    for radius in radii:
        row = dict(result[radius])
        row.update(measured_by_radius.get(radius, {}))
        output.append(row)
    return output


def _metrics(measured: list[float], reconstructed: list[float]) -> dict[str, float | None]:
    if not measured:
        return {"mae": None, "rmse": None, "correlation": None, "relative_l1": None}
    a = np.asarray(measured, dtype=float)
    b = np.asarray(reconstructed, dtype=float)
    mae = float(np.mean(np.abs(a - b)))
    rmse = float(np.sqrt(np.mean((a - b) ** 2)))
    denom = float(np.sum(np.abs(a)))
    rel = float(np.sum(np.abs(a - b)) / denom) if denom > 0 else None
    correlation = None
    if len(a) >= 2 and np.std(a) > 0 and np.std(b) > 0:
        correlation = float(np.corrcoef(a, b)[0, 1])
    return {"mae": mae, "rmse": rmse, "correlation": correlation, "relative_l1": rel}


def sholl_metrics(rows: list[dict[str, float]]) -> dict[str, Any]:
    result = {}
    pairs = {
        "length": ("length_measured_um", "length_reconstructed_um"),
        "intersections": ("intersections_measured", "intersections_reconstructed"),
        "nodes": ("nodes_measured", "nodes_reconstructed"),
        "endings": ("endings_measured", "endings_reconstructed"),
    }
    for name, (m_key, r_key) in pairs.items():
        result[name] = _metrics(
            [row.get(m_key, 0.0) for row in rows],
            [row.get(r_key, 0.0) for row in rows],
        )
        result[name]["measured_total"] = sum(row.get(m_key, 0.0) for row in rows)
        result[name]["reconstructed_total"] = sum(row.get(r_key, 0.0) for row in rows)
    return result


def _points_from_reconstruction(
    reconstruction: dict[str, Any],
    kind: str,
) -> list[list[float]]:
    if kind == "branch":
        return [
            segment["end"] for segment in reconstruction["segments"]
            if segment["end"] is not None
            and str(segment["terminal_type"]).lower() == "branch"
        ]
    return [
        segment["end"] for segment in reconstruction["segments"]
        if segment["end"] is not None
        and str(segment["terminal_type"]).lower() != "branch"
    ]


def _nearest_distances(points: list[list[float]]) -> list[float]:
    if len(points) < 2:
        return []
    arr = np.asarray(points, dtype=float)
    distances = np.sqrt(
        np.sum((arr[:, None, :] - arr[None, :, :]) ** 2, axis=2)
    )
    np.fill_diagonal(distances, np.inf)
    return np.min(distances, axis=1).tolist()


def validate_nearest_neighbour(
    reconstruction: dict[str, Any],
    nn_rows: list[dict[str, str]],
) -> dict[str, Any]:
    measured_points: list[list[float]] = []
    measured_nearest: list[float] = []
    # The three uploaded NN workbooks use slightly different coordinate
    # headers. The first three columns after ``termination`` are consistently
    # the X, Y, and Z coordinates of the selected point.
    coordinate_keys: list[str] = []
    if nn_rows:
        keys = list(nn_rows[0].keys())
        try:
            start_index = keys.index("termination") + 1
        except ValueError:
            start_index = 1
        coordinate_keys = keys[start_index : start_index + 3]

    for row in nn_rows:
        try:
            point = [float(row[key]) for key in coordinate_keys]
        except (KeyError, TypeError, ValueError):
            continue
        measured_points.append(point)
        value = _num(row.get("nearest_neighbor_um"))
        if value is not None:
            measured_nearest.append(value)

    candidate_results = {}
    for kind in ("branch", "terminal"):
        candidate_points = _points_from_reconstruction(reconstruction, kind)
        if not measured_points or not candidate_points:
            continue
        minimum_distances = [
            min(_distance(point, candidate) for candidate in candidate_points)
            for point in measured_points
        ]
        candidate_nearest = _nearest_distances(candidate_points)
        n_compare = min(len(measured_nearest), len(candidate_nearest))
        candidate_results[kind] = {
            "candidate_point_count": len(candidate_points),
            "measured_point_count": len(measured_points),
            "mean_coordinate_mismatch_um": float(np.mean(minimum_distances)),
            "median_coordinate_mismatch_um": float(np.median(minimum_distances)),
            "points_within_0_15_um": sum(x <= 0.15 for x in minimum_distances),
            # Compare sorted distributions because workbook row order and
            # reconstructed segment order need not be identical.
            "nearest_distance_metrics": _metrics(
                sorted(measured_nearest)[:n_compare],
                sorted(candidate_nearest)[:n_compare],
            ),
        }

    matched_kind = min(
        candidate_results,
        key=lambda key: candidate_results[key]["mean_coordinate_mismatch_um"],
    ) if candidate_results else None
    return {
        "matched_coordinate_set": matched_kind,
        "candidates": candidate_results,
        "note": (
            "The best-matching reconstructed endpoint class is selected from "
            "branch points and terminal endings because the uploaded NN headers "
            "use the generic label 'termination'."
        ),
    }


def validate_angles(
    reconstruction: dict[str, Any],
    angle_rows: list[dict[str, str]],
) -> dict[str, Any]:
    reconstructed = []
    for segment in reconstruction["segments"]:
        if segment["end"] is None:
            continue
        start = np.asarray(segment["start"], dtype=float)
        end = np.asarray(segment["end"], dtype=float)
        vector = end - start
        horizontal = math.hypot(float(vector[0]), float(vector[1]))
        xy = math.degrees(math.atan2(float(vector[1]), float(vector[0]))) % 360.0
        z = math.degrees(math.atan2(float(vector[2]), horizontal))
        reconstructed.append((xy, z))

    measured_xy = [
        value for value in (_num(row.get("xy_angle")) for row in angle_rows)
        if value is not None
    ]
    measured_z = [
        value for value in (_num(row.get("z_angle")) for row in angle_rows)
        if value is not None
    ]
    rec_xy = [value[0] for value in reconstructed]
    rec_z = [value[1] for value in reconstructed]

    def circular_error(measured: list[float], rec: list[float]) -> dict[str, float | None]:
        n = min(len(measured), len(rec))
        if n == 0:
            return {"mean_absolute_deg": None, "maximum_absolute_deg": None}
        errors = [
            min(abs(measured[i] - rec[i]) % 360.0, 360.0 - abs(measured[i] - rec[i]) % 360.0)
            for i in range(n)
        ]
        return {
            "mean_absolute_deg": float(np.mean(errors)),
            "maximum_absolute_deg": float(np.max(errors)),
        }

    return {
        "xy_angle": circular_error(measured_xy, rec_xy),
        "z_angle": _metrics(measured_z[:len(rec_z)], rec_z[:len(measured_z)]),
        "measured_rows": len(angle_rows),
        "reconstructed_segments": len(reconstructed),
    }


def validate_branch_order(
    reconstruction: dict[str, Any],
    order_sholl_rows: list[dict[str, str]],
) -> dict[str, Any]:
    reconstructed_by_order: dict[int, float] = defaultdict(float)
    for segment in reconstruction["segments"]:
        reconstructed_by_order[int(segment["order"])] += float(segment["length_um"])

    measured_by_order: dict[int, float] = defaultdict(float)
    for row in order_sholl_rows:
        for key, value in row.items():
            if key.startswith("order_") and key.endswith("_um"):
                try:
                    order = int(key.split("_")[1])
                except (IndexError, ValueError):
                    continue
                number = _num(value)
                if number is not None:
                    measured_by_order[order] += number

    orders = sorted(set(reconstructed_by_order) | set(measured_by_order))
    rows = [
        {
            "order": order,
            "measured_length_um": measured_by_order.get(order, 0.0),
            "reconstructed_length_um": reconstructed_by_order.get(order, 0.0),
        }
        for order in orders
    ]
    metrics = _metrics(
        [row["measured_length_um"] for row in rows],
        [row["reconstructed_length_um"] for row in rows],
    )
    return {"rows": rows, "metrics": metrics}


def validate_cell(
    reconstruction_path: str | Path,
    sholl_path: str | Path,
    sholl_order_path: str | Path,
    nn_path: str | Path,
    angles_path: str | Path,
) -> dict[str, Any]:
    reconstruction = json.loads(Path(reconstruction_path).read_text(encoding="utf-8"))
    sholl_rows = _read_csv(sholl_path)
    sholl_order_rows = _read_csv(sholl_order_path)
    nn_rows = _read_csv(nn_path)
    angle_rows = _read_csv(angles_path)

    sholl = recompute_sholl(reconstruction, sholl_rows)
    return {
        "cell_id": reconstruction["cell_id"],
        "sholl_rows": sholl,
        "sholl_metrics": sholl_metrics(sholl),
        "branch_order": validate_branch_order(reconstruction, sholl_order_rows),
        "nearest_neighbour": validate_nearest_neighbour(reconstruction, nn_rows),
        "angles": validate_angles(reconstruction, angle_rows),
    }
