# Public data included with the repository

The experimental collaborators authorised inclusion of the complete project dataset used for this modelling study. The repository therefore contains both the source morphology files and the validated/derived inputs needed to reproduce the manuscript figures.

```text
data/
├── source/MariaDATA/          collaborator-supplied morphology dataset
│   ├── NLResults/             Neurolucida quantitative exports
│   ├── NLTracings/            tracing provenance files
│   ├── MorphologyStats/       statistical project files
│   └── MorphologyPlots/       original plotting workspaces
├── derived/gm3_validated/
│   └── cells.zip              validated 35-cell GM3 cohort used by Figure 1
├── inventory/                 reproducible GM0 inventory and readiness tables
└── example_dataset/           synthetic smoke-test material
```

The original `Morphology_Graphs_New.pxp` file was 193 MB, exceeding GitHub's 100 MB per-file limit. It is included losslessly as `Morphology_Graphs_New.pxp.gz`; decompress it with `gunzip` if the Igor Pro workspace is needed. This archive is provenance material and is not read by the Python pipeline.

The inventory discovers 41 cell identifiers. Thirty-five have the required inputs and form the validated modelling cohort: P10, n=12; P20, n=12; P50, n=11. The other six records are retained transparently and listed in `inventory/readiness_report.md`; they are not silently merged or used in the cohort simulations.

The default configuration points directly to `data/source/MariaDATA`, so no manual copying or path editing is required.
