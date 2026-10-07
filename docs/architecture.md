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

Visualization consumes normalized result and analysis data. It must not contain model equations, parameter interpretation or simulation state transitions. Durable result serialization is a separate boundary: figures may still consume in-memory normalized results, while the v0.1 run-bundle layer can persist those same scientific contracts for later inspection.

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
normalized summaries + spatial field snapshots + run metadata
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

The native runner currently exposes only the behavior needed for verification: a bounded 2D no-flux field with diffusion, first-order decay, a uniform initial condition, explicit numerical grid/timestep settings, at most one localized synthetic amount-per-time release source, and multiple explicit-volume synthetic uptake sinks in distinct numerical voxels. Source and recipient populations may run independently or together.

Release sources now have two engine-neutral geometry forms.

A `PointReleaseSource` keeps the original one-voxel reference semantics. A `CircularReleaseSource` adds an explicit physical 2D donor footprint radius while retaining one aggregate provenance-bearing amount-per-time release rate. The adapter rasterizes circular donors onto voxel centers and divides the declared aggregate release rate across the selected BioFVM `Basic_Agent.net_export_rates` components. Grid refinement may change component count and local concentration shape, but not the total amount released.

The donor radius and aggregate release rate remain independent inputs; VesicleScope does not infer secretion from source area or perimeter.

Uptake recipients have two engine-neutral geometry forms.

A `PointUptakeSink` keeps the original one-voxel reference semantics. A `CircularUptakeSink` adds an explicit 2D footprint radius while keeping effective uptake volume as a separate quantity. The adapter rasterizes circular footprints onto voxel centers, divides the declared effective volume across the selected BioFVM `Basic_Agent` components, and aggregates component internalization back to one scientific recipient identifier.

Different recipients may not share native uptake voxels in the current model so per-recipient attribution cannot become update-order dependent.

Normalized results carry mean/min/max concentration summaries, the extracellular integrated field quantity `∫c dV`, aggregate cumulative internalized quantity, one explicit 2D grid descriptor, one complete extracellular concentration-field snapshot per requested sample, and identifier-stable per-recipient uptake series. Integrated quantities carry explicit derived units.

Release mass balance is checked independently of x/y mesh resolution because net export is amount-per-time. Both point and finite circular donors preserve the declared aggregate release under rasterization. Point-sink uptake remains a documented resolution-dependent reference. Finite circular recipients preserve total configured effective volume under grid refinement and are explicitly verified across multiple x/y grids before being used for stronger density studies.

For coupled runs the numerical operator order is source net export → uptake → diffusion/decay for each timestep. This ordering is explicit reproducibility metadata/behavior, not a biological sequence. Combined verification checks released = extracellular + internalized quantity and confirms a reproducible synthetic near-versus-far uptake difference.

Spatial fields are now available in the normalized in-memory result contract, so analysis and visualization no longer need BioFVM internals. The first engine-independent analysis module consumes only `TransportExperiment` plus normalized result objects to derive planar recipient density, donor distance and distance-binned uptake.

Planar recipient density is explicitly a 2D quantity in `recipient/mm^2`; it must not be presented as volumetric tissue cell density. The current controlled count sweep runs at one fixed numerical resolution because point-sink uptake retains `V_agent / V_voxel` dependence.

The first figure boundary lives in `vesiclescope.figures`. It validates normalized result/analysis inputs, reconstructs the documented x-fastest 2D field layout, and delegates rendering only to the optional pinned Matplotlib dependency. The reusable 2/4/8 count-sweep definition lives in `vesiclescope.scenarios`, so native verification and figure generation cannot silently drift onto different synthetic geometries.

The headless generator runs the pinned BioFVM adapter, derives public population summaries, and renders an SVG labelled as synthetic fixed-grid verification. Numerical/core analysis CI remains independent of Matplotlib; a dedicated figure CI job installs the optional renderer and uploads the generated SVG as an artifact.

Durable normalized-result serialization is now implemented through the deterministic VesicleScope v0.1 run bundle because validation/model-comparison workflows need completed runs independently of immediate figure generation. The format preserves experiment provenance, numerics, exact engine identity, normalized fields and recipient uptake series with a payload digest. It is MIASE-informed but deliberately does not claim SED-ML/OMEX compatibility while the spatial BioFVM model lacks a complete standard model representation. Binary storage remains deferred until measured data volume or performance justifies it.



## Blood/plasma EV measurement boundary

Longitudinal blood-derived EV measurements are a separate scientific boundary
from `TransportExperiment` and `ScientificParameter`.

`vesiclescope.domain.measurements` records sample pre-analytics,
centrifugation history, assay semantics, marker-defined observations,
replicates and explicit condition-relative time points.
`vesiclescope.measurement_files` persists those records in a deterministic,
integrity-protected document.

The separation is deliberate:

```text
measured assay observation
        |
        v
measurement dataset
        |
        v
explicit future calibration / validation adapter
        |
        v
model parameter or model-vs-data comparison
```

A particle concentration, marker fluorescence signal or marker-positive event
count must never become a transport parameter by implicit assignment. Blood
pre-analytical metadata also remain attached to the measurement rather than
being treated as solver configuration.

See [blood-derived longitudinal EV measurement workflow](research/blood-ev-longitudinal-workflow.md).

## External measured-data audit boundary

`vesiclescope.validation.mucus_data` reads only the digest-pinned external DRUM workbook via optional openpyxl. It produces provenance-bearing measurement audits for the CLI, with explicit sample nesting, species/particle identity and contextual units. It does not modify `TransportExperiment` or feed estimates into the engine. Originals and derived measurements remain outside the repository. See [local measured-data audit](measured-data.md).
