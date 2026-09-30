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

A 2D domain is a physical slice, not a zero-thickness plane. `RectangularDomain2D` therefore carries an explicit `slice_thickness_micron`. This thickness is independent of the numerical x/y grid and must remain unchanged under spatial refinement unless the physical experiment itself changes.

This prevents a future source/sink model from changing physical release or uptake merely because BioFVM voxel volume changed with numerical resolution.

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


## Current engine boundary

The first executable engine boundary is a process adapter in `vesiclescope.engines.biofvm`.

The Python scientific contract does not import or embed BioFVM. It validates the `TransportExperiment`, constructs an explicit argument vector for a pinned native runner, and parses a small normalized result stream. This keeps BioFVM-specific build and runtime details behind the adapter while avoiding a binding framework that the current research question does not require.

The native runner currently exposes only the behavior needed for verification: a bounded 2D no-flux field with diffusion, first-order decay, a uniform initial condition, explicit numerical grid/timestep settings, at most one localized synthetic amount-per-time release source, and at most one explicit-volume synthetic uptake sink. Source and sink may now be run independently or together in the first synthetic donor-recipient experiment.

A source is represented engine-neutrally as a `PointReleaseSource` with explicit position and provenance-bearing release rate. The BioFVM adapter maps that source to `net_export_rates`, because this preserves amount-per-time semantics without introducing a saturation target that the current evidence does not justify.

An uptake sink is represented engine-neutrally as a `PointUptakeSink` with explicit position, effective physical volume, and provenance-bearing `1/min` coefficient. The BioFVM adapter maps these inputs to `Basic_Agent.uptake_rates` and `set_total_volume`, preserving the volume dependence that exists in the pinned solver rather than hiding it.

Normalized samples carry mean/min/max concentration, the extracellular integrated field quantity `∫c dV`, and cumulative internalized quantity where uptake is enabled. Both integrated quantities carry explicit derived units.

Release mass balance is checked independently of x/y mesh resolution because net export is amount-per-time. Point-sink uptake is deliberately not claimed to be spatial-resolution invariant because BioFVM's discrete sink contains `V_agent / V_voxel`.

For coupled runs the numerical operator order is source net export → uptake → diffusion/decay for each timestep. This ordering is explicit reproducibility metadata/behavior, not a biological sequence. Combined verification checks released = extracellular + internalized quantity and confirms a reproducible synthetic near-versus-far uptake difference.

Full spatial-field serialization is deferred until the first recipient-population/distance analysis requires it.
