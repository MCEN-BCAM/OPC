# GM7 status

**Implementation:** complete.

**Scope:** cohort-wide baseline and one-factor sensitivity screen over Rm, Ra, Cm, process diameter, synaptic conductance, rise time and decay time; optional interaction design; per-condition failure capture; cell-normalised robustness metrics; P10/P20/P50 summaries; reproducibility metadata.

**Default workload:** 36 parameter conditions per accepted cell. Each condition runs the GM6 single-site, temporal and spatial protocols.

**Validation in hosted runtime:** source syntax, package compilation and parameter-design generation checked. Real NEURON sweeps were not executed because the hosted environment does not provide the `neuron` package. Biological results must be generated locally from validated reconstruction JSON files.

**Next milestone:** GM8, manuscript-ready statistical synthesis and figure assembly from GM3–GM7 outputs.
