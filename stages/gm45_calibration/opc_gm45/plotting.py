from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .utils import ensure_dir


COLORS = {"P10": "#377eb8", "P20": "#4daf4a", "P50": "#e41a1c"}


def make_figures(summary: list[dict], targets: dict, output_dir: str | Path) -> list[Path]:
    output_dir = ensure_dir(output_dir)
    made = []
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    for age, color in COLORS.items():
        rows = sorted((r for r in summary if r["age"] == age), key=lambda r: r["rm_kohm_cm2"])
        x = [r["rm_kohm_cm2"] for r in rows]; y = [r["mean_rin_mohm"] for r in rows]
        sem = [r["sem_rin_mohm"] for r in rows]
        ax.plot(x, y, marker="o", color=color, label=f"{age} model")
        ax.fill_between(x, [a-b for a,b in zip(y,sem)], [a+b for a,b in zip(y,sem)], color=color, alpha=.15)
        target = targets[age]
        ax.axhspan(target["mean_mohm"]-target["sem_mohm"], target["mean_mohm"]+target["sem_mohm"], color=color, alpha=.08)
        ax.axhline(target["mean_mohm"], color=color, linestyle="--", linewidth=1)
    ax.set(xlabel=r"$R_m$ (k$\Omega\,cm^2$)", ylabel=r"Input resistance (M$\Omega$)")
    ax.legend(frameon=False); ax.grid(alpha=.2); fig.tight_layout()
    for suffix in ("png", "pdf"):
        path = output_dir / f"Figure1_Model_vs_Experiment.{suffix}"; fig.savefig(path, dpi=300); made.append(path)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    for age, color in COLORS.items():
        rows = sorted((r for r in summary if r["age"] == age), key=lambda r: r["rm_kohm_cm2"])
        ax.plot([r["rm_kohm_cm2"] for r in rows], [100*r["relative_error"] for r in rows], marker="o", color=color, label=age)
    ax.axhline(0, color="black", linewidth=1); ax.set(xlabel=r"$R_m$ (k$\Omega\,cm^2$)", ylabel="Relative calibration error (%)")
    ax.legend(frameon=False); ax.grid(alpha=.2); fig.tight_layout()
    for suffix in ("png", "pdf"):
        path = output_dir / f"Figure2_Relative_Calibration_Error.{suffix}"; fig.savefig(path, dpi=300); made.append(path)
    plt.close(fig)
    return made

