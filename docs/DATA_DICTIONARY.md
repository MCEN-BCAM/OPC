# Data dictionary and provenance

The pipeline consumes processed Neurolucida analyses organised by age group (`P10`, `P20`, `P50`). Required file families are BasicAnalyses, Sholl, Angles, and standard nearest-neighbour workbooks. Raw `.DAT` tracings and `_NN_2_5.xlsx` files are recorded when present but are not required by GM0 readiness rules.

Canonical cell identifiers have the form `animal_tracing_age`, for example `NX5_9_P10`. Age is taken from the directory structure and is never inferred from a filename alone. Ambiguous or incomplete associations are reported rather than silently repaired.

The repository intentionally excludes raw and processed experimental workbooks. Before public release, document the data-access route, ethics/provenance statement where applicable, and the exact archival version used for the paper.
