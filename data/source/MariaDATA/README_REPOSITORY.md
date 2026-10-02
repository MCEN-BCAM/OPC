# Source-data note

This directory preserves the collaborator-supplied `MariaDATA` hierarchy used by GM0–GM3. File and folder names have been retained because the discovery code uses them to identify cell, age, and analysis family.

The only storage transformation is lossless gzip compression of `MorphologyPlots/Morphology_Graphs_New.pxp`, required because the original 193 MB file exceeds GitHub's per-file limit. The Python modelling pipeline uses `NLResults` and tracing provenance; it does not require the Igor Pro plotting workspace.

The SHA-256 checksum of both the original file and the decompressed `.pxp.gz`
content is:

```text
a83b1ebe5cd966a98b29ccb8c3b37e242aef07e8409478a5c80329ef93eb16a7
```

See `data/inventory/readiness_report.md` for cohort inclusion and `docs/DATASET.md` for the relationship between source data, validated reconstructions, simulations, and figures.
