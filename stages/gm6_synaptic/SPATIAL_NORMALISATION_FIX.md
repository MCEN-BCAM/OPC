# GM6 spatial-normalisation correction

## Problem

The original spatial denominator approximated each distributed site's isolated EPSP using the nearest one of the three representative proximal/intermediate/distal responses. Since these were not necessarily the exact sites activated in the spatial protocol, the one-input ratio could exceed one.

## Correction

For every candidate site used by the spatial protocol, GM6 now performs a matched isolated stimulation and caches its somatic EPSP. For selected sites \(s_1,\ldots,s_N\), the corrected ratio is

\[
S_{\mathrm{spat}}(N)=
\frac{V_{\mathrm{simultaneous}}(s_1,\ldots,s_N)}
{\sum_{m=1}^{N}V_{\mathrm{single}}(s_m)}.
\]

The \(N=1\) numerator reuses that exact isolated response, so \(S_{\mathrm{spat}}(1)=1\) by construction.

## Output additions

Spatial rows now include:

- `linear_prediction_mV`
- `component_segment_ids`
- `component_single_epsps_mV`

Cell summaries additionally include:

- `max_spatial_summation_ratio_n_gt_1`
- `spatial_summation_ratio_n8`

The legacy `max_spatial_summation_ratio` is retained for compatibility, but it normally equals one because the \(N=1\) condition is included.
