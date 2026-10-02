from __future__ import annotations

from collections import defaultdict
from statistics import mean, stdev

from .interpolation import crossing_rm


AGES = ("P10", "P20", "P50")


def summarize(rows: list[dict], targets: dict) -> tuple[list[dict], list[dict], list[dict]]:
    grouped: dict[tuple[str, float], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["age"]), float(row["rm_kohm_cm2"]))].append(float(row["rin_mohm"]))
    summary = []
    for (age, rm), values in sorted(grouped.items()):
        target = float(targets[age]["mean_mohm"])
        sd = stdev(values) if len(values) > 1 else 0.0
        sem = sd / len(values) ** 0.5
        avg = mean(values)
        summary.append({"age": age, "rm_kohm_cm2": rm, "n_cells": len(values),
                        "mean_rin_mohm": avg, "sd_rin_mohm": sd, "sem_rin_mohm": sem,
                        "experimental_rin_mohm": target,
                        "relative_error": (avg - target) / target,
                        "absolute_relative_error": abs(avg - target) / target})
    best, comparison = [], []
    for age in AGES:
        curve = sorted((r for r in summary if r["age"] == age), key=lambda r: r["rm_kohm_cm2"])
        if not curve:
            continue
        winner_index = min(range(len(curve)), key=lambda i: curve[i]["absolute_relative_error"])
        winner = curve[winner_index]
        neighbours = [curve[i] for i in (winner_index - 1, winner_index + 1) if 0 <= i < len(curve)]
        inferred, bracketed = crossing_rm([r["rm_kohm_cm2"] for r in curve],
                                         [r["mean_rin_mohm"] for r in curve],
                                         float(targets[age]["mean_mohm"]))
        best.append({"age": age, "best_grid_rm_kohm_cm2": winner["rm_kohm_cm2"],
                     "interpolated_rm_kohm_cm2": inferred, "target_bracketed": bracketed,
                     "minimum_relative_error": winner["absolute_relative_error"],
                     "neighbouring_rm_values": ";".join(str(r["rm_kohm_cm2"]) for r in neighbours),
                     "neighbouring_errors": ";".join(str(r["absolute_relative_error"]) for r in neighbours)})
        comparison.append({"age": age, "experimental_mean_rin_mohm": targets[age]["mean_mohm"],
                           "experimental_sem_rin_mohm": targets[age]["sem_mohm"],
                           "best_model_mean_rin_mohm": winner["mean_rin_mohm"],
                           "best_grid_rm_kohm_cm2": winner["rm_kohm_cm2"],
                           "interpolated_rm_kohm_cm2": inferred,
                           "absolute_relative_error": winner["absolute_relative_error"]})
    return summary, best, comparison

