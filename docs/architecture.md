# Architecture baseline

This document defines the smallest architecture justified by the first VesicleScope research question. It intentionally avoids creating modules that do not yet have functionality.

## v0.1 scientific objective

Build a reproducible, verified continuum transport experiment that can vary donor/recipient geometry and recipient density while tracking extracellular EV exposure and recipient uptake.

The baseline is not a whole-body EV simulator and not a general cell biology platform.

## Boundary decisions

### Scientific engine

BioFVM is the selected first continuum transport engine.

VesicleScope should integrate it through a narrow headless runner/adapter rather than duplicating its diffusion solver. Full PhysiCell behavior is deferred until a requirement needs cell mechanics, migration, cycling or other cell-state machinery.

### Headless first

A complete experiment must run without a dashboard or notebook.

Visualization consumes stored result data. It must not contain model equations, parameter interpretation or simulation state transitions.

### Initial conceptual components

Only create these components when implementation begins:

- **experiment contract** — model/geometry references, parameter values, provenance references, duration, sampling, solver settings and seed where applicable;
- **engine adapter** — translates the experiment contract into BioFVM configuration/runtime calls;
- **result contract** — field samples, cell exposure/uptake observables and reproducibility metadata;
- **validation** — analytical/reference benchmarks, conservation checks and resolution/timestep studies;
- **analysis** — derived metrics such as exposure over distance and cumulative uptake;
- **figures** — reproducible plots generated solely from stored results.

There is no justification yet for microservices, a database, message queue, distributed scheduler, GPU layer or web frontend.

## Canonical units

The first executable transport contract now fixes the v0.1 transport units to match the reviewed BioFVM/PhysiCell convention:

- length: `micron`;
- time: `min`;
- diffusion coefficient: `micron^2/min`;
- first-order rate: `1/min`.

Spatial and temporal dimensions remain explicit. The current boundary validates these unit strings and performs no implicit conversion. A different unit must be converted deliberately by a future unit-aware boundary before numerical execution.

Concentration units remain parameter-specific until an EV-specific amount/concentration model is defined; they must still be explicit on the corresponding `ScientificParameter`.

No conversion may occur implicitly in analysis or visualization.

## Parameter provenance contract

Every biologically meaningful parameter record must be able to carry:

- stable parameter identifier;
- scientific name;
- value, interval or distribution;
- unit;
- evidence category;
- DOI/PMID/source URL and source location when practical;
- species;
- tissue;
- cell type/cell line;
- EV preparation/fraction context;
- measurement method;
- experimental conditions;
- date reviewed;
- transformation/conversion applied;
- assumptions;
- applicability limitations.

Minimum evidence categories:

- measured in target context;
- measured in related context;
- literature estimate;
- fitted;
- inferred;
- assumed;
- synthetic benchmark.

A simulated result is not a parameter evidence category.

## Experiment reproducibility contract

A run must eventually preserve at least:

- experiment/schema version;
- model/engine identity and version;
- VesicleScope commit SHA;
- geometry and initial conditions;
- parameter set and provenance snapshot;
- boundary conditions;
- solver and solver settings;
- simulation duration;
- timestep;
- output sampling;
- requested observables;
- random seed where stochastic behavior exists;
- software/dependency versions.

MIASE is the conceptual minimum-information reference. SED-ML/COMBINE should be reused where they represent the experiment naturally; VesicleScope-specific fields should be introduced only for genuine gaps.

## v0.1 observables

Do not define a single universal "communication range" metric yet.

Store enough primary output to derive and compare candidate metrics:

- extracellular field over space/time;
- recipient-cell local exposure history;
- cumulative recipient uptake when the model supports it;
- radial/distance-binned exposure;
- total extracellular quantity for mass-balance checks.

Any threshold-based range metric must record the threshold and its origin.

## Validation ladder

### 1. Mathematical verification

Start with synthetic cases whose expected behavior is known:

- zero source → zero exposure;
- diffusion of a known initial condition where an analytical/reference solution is available;
- diffusion plus decay benchmark;
- zero uptake → zero cellular uptake;
- source/sink mass accounting where applicable.

### 2. Numerical verification

Check:

- timestep refinement;
- spatial-resolution refinement;
- boundary-condition behavior;
- solver tolerance/settings where exposed;
- mass balance within documented numerical tolerance.

### 3. Adapter verification

Check:

- unit conversion;
- parameter mapping;
- geometry mapping;
- engine-version capture;
- output parsing;
- deterministic repeatability.

### 4. Biological validation

Only after the above layers are stable, select a documented experimental context and compare model trends/observables against data without tuning solely for visual agreement.

## Data flow

```text
experiment definition
        |
        v
validation + provenance checks
        |
        v
BioFVM adapter / headless runner
        |
        v
raw result + run metadata
        |
        +--> validation metrics
        |
        +--> analysis observables
        |
        +--> reproducible figures
```

## Failure behavior

A run must fail clearly rather than silently continue when:

- a required unit is missing or incompatible;
- a biologically presented parameter has no provenance category;
- an evidence-backed parameter lacks a source;
- a synthetic value is mislabeled as measured/literature-derived;
- the experiment requests an unsupported mechanism;
- the engine version cannot be recorded;
- a stochastic run omits a required seed.

The first Python transport contract now enforces geometry, timing, transport-unit, provenance and non-negativity checks. A serialized experiment schema remains deferred until a reproducible runner needs one.

## Deferred work

The following are intentionally outside v0.1:

- ECM binding;
- interstitial flow/advection;
- heterogeneous EV subpopulations;
- cargo and phenotype response;
- receptor-level uptake;
- 3D tissue;
- particle/discrete simulation;
- parameter calibration;
- sensitivity/uncertainty suites beyond what the first research question requires;
- interactive viewer;
- remote execution infrastructure.

Deferral is not rejection. Each item needs its own scientific question and evidence review before implementation.
