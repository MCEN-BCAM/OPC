# Dataset guide

## Included source data

The repository includes the authorised collaborator-supplied morphology dataset under `data/source/MariaDATA/`. The model begins with processed Neurolucida exports rather than raw microscopy images.

The principal input families are:

- `NLResults/BasicAnalyses`: cell, process, segment, node, terminal, and soma measurements;
- `NLResults/Sholl`: intersections and cable length by radial shell;
- `NLResults/NearestNeighbour`: branch-point spacing at the available scales;
- `NLResults/Angles`: segment orientation and branching-angle measurements;
- `NLTracings`: tracing provenance and geometry candidates;
- `MorphologyStats` and `MorphologyPlots`: original experimental statistics and plotting provenance.

GM0 discovers 41 cell identifiers. Thirty-five contain the required analysis families and form the validated cohort used throughout the manuscript: 12 P10, 12 P20, and 11 P50 cells. Six incomplete identifiers are retained in the public source tree and explicitly reported in `data/inventory/readiness_report.md`, but are not propagated into the simulations.

## Derived and figure-level data

`data/derived/gm3_validated/cells.zip` is the validated 35-cell reconstruction archive used directly by the Figure 1 notebook. It contains the accepted per-cell measurements, reconstructed geometry, and validation products.

The compact calibrated outputs required by Figures 2–5 are under `analysis/reference_outputs/calibrated/`:

- GM4.5 sweep and interpolation tables for Figure 2;
- GM5 accepted-cell passive metrics for Figure 3;
- GM6 cell metrics, all 420 displayed protocol rows, and representative traces for Figure 4;
- GM7 age/factor sensitivity summaries for Figure 5.

The experimental input-resistance means and SEM values used as GM4.5 targets are recorded explicitly in `stages/gm45_calibration/config/calibration_config.json`.

## GitHub compatibility

No tracked file exceeds GitHub's 100 MB limit. The original 193 MB Igor Pro workspace is included losslessly as `Morphology_Graphs_New.pxp.gz`; decompress it only if that historical plotting workspace is required. It is not a computational input to the Python pipeline.

See `data/DATA_TERMS.md` for the current permission statement and the outstanding choice of a formal data-reuse licence.
