# Localized release model baseline

Status: synthetic verification model for issue #13  
Reviewed: 2026-09-30

## Question

How should VesicleScope represent the first localized extracellular-vesicle source without turning a context-specific secretion measurement into a universal biological constant?

## Evidence does not support one default EV release rate

The current evidence is strongly context dependent.

Colombo et al. directly imaged CD9-labelled EV exchange in cancer-cell systems and estimated roughly three labelled EV release events per minute in that specific setup. The same study also found that release per cell changed with cell density and that local internalization strongly affected observed dissemination.

- Colombo F, Nimkar K, Norton EG, Lovat F, Cocucci E. *Exploring the Spatial Limits of Extracellular Vesicles-Mediated Intercellular Communication.* Journal of Extracellular Vesicles. 2025;14:e70169. DOI: https://doi.org/10.1002/jev2.70169
- PMID: 41167986

A separate analysis estimating basal secretion from human blood-cell populations reported cell-specific rates spanning orders of magnitude, from very low erythrocyte-associated estimates to much higher monocyte-associated estimates.

- *An estimate of extracellular vesicle secretion rates of human blood cells.* PMID: 38938292. https://pubmed.ncbi.nlm.nih.gov/38938292/

These values are evidence that release can be quantified. They are not interchangeable defaults for another cell type, EV preparation, assay or tissue.

## v0.1 model decision

The first executable release model is therefore **synthetic** and deliberately narrower than a donor-cell biology model.

A `PointReleaseSource` contains:

- a stable source identifier;
- x/y position in micron;
- a provenance-bearing release-rate parameter.

The release-rate unit is:

```text
particle_equivalent/min
```

`particle_equivalent` is a model amount used for verification. It must not be presented as a directly measured count of biologically validated EVs unless a later experiment supplies appropriate evidence and measurement semantics.

A `TransportExperiment` may hold zero or more engine-neutral release sources. The current BioFVM adapter intentionally supports at most one localized source because the first benchmark needs only one. Multiple donor sources should be implemented only with a concrete experiment that requires them.

## Why constant net export

The pinned BioFVM 1.1.7 source provides two different source concepts.

Its secretion/uptake update follows the form:

```text
dp/dt = S * (T - p) - U * p
```

Using that secretion term would require a secretion rate and a saturation target `T`. VesicleScope does not yet have evidence for a biologically meaningful saturation-density model.

BioFVM also exposes `net_export_rates`. In the pinned source, net export over one timestep is converted from amount to density by:

```text
density increment = export_rate * dt / voxel_volume
```

That directly matches the first benchmark's amount-per-time semantics and avoids inventing an unsupported saturation target.

Reviewed upstream source:

- `MathCancer/PhysiCell`, commit `dbd3499250141b27600e91e501c54c46f68f2763`
- `BioFVM/BioFVM_basic_agent.cpp`
- BioFVM version 1.1.7

## Synthetic mass-balance benchmark

The first source verification uses:

- one point source;
- zero initial concentration;
- zero decay;
- no uptake;
- no-flux boundaries;
- fixed physical slice thickness.

For a constant source rate `q`, total extracellular amount must satisfy:

```text
M(t) = q * t
```

Diffusion may redistribute the field but cannot alter total amount under these conditions.

The benchmark is executed at multiple x/y grid spacings while holding the physical slice thickness constant. A correct amount-per-time source must produce the same integrated amount after refinement.

## What this does not establish

Passing this benchmark does not establish:

- a biological EV secretion rate;
- stochastic release timing;
- donor-cell surface dependence;
- density-dependent release;
- EV subtype composition;
- cargo amount;
- recipient uptake;
- downstream phenotype.

Those require separate model and evidence decisions.
