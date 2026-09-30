# Recipient uptake model baseline

Status: synthetic verification model for issue #15  
Reviewed: 2026-09-30

## Question

How should VesicleScope represent the first recipient uptake sink without turning a context-specific uptake measurement into a universal extracellular-vesicle uptake constant?

## Uptake is context dependent

Published quantitative uptake studies do not support one universal EV uptake rate or one universal kinetic law.

Bonsergent et al. quantified uptake and cytosolic cargo delivery in HeLa cells and found strong dose/time dependence, low spontaneous uptake in their experimental system, and no clear saturation across the tested high-dose range.

- Bonsergent E et al. *Quantitative characterization of extracellular vesicle uptake and content delivery within mammalian cells.* Nature Communications. 2021;12:1864. DOI: https://doi.org/10.1038/s41467-021-22126-y

Other recipient-cell systems have shown dose/time-dependent uptake with saturating behavior.

- Heusermann W et al. *Exosomes surf on filopodia to enter cells at endocytic hot spots, traffic within endosomes, and are targeted to the ER.* Journal of Cell Biology. 2016;213:173-184. DOI: https://doi.org/10.1083/jcb.201506084

Imaging-flow-cytometry work in HEK293T recipient cells likewise reports uptake as dependent on dose, time, and recipient context.

- *Kinetics and Specificity of HEK293T Extracellular Vesicle Uptake using Imaging Flow Cytometry.* PMID: 32833066.

These studies justify recipient uptake as an important mechanism to investigate. They do not justify copying one reported rate into VesicleScope as a default.

## v0.1 model decision

The first executable uptake model is therefore **synthetic** and deliberately represents only an effective sink.

A `PointUptakeSink` contains:

- a stable identifier;
- x/y position in micron;
- explicit effective physical volume in `micron^3`;
- a provenance-bearing first-order uptake coefficient in `1/min`.

The explicit volume is not optional metadata. In the pinned BioFVM 1.1.7 discretization, the uptake contribution depends on:

```text
dt * effective_agent_volume / voxel_volume * uptake_rate
```

Therefore the same numeric uptake coefficient does not have a complete numerical meaning without the effective recipient volume and current voxel volume.

No biological default is supplied for either quantity.

## Pinned BioFVM semantics

For one substrate and no secretion, BioFVM's `Basic_Agent` update reduces locally to the implicit discrete form:

```text
rho[n+1] = rho[n] / (1 + dt * (V_agent / V_voxel) * U)
```

where:

- `rho` is the extracellular concentration in the agent's current voxel;
- `V_agent` is the declared effective recipient volume;
- `V_voxel` is the numerical voxel volume;
- `U` is the declared uptake coefficient.

Reviewed upstream source:

- `MathCancer/PhysiCell`, commit `dbd3499250141b27600e91e501c54c46f68f2763`
- `BioFVM/BioFVM_basic_agent.cpp`
- BioFVM version 1.1.7

VesicleScope does not reimplement this update in the native runner. The runner configures `Basic_Agent.uptake_rates`, sets the explicit agent volume, and calls BioFVM's existing source/sink update.

## Internalized-quantity accounting

For uptake verification, BioFVM internalized-substrate tracking is enabled.

The result protocol records two distinct integrated quantities:

- extracellular `∫c dV`;
- cumulative internalized quantity reported by the uptake agent.

Both quantities carry a derived unit. For the synthetic benchmark using `particle_equivalent/micron^3`, the integrated unit is `particle_equivalent`.

With:

- zero source;
- zero extracellular decay;
- no-flux boundaries;

the verification invariant is:

```text
extracellular integrated quantity
+ internalized quantity
= initial integrated quantity
```

The internalized quantity must also remain non-negative and non-decreasing.

## Numerical verification

The first sink benchmark uses zero diffusion so the affected voxel can be checked exactly against BioFVM's own discrete update.

A separate timestep-refinement check compares the discrete result with the corresponding continuous local first-order limit. Reducing the timestep must reduce the error.

This verifies the numerical mapping. It does not make the continuous first-order law a biological claim.

## Spatial-resolution limitation

A point sink is tied to one numerical voxel. Because BioFVM scales the sink by `V_agent / V_voxel`, changing x/y grid spacing changes the local point-sink kinetics even when `V_agent` and `U` remain fixed.

VesicleScope therefore does **not** claim spatial-resolution-independent point-sink uptake.

This is different from the amount-per-time source benchmark, whose integrated release was intentionally resolution invariant.

A later biologically meaningful recipient model should represent finite recipient geometry or otherwise define how cell volume/footprint couples to the continuum mesh before spatial-refinement invariance is expected.

## What this does not establish

Passing the benchmark does not establish:

- a biological EV uptake coefficient;
- a universal recipient-cell volume;
- receptor binding;
- endocytic pathway choice;
- uptake saturation;
- endosomal trafficking;
- cargo escape;
- degradation/recycling after uptake;
- functional cargo delivery;
- downstream phenotype.

Those require separate evidence and model decisions.
