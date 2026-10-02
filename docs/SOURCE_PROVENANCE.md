# Source provenance

This consolidated repository was assembled from the latest validated project packages rather than from an older GitHub snapshot.

| Module | Authoritative package used |
|---|---|
| GM0 | `1-opc_milestone0_dataset_inventory` |
| GM1–GM3 | `2-opc_inventory_driven_pipeline` |
| GM3 validation evidence | `3-opc_step3_validation` |
| GM4 | `4-opc_step4_cohort_passive` |
| GM4.5 | extended calibration package and validated 445-simulation outputs |
| GM5 | calibrated passive-atlas package and validated outputs |
| GM6 | calibrated synaptic-atlas package with the matched-site spatial-normalisation correction |
| GM7 | calibrated sensitivity/robustness package and validated outputs |
| Report | V12 calibrated report with five main figures and the supplementary morphology-only control |
| Experimental dataset | collaborator-authorised `MariaDATA` source tree (41 discovered records; 35-cell validated cohort) |

GM1–GM3 intentionally remain a combined cumulative stage because that was the validated implementation. GM4 is retained as the common-parameter morphology control. GM4.5 and the calibrated downstream modules are separate so their scientific roles and provenance remain explicit.

`MANIFEST.sha256` records the packaged file hashes. The stage-level `SCIENTIFIC_CODE_SHA256.txt` supplied with GM1–GM3 is retained as additional evidence of scientific-code identity.

The manuscript assembly functions in `analysis/scripts/calibrated_figures.py` were recovered from the original calibrated-report build and adapted only to repository-relative paths. Figure 1 is regenerated from the packaged GM3 validated reconstructions and the collaborator-supplied BasicAnalyses data. Figure 4 uses the packaged 420-row GM6 protocol table and the three traces for the prespecified representative P20 cell. Together, the source dataset, validated reconstruction archive, and calibrated reference outputs make all five main manuscript figures regenerable from this repository.

The original 193 MB `Morphology_Graphs_New.pxp` workspace is preserved losslessly as `Morphology_Graphs_New.pxp.gz`, because GitHub rejects individual files larger than 100 MB. Its uncompressed SHA-256 checksum is recorded in `data/source/MariaDATA/README_REPOSITORY.md`.
