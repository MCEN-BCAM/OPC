import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "analysis" / "reference_outputs" / "calibrated"
GM6_SOURCE = DATA / "gm6" / "figure_source"
DEFAULT_OUT = ROOT / "results" / "paper" / "figures"
OUT = DEFAULT_OUT

AGES = ["P10", "P20", "P50"]
COLORS = {"P10": "#3B82B8", "P20": "#E28E2C", "P50": "#4E9F6D"}


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.8, "figure.dpi": 180,
        "savefig.dpi": 300, "savefig.bbox": "tight",
    })


def panel(ax, letter):
    ax.text(-0.18, 1.07, letter, transform=ax.transAxes, fontsize=12,
            fontweight="bold", va="top")


def jitter_points(ax, frame, metric, ylabel):
    rng = np.random.default_rng(45)
    for i, age in enumerate(AGES):
        vals = frame.loc[frame.age_group == age, metric].dropna().to_numpy()
        x = i + rng.uniform(-0.10, 0.10, len(vals))
        ax.scatter(x, vals, s=24, color=COLORS[age], alpha=0.78,
                   edgecolor="white", linewidth=0.4, zorder=2)
        ax.plot([i - .18, i + .18], [np.median(vals)] * 2, color="black", lw=1.5, zorder=3)
    ax.set_xticks(range(3), AGES)
    ax.set_ylabel(ylabel)


def save(fig, stem):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{stem}.pdf")
    fig.savefig(OUT / f"{stem}.png")
    plt.close(fig)


def calibration_figure():
    summary = pd.read_csv(DATA / "gm45/CalibrationSummary.csv")
    best = pd.read_csv(DATA / "gm45/BestFitParameters.csv")
    comparison = pd.read_csv(DATA / "gm45/ModelExperimentComparison.csv")

    fig, axes = plt.subplots(2, 2, figsize=(8.0, 6.4))
    ax = axes[0, 0]
    for age in AGES:
        d = summary[summary.age == age].sort_values("rm_kohm_cm2")
        ax.plot(d.rm_kohm_cm2, d.mean_rin_mohm, "o-", ms=3.5, lw=1.4,
                color=COLORS[age], label=age)
        ax.axhline(d.experimental_rin_mohm.iloc[0], color=COLORS[age], ls="--", lw=.9)
    ax.set(xlabel=r"$R_m$ (k$\Omega$ cm$^2$)", ylabel=r"Mean $R_{in}$ (M$\Omega$)")
    ax.legend(frameon=False, ncol=3, fontsize=8)
    panel(ax, "A")

    ax = axes[0, 1]
    for age in AGES:
        d = summary[summary.age == age].sort_values("rm_kohm_cm2")
        ax.plot(d.rm_kohm_cm2, 100 * d.relative_error, "o-", ms=3.5,
                lw=1.4, color=COLORS[age], label=age)
    ax.axhline(0, color="0.25", lw=.9)
    ax.set(xlabel=r"$R_m$ (k$\Omega$ cm$^2$)", ylabel="Relative calibration error (%)")
    panel(ax, "B")

    ax = axes[1, 0]
    x = np.arange(3)
    exp = comparison.set_index("age").loc[AGES]
    ax.errorbar(x - .10, exp.experimental_mean_rin_mohm,
                yerr=exp.experimental_sem_rin_mohm, fmt="o", color="black",
                capsize=3, label="Experiment")
    ax.scatter(x + .10, exp.best_model_mean_rin_mohm, marker="s", s=35,
               color=[COLORS[a] for a in AGES], label="Best grid model")
    ax.set_xticks(x, AGES)
    ax.set_ylabel(r"$R_{in}$ (M$\Omega$)")
    ax.legend(frameon=False, fontsize=8)
    panel(ax, "C")

    ax = axes[1, 1]
    vals = best.set_index("age").loc[AGES].interpolated_rm_kohm_cm2
    ax.bar(x, vals, width=.58, color=[COLORS[a] for a in AGES])
    for i, v in enumerate(vals):
        ax.text(i, v + .8, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x, AGES)
    ax.set_ylabel(r"Calibrated $R_m$ (k$\Omega$ cm$^2$)")
    ax.set_ylim(0, 34)
    panel(ax, "D")
    fig.tight_layout(w_pad=2.0, h_pad=2.0)
    save(fig, "Figure2_Rm_calibration")


def passive_figure():
    d = pd.read_csv(DATA / "gm5/accepted_cell_metrics.csv")
    fig, axes = plt.subplots(2, 2, figsize=(8.0, 6.4))
    specs = [
        ("input_resistance_MOhm", r"$R_{in}$ (M$\Omega$)"),
        ("tau_ms", r"Membrane time constant (ms)"),
        ("mean_soma_normalised_attenuation", "Mean soma-normalised attenuation"),
        ("minimum_soma_normalised_attenuation", "Minimum soma-normalised attenuation"),
    ]
    for ax, (metric, label), letter in zip(axes.flat, specs, "ABCD"):
        jitter_points(ax, d, metric, label)
        panel(ax, letter)
    fig.tight_layout(w_pad=2.0, h_pad=2.0)
    save(fig, "Figure3_calibrated_passive_atlas")


def synaptic_figure():
    d = pd.read_csv(DATA / "gm6/cell_level_synaptic_metrics.csv")
    protocols = pd.read_csv(GM6_SOURCE / "all_synaptic_protocols.csv")
    single = protocols.loc[protocols.protocol == "single"].copy()
    temporal = protocols.loc[protocols.protocol == "temporal"].copy()
    spatial = protocols.loc[protocols.protocol == "spatial"].copy()

    fig, axes = plt.subplots(2, 3, figsize=(9.2, 6.4))

    # A: waveform illustration from the P20 cell closest to the cohort-median
    # proximal EPSP amplitude.
    ax = axes[0, 0]
    representative = "NX16_2_P20"
    site_colors = {
        "proximal": "#3B82B8", "intermediate": "#E28E2C", "distal": "#4E9F6D"
    }
    for site in ["distal", "intermediate", "proximal"]:
        trace_path = GM6_SOURCE / f"{representative}_single_{site}_trace.csv"
        trace = pd.read_csv(trace_path)
        delta_v = trace.soma_mV - trace.soma_mV.iloc[0]
        ax.plot(trace.time_ms, delta_v, lw=1.25, color=site_colors[site],
                label=site.capitalize())
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel(r"Somatic $\Delta V$ (mV)")
    ax.set_title("Representative calibrated single-site EPSPs", fontsize=9)
    ax.legend(frameon=False, fontsize=7)
    panel(ax, "A")

    # B: all cell-level single-input amplitudes, retaining both age and site.
    ax = axes[0, 1]
    metrics = [
        ("proximal_epsp_mV", "Proximal", "o", -.18),
        ("intermediate_epsp_mV", "Intermediate", "s", 0),
        ("distal_epsp_mV", "Distal", "^", .18),
    ]
    rng = np.random.default_rng(45)
    for metric, label, marker, offset in metrics:
        for i, age in enumerate(AGES):
            vals = d.loc[d.age_group == age, metric].dropna().to_numpy()
            x = i + offset + rng.uniform(-.025, .025, len(vals))
            ax.scatter(x, vals, s=20, marker=marker, color=COLORS[age],
                       alpha=.72, edgecolor="white", linewidth=.35)
            ax.plot([i + offset - .07, i + offset + .07],
                    [np.median(vals)] * 2, color="black", lw=1.1)
    for _, label, marker, _ in metrics:
        ax.scatter([], [], marker=marker, color="0.35", s=22, label=label)
    ax.set_xticks(range(3), AGES)
    ax.set_ylabel("Somatic EPSP amplitude (mV)")
    ax.set_title("Single-input response by age and site", fontsize=9)
    ax.legend(frameon=False, fontsize=6.8, ncol=1)
    panel(ax, "B")

    # C: cell-level attenuation ratio.
    ax = axes[0, 2]
    jitter_points(ax, d, "distal_to_proximal_ratio",
                  "Distal/proximal EPSP ratio")
    ax.axhline(1, color="0.45", ls="--", lw=.8)
    ax.set_title("Location-dependent attenuation", fontsize=9)
    panel(ax, "C")

    # D: continuous relationship between path distance and somatic amplitude.
    ax = axes[1, 0]
    for age in AGES:
        subset = single.loc[single.age_group == age]
        ax.scatter(subset.path_distance_um, subset.soma_epsp_mV, s=20,
                   color=COLORS[age], alpha=.72, edgecolor="white",
                   linewidth=.35, label=age)
    rho = single.path_distance_um.rank().corr(single.soma_epsp_mV.rank())
    ax.text(.03, .96, rf"Spearman $\rho={rho:.2f}$", transform=ax.transAxes,
            va="top", fontsize=7.5)
    ax.set_xlabel(r"Path distance ($\mu$m)")
    ax.set_ylabel("Somatic EPSP amplitude (mV)")
    ax.set_title("EPSP amplitude vs path distance", fontsize=9)
    ax.legend(frameon=False, fontsize=7)
    panel(ax, "D")

    # E: complete temporal summation curves.
    ax = axes[1, 1]
    intervals = [2, 5, 10, 20, 50]
    for age in AGES:
        subset = temporal.loc[temporal.age_group == age]
        means = subset.groupby("interval_ms").summation_ratio.mean().reindex(intervals)
        sds = subset.groupby("interval_ms").summation_ratio.std().reindex(intervals)
        ax.errorbar(intervals, means, yerr=sds, fmt="o-", capsize=2.2,
                    lw=1.3, ms=3.5, color=COLORS[age], label=age)
    ax.axhline(1, color="0.45", ls="--", lw=.8)
    ax.set_xlabel("Inter-event interval (ms)")
    ax.set_ylabel("Temporal summation ratio")
    ax.set_title("Temporal summation at distal sites", fontsize=9)
    ax.legend(frameon=False, fontsize=7)
    panel(ax, "E")

    # F: complete matched-site spatial summation curves.
    ax = axes[1, 2]
    n_values = [1, 2, 4, 8]
    for age in AGES:
        subset = spatial.loc[spatial.age_group == age]
        means = subset.groupby("n_synapses").summation_ratio.mean().reindex(n_values)
        sds = subset.groupby("n_synapses").summation_ratio.std().reindex(n_values).fillna(0)
        ax.errorbar(n_values, means, yerr=sds, fmt="o-", capsize=2.5,
                    lw=1.4, ms=4, color=COLORS[age], label=age)
    ax.axhline(1, color="0.45", ls="--", lw=.8)
    ax.set_xticks(n_values)
    ax.set_xlabel("Simultaneous synaptic inputs")
    ax.set_ylabel("Spatial summation ratio")
    ax.set_title("Spatial summation (exact normalisation)", fontsize=9)
    ax.legend(frameon=False, fontsize=7)
    panel(ax, "F")

    fig.tight_layout(w_pad=1.5, h_pad=2.0)
    save(fig, "Figure4_calibrated_synaptic_atlas")


def robustness_figure():
    d = pd.read_csv(DATA / "gm7/age_factor_summary.csv")
    factor_labels = {
        "weight_uS": "Synaptic weight", "process_diameter_um": "Diameter",
        "tau2_ms": r"$\tau_2$", "cm_uF_cm2": r"$C_m$",
        "rm_ohm_cm2": r"$R_m$", "tau1_ms": r"$\tau_1$", "ra_ohm_cm": r"$R_a$",
    }
    metrics = ["proximal_epsp_mV_median", "distal_epsp_mV_median",
               "distal_to_proximal_ratio_median", "temporal_ratio_max_median",
               "spatial_ratio_n8_median"]
    metric_labels = ["Proximal\nEPSP", "Distal\nEPSP", "Distal/\nproximal",
                     "Temporal\nratio", "Spatial\nratio (n=8)"]
    rows = []
    for factor in factor_labels:
        row = []
        for metric in metrics:
            deviations = []
            for age in AGES:
                baseline = d[(d.age_group == age) & d.factor.isna()][metric].iloc[0]
                q = d[(d.age_group == age) & (d.factor == factor)][metric]
                deviations.extend((100 * abs(q / baseline - 1)).tolist())
            dev = max(deviations)
            row.append(dev)
        rows.append(row)
    arr = np.array(rows)
    order = np.argsort(-arr[:, 0])
    arr = arr[order]
    names = [list(factor_labels.values())[i] for i in order]

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    im = ax.imshow(arr, cmap="YlOrRd", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(range(len(metrics)), metric_labels)
    ax.set_yticks(range(len(names)), names)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            color = "white" if arr[i, j] > 55 else "black"
            ax.text(j, i, f"{arr[i,j]:.1f}%", ha="center", va="center",
                    fontsize=8, color=color)
    cbar = fig.colorbar(im, ax=ax, pad=.025)
    cbar.set_label("Maximum cohort-median deviation from baseline (%)")
    ax.set_title("Sensitivity of calibrated-model outputs")
    fig.tight_layout()
    save(fig, "Figure5_sensitivity_robustness")


FIGURES = {
    "2": calibration_figure,
    "3": passive_figure,
    "4": synaptic_figure,
    "5": robustness_figure,
}


def main(argv=None):
    global OUT
    parser = argparse.ArgumentParser(
        description="Regenerate calibrated manuscript Figures 2-5 from validated tables."
    )
    parser.add_argument("--figure", choices=(*FIGURES, "all"), default="all")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    OUT = args.output_dir.resolve()
    style()
    selected = FIGURES if args.figure == "all" else {args.figure: FIGURES[args.figure]}
    for number, function in selected.items():
        function()
        print(f"PASS: regenerated manuscript Figure {number} in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
