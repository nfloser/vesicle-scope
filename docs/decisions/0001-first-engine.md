# ADR 0001 — Use BioFVM for the first continuum transport baseline

**Status:** Accepted for v0.1 baseline  
**Date:** 2026-09-30  
**Issue:** #1

## Context

The first VesicleScope experiment needs a bounded 2D extracellular field, donor sources, recipient sinks and time-resolved spatial output.

Writing a bespoke PDE solver would provide control but would also make VesicleScope responsible for numerical methods, stability, boundary behavior and performance already handled by established scientific software.

The alternatives reviewed are BioFVM/PhysiCell, CompuCell3D, Morpheus, Smoldyn and a small custom SciPy implementation.

The upstream PhysiCell/BioFVM tree inspected for this decision reported PhysiCell version **1.14.2**. This records the reviewed baseline; the implementation must still pin an exact release or commit and capture it in run metadata.

## Decision

Use **BioFVM** as the first continuum transport engine and place it behind a narrow headless VesicleScope adapter/runner.

Do not adopt the complete PhysiCell behavioral stack until a real requirement needs its additional cell behaviors or mechanics.

Do not add Smoldyn to v0.1. Preserve it as the leading candidate for a later discrete/stochastic model-comparison experiment after the continuum baseline is verified.

## Why BioFVM

BioFVM already implements the core capability required by the first milestone:

- spatial diffusion/decay fields;
- source/sink coupling through agents;
- Cartesian spatial meshes;
- 2D problem support within the current codebase;
- established scientific publication/citation;
- use within the actively maintained PhysiCell ecosystem;
- permissive BSD 3-Clause licensing in the current PhysiCell/BioFVM source.

This allows VesicleScope to spend effort on evidence, model semantics, provenance, validation and comparison rather than reimplementing a numerical transport solver.

## Why not the alternatives now

### Full PhysiCell

Useful when cell mechanics, motility, phenotype, cycling or dynamic multicellular behavior becomes part of the research question. Those capabilities are not required for the first fixed donor/recipient transport baseline.

### CompuCell3D

Strong for Cellular Potts/tissue models with dynamic cell shapes and PDE coupling. That is a larger modeling assumption and software surface than v0.1 requires.

### Morpheus

Strong multiscale environment with ODE/PDE/CPM integration and model-oriented tooling. For v0.1, a small headless adapter around the transport solver gives VesicleScope tighter control over experiment/result/provenance contracts without introducing a GUI/model-language-centered workflow.

### Smoldyn

Excellent fit for particle-based stochastic transport, but that is intentionally the later independent comparison representation rather than the first continuum model.

The current upstream license presentation also needs version-specific verification before adoption: the current GitHub source contains GPL-3.0 text while some historical/manual material describes LGPL distribution.

### Custom SciPy solver

Potentially valuable as an independent reference calculation for verification, but not justified as the production engine while BioFVM satisfies the transport requirement.

## Consequences

### Positive

- no bespoke production PDE solver;
- smaller initial scientific surface;
- existing solver publication and community;
- straightforward path to later PhysiCell capabilities if needed;
- adapter boundary keeps VesicleScope experiment/result contracts independent of the engine.

### Costs

- a C++ scientific dependency enters the project;
- build/version capture must be reproducible;
- the adapter must map units and source/sink semantics explicitly;
- BioFVM numerical behavior still requires verification for the exact VesicleScope benchmark;
- choosing an established solver does not validate the biological model.

## Validation required before biological interpretation

The first implementation issue must include:

1. a diffusion benchmark with known analytical/reference behavior;
2. a diffusion-plus-decay benchmark;
3. zero-source and zero-uptake regression cases;
4. mass-balance checks;
5. spatial- and timestep-refinement checks;
6. explicit unit-mapping tests;
7. capture of BioFVM/PhysiCell version and VesicleScope commit SHA.

Only after these pass should a biologically parameterized EV scenario be interpreted.

## Revisit triggers

Revisit this ADR if:

- required boundary conditions cannot be represented correctly;
- a validated benchmark exposes unacceptable numerical behavior;
- the first biological question requires cell/tissue mechanics outside BioFVM's intended role;
- integration/licensing constraints become disproportionate;
- model-comparison work requires a common contract the adapter cannot support cleanly.
