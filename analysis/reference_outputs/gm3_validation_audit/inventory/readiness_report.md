# OPC dataset readiness report

Dataset root: `/mnt/data/opc_step2_inputs/extracted/MariaDATA/MariaDATA`

## Overall

- Total discovered cell identifiers: **41**
- Complete without warnings: **10**
- Complete with warnings: **25**
- Incomplete: **6**

## By developmental age

| Age | Total | Complete | Complete with warnings | Incomplete |
|---|---:|---:|---:|---:|
| P10 | 14 | 2 | 10 | 2 |
| P20 | 12 | 5 | 7 | 0 |
| P50 | 15 | 3 | 8 | 4 |

## Incomplete cells

| Age | Cell | Missing | Warnings |
|---|---|---|---|
| P10 | NX13_1 | basic_analysis, sholl, nearest_neighbour | — |
| P10 | NX13_3 | angles | — |
| P50 | NX80_16 | angles, nearest_neighbour | multiple_tracing_candidates:2 |
| P50 | NX80_23 | angles, nearest_neighbour | multiple_tracing_candidates:2 |
| P50 | NX89_16 | basic_analysis, sholl | no_tracing_candidate |
| P50 | NX89_23 | basic_analysis, sholl | no_tracing_candidate |

## Potential filename mismatches

- `NX13_1` (P10), missing `basic_analysis`; same-animal candidate(s): NX13_3.
- `NX13_1` (P10), missing `sholl`; same-animal candidate(s): NX13_3.
- `NX13_1` (P10), missing `nearest_neighbour`; same-animal candidate(s): NX13_3.
- `NX13_3` (P10), missing `angles`; same-animal candidate(s): NX13_1.
- `NX80_16` (P50), missing `angles`; same-animal candidate(s): NX89_16.
- `NX80_16` (P50), missing `nearest_neighbour`; same-animal candidate(s): NX89_16.
- `NX80_23` (P50), missing `angles`; same-animal candidate(s): NX89_23.
- `NX80_23` (P50), missing `nearest_neighbour`; same-animal candidate(s): NX89_23.
- `NX89_16` (P50), missing `basic_analysis`; same-animal candidate(s): NX80_16.
- `NX89_16` (P50), missing `sholl`; same-animal candidate(s): NX80_16.
- `NX89_23` (P50), missing `basic_analysis`; same-animal candidate(s): NX80_23.
- `NX89_23` (P50), missing `sholl`; same-animal candidate(s): NX80_23.

## Notes

- Neurolucida `.DAT` tracings are treated as provenance candidates, not required inputs.
- Multiple tracing candidates are expected when an animal contributed more than one recorded cell.
- The software never silently merges biologically ambiguous identifiers.
