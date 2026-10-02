# Pipeline execution and scientific dependencies

All user-editable paths and primary orchestration settings are centralised in `config/default.yaml`.

## Dependency chain

```text
authorised processed dataset
          │
          ├── GM0 inventory
          └── GM1–GM3 reconstruction and validation
                         │
                         ├── GM4 common-Rm morphology control
                         └── GM4.5 age-specific Rm calibration
                                      │
                                      ├── calibrated GM4 outputs → GM5
                                      ├── calibrated reconstructions → GM6
                                      └── calibrated reconstructions → GM7
```

GM4.5 does not replace GM4. GM4 is the fixed-parameter control; GM4.5 estimates the age-specific membrane resistivities subsequently used by GM5–GM7.

## Planning safely

```bash
python run_pipeline.py --dry-run --print-plan
python run_pipeline.py --dataset /path/to/MariaDATA --stages gm0 gm1_gm3 --dry-run
```

The root dry run prints every command and executes none of them. To run the configured workflow:

```bash
python run_pipeline.py --config config/default.yaml
```

The runner stops at the first failed stage and preserves completed outputs. Set `execution.limit: 3` for a pilot before a full cohort.

## Calibration and units

`R_m` is a membrane resistivity in kΩ·cm² in the calibration tables and configuration. `R_in` is the whole-cell input resistance in MΩ. They are different physical quantities and therefore are not expected to have the same numerical value or unit. For each cell and tested `R_m`, GM4 applies a known somatic current step and calculates

$$
R_{\mathrm{in},i}=\frac{\Delta V_{\mathrm{soma},i}}{I_{\mathrm{inj}}},
\qquad \frac{\mathrm{mV}}{\mathrm{nA}}=\mathrm{M}\Omega.
$$

The cohort mean modelled `R_in` is compared with the experimental age-group mean. A bracketing interpolation then finds the `R_m` at which the model curve reaches that experimental target. Thus the measured MΩ target is used to select a kΩ·cm² model parameter; there is no direct unit conversion between them.

The base sweep was 2–20 kΩ·cm² at 11 specified points. P10 was extended to 24–32 kΩ·cm² because its experimental target lay above the original bracket. The complete analysis comprised 445 cell–parameter simulations.

## Exact matched-site spatial normalisation

For selected distributed sites $s_1,\ldots,s_N$, GM6 defines

$$
S_{\mathrm{spat}}(N)=
\frac{V_N(s_1,\ldots,s_N)}
{\sum_{j=1}^{N}V_{\mathrm{single}}(s_j)}.
$$

Here, $V_N(s_1,\ldots,s_N)$ is the peak somatic EPSP evoked by simultaneous activation of those $N$ sites, and $V_{\mathrm{single}}(s_j)$ is the peak somatic EPSP produced by activating the identical site $s_j$ alone. This guarantees $S_{\mathrm{spat}}(1)=1$ and isolates deviation from linear superposition. See `stages/gm6_synaptic/SPATIAL_NORMALISATION_FIX.md`.

## GM7 interpretation

GM7 varies one factor at a time around each age group's calibrated baseline while holding the remaining factors fixed. Its five reported outputs are proximal EPSP amplitude, distal EPSP amplitude, the distal-to-proximal EPSP ratio, the maximum temporal summation ratio, and the matched-site eight-input spatial summation ratio. This tests whether the main developmental conclusions remain stable under isolated plausible parameter changes. It is not a probability model and, unless explicitly enabled, does not test simultaneous factor interactions.
