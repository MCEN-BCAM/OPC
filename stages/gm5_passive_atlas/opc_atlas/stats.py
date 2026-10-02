from __future__ import annotations

from itertools import combinations
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu


def bootstrap_ci(values: Iterable[float], rng: np.random.Generator, replicates: int, confidence: float) -> tuple[float, float]:
    x = np.asarray(list(values), dtype=float)
    if len(x) == 0:
        return np.nan, np.nan
    estimates = np.empty(replicates)
    for i in range(replicates):
        estimates[i] = np.mean(rng.choice(x, size=len(x), replace=True))
    alpha = 1.0 - confidence
    return float(np.quantile(estimates, alpha / 2)), float(np.quantile(estimates, 1 - alpha / 2))


def cliffs_delta(x: Iterable[float], y: Iterable[float]) -> float:
    a = np.asarray(list(x), dtype=float)
    b = np.asarray(list(y), dtype=float)
    if len(a) == 0 or len(b) == 0:
        return np.nan
    return float(sum((ai > b).sum() - (ai < b).sum() for ai in a) / (len(a) * len(b)))


def holm_adjust(p_values: list[float]) -> list[float]:
    m = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(m, dtype=float)
    running = 0.0
    for rank, idx in enumerate(order):
        candidate = (m - rank) * p_values[idx]
        running = max(running, candidate)
        adjusted[idx] = min(1.0, running)
    return adjusted.tolist()


def descriptive_table(frame: pd.DataFrame, metrics: list[str], config: dict) -> pd.DataFrame:
    rng = np.random.default_rng(int(config["statistics"]["random_seed"]))
    reps = int(config["statistics"]["bootstrap_replicates"])
    conf = float(config["statistics"]["confidence_level"])
    rows = []
    for age, group in frame.groupby("age_group", sort=True):
        for metric in metrics:
            x = pd.to_numeric(group[metric], errors="coerce").dropna().to_numpy()
            if len(x) == 0:
                continue
            lo, hi = bootstrap_ci(x, rng, reps, conf)
            rows.append({
                "age_group": age,
                "metric": metric,
                "n": len(x),
                "mean": float(np.mean(x)),
                "sd": float(np.std(x, ddof=1)) if len(x) > 1 else 0.0,
                "median": float(np.median(x)),
                "iqr": float(np.quantile(x, .75) - np.quantile(x, .25)),
                "minimum": float(np.min(x)),
                "maximum": float(np.max(x)),
                "mean_ci_low": lo,
                "mean_ci_high": hi,
            })
    return pd.DataFrame(rows)


def inferential_table(frame: pd.DataFrame, metrics: list[str], minimum_n: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    omnibus = []
    pairwise = []
    ages = sorted(frame["age_group"].dropna().unique())
    for metric in metrics:
        groups = [pd.to_numeric(frame.loc[frame.age_group == age, metric], errors="coerce").dropna().to_numpy() for age in ages]
        eligible = [(age, x) for age, x in zip(ages, groups) if len(x) >= minimum_n]
        if len(eligible) >= 2:
            pooled = np.concatenate([x for _, x in eligible])
            if np.ptp(pooled) == 0:
                h, p = 0.0, 1.0
            else:
                h, p = kruskal(*[x for _, x in eligible])
            omnibus.append({"metric": metric, "test": "Kruskal-Wallis", "groups": ";".join(a for a, _ in eligible), "statistic": float(h), "p_value": float(p)})
        local = []
        for (age_a, x), (age_b, y) in combinations(eligible, 2):
            u, p = mannwhitneyu(x, y, alternative="two-sided")
            local.append({
                "metric": metric, "group_a": age_a, "group_b": age_b,
                "n_a": len(x), "n_b": len(y), "test": "Mann-Whitney U",
                "statistic": float(u), "p_value": float(p),
                "cliffs_delta": cliffs_delta(x, y),
                "median_difference": float(np.median(x) - np.median(y)),
            })
        if local:
            adjusted = holm_adjust([r["p_value"] for r in local])
            for row, p_adj in zip(local, adjusted):
                row["p_holm"] = p_adj
            pairwise.extend(local)
    return pd.DataFrame(omnibus), pd.DataFrame(pairwise)
