# ADR-0001: Use BioFVM for the first continuum transport benchmark

- Status: accepted for v0.1 baseline
- Date: 2026-09-30
- Issue: #1

## Context

VesicleScope needs an initial transport model before it can compare continuum and particle descriptions of EV movement.

The baseline needs:
- spatial diffusion;
- first-order loss/decay;
- donor release;
- recipient uptake;
- deterministic, headless execution;
- a path to analytical and numerical validation.

The project explicitly avoids building scientific infrastructure that a mature tool already supplies.

## Options considered

### Write a VesicleScope PDE solver

Rejected for v0.1.

It would make numerical-method implementation part of the project's validation burden before VesicleScope has established any unique scientific value. A bespoke solver may be justified later only if existing engines cannot represent a validated requirement.

### BioFVM

Selected for the first continuum benchmark.

Its published transport model directly contains diffusion, decay, sources/secretion, and uptake. It is designed as a reusable transport solver and can be isolated behind an adapter.

### CompuCell3D

Deferred.

It can solve diffusion/reaction fields and model cell behavior, but its Cellular Potts capabilities add machinery not required for the first fixed donor/recipient benchmark.

### Morpheus

Deferred.

Its declarative multiscale workflow is attractive for later tissue models, but v0.1 does not need ODE/PDE/CPM composition.

### Smoldyn

Selected as the planned particle comparison, not the first baseline.

It naturally represents discrete stochastic particles, which is valuable for testing continuum assumptions, but requires particle-specific modeling decisions that should be made only after the shared experiment/result semantics are stable.

## Decision

Implement the first engine boundary around BioFVM.

VesicleScope owns:
- scientific experiment definitions;
- units and parameter provenance;
- engine-neutral geometry/source/sink semantics;
- validation cases;
- result normalization;
- uncertainty and model-comparison logic.

BioFVM owns:
- numerical solution of the continuum transport equation.

No BioFVM-specific type may appear in the public VesicleScope domain model.

## Consequences

Positive:
- less numerical code to maintain;
- the first benchmark can focus on scientific semantics and validation;
- later engines can be compared through the same contract.

Costs:
- an adapter/build boundary is required;
- version and license metadata must be pinned;
- BioFVM's volumetric continuum representation requires an explicit thickness convention for 2D experiments;
- some future transport models may exceed BioFVM's assumptions.

## Licensing/citation boundary

The BioFVM publication reports Apache-2.0 licensing for BioFVM. The current PhysiCell project reports 3-Clause BSD for PhysiCell. The exact version integrated by VesicleScope must be checked and recorded before code is distributed.

Smoldyn's exact release/package terms also require explicit verification because its repository contains project-specific LGPL language and a separate GPLv3 license text.

VesicleScope will not vendor third-party simulator source code during the first adapter implementation.
