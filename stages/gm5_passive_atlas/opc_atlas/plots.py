from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


AGE_ORDER = ["P10", "P20", "P50"]


def save_figure(fig, base: Path, config: dict) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    for ext in config["figures"].get("formats", ["png"]):
        fig.savefig(base.with_suffix("." + ext), dpi=int(config["figures"].get("dpi", 200)), bbox_inches="tight")
    plt.close(fig)


def metric_distribution(frame: pd.DataFrame, metric: str, ylabel: str, path: Path, config: dict) -> None:
    groups = [pd.to_numeric(frame.loc[frame.age_group == age, metric], errors="coerce").dropna().to_numpy() for age in AGE_ORDER]
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    valid = [(age, x) for age, x in zip(AGE_ORDER, groups) if len(x)]
    if valid:
        labels, data = zip(*valid)
        ax.boxplot(data, tick_labels=labels, showmeans=True)
        rng = np.random.default_rng(12345)
        for i, x in enumerate(data, start=1):
            jitter = rng.normal(i, 0.035, size=len(x))
            ax.scatter(jitter, x, alpha=.7, s=20)
    ax.set_xlabel("Age group")
    ax.set_ylabel(ylabel)
    ax.set_title(ylabel + " across reconstructed OPCs")
    ax.grid(axis="y", alpha=.25)
    save_figure(fig, path, config)


def attenuation_by_distance(attenuation: pd.DataFrame, path: Path, config: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    for age in AGE_ORDER:
        group = attenuation.loc[attenuation.age_group == age].dropna(subset=["distance_bin_centre_um", "soma_normalised_attenuation"])
        if group.empty:
            continue
        summary = group.groupby("distance_bin_centre_um")["soma_normalised_attenuation"].agg(["mean", "sem"]).reset_index()
        ax.plot(summary.distance_bin_centre_um, summary["mean"], marker="o", label=age)
        ax.fill_between(summary.distance_bin_centre_um, summary["mean"] - summary["sem"].fillna(0), summary["mean"] + summary["sem"].fillna(0), alpha=.15)
    ax.axhline(1.0, linewidth=.8, linestyle="--")
    ax.set_xlabel("Path distance from soma (µm)")
    ax.set_ylabel("Soma-normalised voltage deflection")
    ax.set_title("Passive attenuation profile")
    ax.legend()
    ax.grid(alpha=.25)
    save_figure(fig, path, config)


def morphology_electrophysiology(frame: pd.DataFrame, x_metric: str, y_metric: str, path: Path, config: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    for age in AGE_ORDER:
        g = frame.loc[frame.age_group == age]
        ax.scatter(g[x_metric], g[y_metric], label=age, alpha=.8)
    x = pd.to_numeric(frame[x_metric], errors="coerce")
    y = pd.to_numeric(frame[y_metric], errors="coerce")
    mask = x.notna() & y.notna()
    if mask.sum() >= 2:
        coeff = np.polyfit(x[mask], y[mask], 1)
        xx = np.linspace(x[mask].min(), x[mask].max(), 100)
        ax.plot(xx, coeff[0] * xx + coeff[1], linestyle="--", linewidth=1)
    ax.set_xlabel(x_metric.replace("_", " "))
    ax.set_ylabel(y_metric.replace("_", " "))
    ax.set_title("Morphology–electrophysiology relationship")
    ax.legend()
    ax.grid(alpha=.25)
    save_figure(fig, path, config)


def soma_trace(trace: pd.DataFrame, cell_id: str, path: Path, config: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    ax.plot(trace["time_ms"], trace["soma_mV"])
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Somatic voltage (mV)")
    ax.set_title(f"Standard passive current step — {cell_id}")
    ax.grid(alpha=.25)
    save_figure(fig, path, config)


def cell_attenuation_map(attenuation: pd.DataFrame, cell_id: str, path: Path, config: dict) -> None:
    frame = attenuation.dropna(subset=["path_distance_um", "soma_normalised_attenuation"])
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    if not frame.empty:
        sc = ax.scatter(frame["path_distance_um"], frame["soma_normalised_attenuation"], c=frame.get("order", pd.Series(index=frame.index, dtype=float)), alpha=.8)
        fig.colorbar(sc, ax=ax, label="Branch order")
    ax.set_xlabel("Path distance from soma (µm)")
    ax.set_ylabel("Soma-normalised voltage deflection")
    ax.set_title(f"Passive attenuation — {cell_id}")
    ax.grid(alpha=.25)
    save_figure(fig, path, config)
