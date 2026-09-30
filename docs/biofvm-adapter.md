# BioFVM transport adapter

Issues: #8, #11, #13, #15, #17, #19, #21

The first VesicleScope engine adapter is deliberately a small process boundary rather than a Python binding layer.

`TransportExperiment` remains the engine-neutral scientific contract. `vesiclescope.engines.biofvm` translates that validated contract into arguments for a pinned native BioFVM runner and normalizes the runner output back into immutable Python result objects.

## Why a process boundary

The v0.1 transport work does not require a custom Python/C++ binding framework.

A subprocess boundary provides:

- a headless execution path;
- explicit, inspectable inputs;
- no arbitrary shell interpolation;
- independent native build/test failure;
- a narrow place to validate engine identity;
- no new runtime dependency.

The adapter invokes the executable with an argument vector and never with `shell=True`.

## Pinned engine identity

The reviewed engine metadata has one repository source of truth:

`vesiclescope/engines/physicell.env`

It records:

- PhysiCell release `1.14.2`;
- PhysiCell commit `dbd3499250141b27600e91e501c54c46f68f2763`;
- BioFVM version `1.1.7`.

The source-fetch script consumes the same file, verifies the Git commit, and verifies the BioFVM version string found in the pinned upstream source before the native build proceeds.

The native runner embeds that reviewed identity at build time. The Python result parser rejects output whose engine metadata differs from the repository pin.

License and citation information remain in [THIRD_PARTY.md](../THIRD_PARTY.md).

## Supported transport contract

The adapter currently accepts only the existing v0.1 contract:

- rectangular 2D domain with explicit physical slice thickness;
- `no_flux` boundary;
- diffusion in `micron^2/min`;
- first-order decay in `1/min`;
- explicit initial-concentration unit;
- duration and output interval in minutes;
- zero or one localized synthetic release source in `particle_equivalent/min`;
- zero or more localized synthetic uptake sinks with explicit effective volume in `micron^3` and uptake coefficient in `1/min`.

The current adapter supports at most one localized release source and any number of point uptake sinks that map to distinct numerical x/y voxels. Recipient sinks may run independently or together with the source.

There is no implicit unit conversion. Localized release additionally requires concentration unit `particle_equivalent/micron^3` so amount and concentration semantics stay explicit.

The numerical configuration is separate from physical geometry and biological/model parameters:

- x/y grid spacing in micron;
- numerical timestep in min.

The physical slice thickness comes from `RectangularDomain2D.slice_thickness_micron`. The native runner creates one z layer with that declared thickness, while x/y grid spacing may be refined independently.

Grid spacing must tile both x/y domain dimensions exactly. It does not need to divide the physical slice thickness. The timestep must tile both the total duration and output-sampling interval exactly. This prevents silent rounding of the requested experiment.

Keeping z thickness independent from x/y resolution is a prerequisite for future release/uptake work because BioFVM source/sink coupling uses voxel volume. Numerical refinement must not silently change the represented physical volume.

## Native runner

The runner:

1. constructs a BioFVM microenvironment with one z layer at the declared physical slice thickness;
2. explicitly sets spatial units to `micron` and time units to `min`;
3. maps diffusion and decay from the experiment contract;
4. initializes a spatially uniform field;
5. uses the pinned BioFVM 2D constant-coefficient LOD solver;
6. samples the field at every requested output time and at the final time;
7. optionally applies one BioFVM net-export source agent;
8. optionally applies indexed explicit-volume BioFVM uptake agents and tracks each agent's internalized substrate separately;
9. returns mean/min/max concentration summaries, aggregate and per-recipient internalized quantities, one complete sampled 2D concentration field per requested output time, and exact engine metadata.

The runner links BioFVM's transport core plus `Basic_Agent` and the minimal `Agent_Container` required for net-export source semantics. MultiCellDS, PhysiCell cell behaviours, XML configuration and other unused framework components are not part of this executable.

## Result contract

`BioFVMRunResult` contains:

- experiment identifier;
- concentration unit from the source experiment;
- exact engine metadata;
- one validated `BioFVMGrid2D` descriptor;
- ordered `TransportSample` records;
- one ordered `SpatialFieldSnapshot2D` for every summary sample;
- one identifier-stable `RecipientUptakeSeries` for every configured uptake sink.

Each sample contains:

- time;
- mean concentration;
- minimum concentration;
- maximum concentration;
- integrated field quantity `∫c dV`, calculated from mean concentration and the explicit physical domain volume;
- cumulative internalized field quantity reported by the configured uptake agent.

`BioFVMRunResult.integrated_quantity_unit` and `internalized_quantity_unit` record the derived units. For `particle_equivalent/micron^3`, the integrated quantity unit is `particle_equivalent`; for other synthetic concentration units it remains a concentration-volume quantity rather than being mislabeled as a biological amount.

The integrated field quantity is especially important for source/sink verification. Because the domain carries a physical slice thickness, it is not tied to the x/y mesh spacing.

Each spatial field snapshot contains the extracellular concentration value for every x/y voxel at the same sample time. Values are flattened with x changing fastest, then y, on the current single-z-layer mesh.

The parser rejects:

- missing or unknown result headers;
- missing/changed engine metadata;
- missing or duplicate grid metadata;
- malformed or non-finite samples;
- malformed, negative or incorrectly sized field snapshots;
- non-monotonic sample times;
- field times that do not match summary sample times;
- grid geometry that does not match the experiment;
- returned grid spacing that differs from the requested numerical configuration;
- field-derived mean/min/max/integrated quantity that disagrees with the summary.

The aggregate internalized value on every summary sample is cross-checked against the sum of all recipient-specific uptake series. Recipient metadata echoed by the native runner is also checked against the configured engine-neutral sink geometry, effective volume and uptake coefficient.

Two point recipients that map to the same numerical voxel are rejected before native execution because sequential same-voxel sinks would make per-recipient attribution order-dependent. The runner independently enforces the same constraint.

The full field protocol, ordering and current stdout-size limitation are documented in [spatial field result contract](spatial-field-results.md). Population-specific semantics are documented in [recipient population model baseline](research/recipient-population-model.md).

## Uniform-decay verification

For a spatially uniform initial field with no source or uptake, diffusion must preserve uniformity and first-order decay has the closed-form reference

```text
c(t) = c0 exp(-lambda t)
```

CI verifies:

- zero decay preserves the uniform field and level;
- non-zero synthetic decay agrees with the analytical solution at every requested sample within 0.5% relative error;
- reducing timestep reduces final analytical error;
- changing spatial resolution does not change the uniform solution within the asserted numerical tolerance.

All values used by these tests are labelled synthetic verification inputs. They are not EV diffusivity, clearance or concentration estimates.

## Localized-release verification

The source-capable runner links BioFVM's `Basic_Agent` and minimal `Agent_Container` implementation only for this executable. A single synthetic `PointReleaseSource` is mapped to BioFVM `net_export_rates`.

With zero initial concentration, zero decay, no uptake and no-flux boundaries, CI checks:

```text
integrated field quantity(t) = release rate * t
```

at every requested sample.

The same experiment is run at two x/y grid spacings with fixed physical slice thickness. Integrated amount must remain unchanged under refinement.

The adapter currently rejects more than one source. That is an intentional capability boundary, not a claim that biological systems have only one donor.

Scientific rationale and evidence limits are documented in [localized release model baseline](research/localized-release-model.md).

## Localized-uptake verification

A synthetic `PointUptakeSink` maps to a separate BioFVM `Basic_Agent`. Both the effective agent volume and the `1/min` uptake coefficient are explicit experiment inputs.

For zero source, zero extracellular decay and zero diffusion, CI verifies BioFVM's pinned implicit update directly:

```text
rho[n+1] = rho[n] / (1 + dt * (V_agent / V_voxel) * U)
```

BioFVM internalized-substrate tracking is enabled only for uptake runs. At every sampled time CI also verifies:

```text
extracellular integrated quantity + internalized quantity
= initial integrated quantity
```

The internalized quantity must remain non-negative and non-decreasing. A timestep-refinement check confirms convergence toward the corresponding continuous local first-order limit.

The point-sink kinetics are **not** asserted to be spatial-resolution invariant. Because the pinned BioFVM discretization contains `V_agent / V_voxel`, changing x/y mesh resolution changes local point-sink kinetics. A finite recipient geometry is required before a stronger spatial-refinement claim would be justified.

Scientific rationale and evidence limits are documented in [recipient uptake model baseline](research/recipient-uptake-model.md).

## Combined donor-recipient verification

Issue #17 combines the already verified source and sink primitives without changing their parameter semantics.

For every numerical timestep, the native runner applies:

```text
source net export -> recipient uptake -> diffusion / extracellular decay
```

This ordering is an operator-splitting choice of the numerical runner, not a biological timing claim.

With zero initial amount, zero extracellular decay and no-flux boundaries, CI verifies at every sample:

```text
extracellular integrated quantity + internalized quantity
= cumulative released quantity
```

The benchmark also runs two otherwise identical synthetic scenarios that differ only in donor-recipient separation. The selected verification regime requires the nearer recipient to internalize more by the final sample than the farther recipient. Repeated identical runs must reproduce the same normalized quantities within numerical tolerance.

These checks establish numerical coupling and distance sensitivity only. They are not calibrated to measured EV communication distances.

Scientific motivation, published distance observations and limitations are documented in [donor-recipient distance model baseline](research/donor-recipient-distance-model.md).

## Recipient-population verification

Issue #21 extends the already verified explicit-volume point sink from one recipient to multiple independently identified recipients without changing BioFVM uptake kinetics.

CI uses two identical sinks in mirror-symmetric voxels around one donor. It verifies:

```text
uptake_left(t) ~= uptake_right(t)
```

at every requested sample while aggregate internalized quantity equals the recipient sum and global extracellular + internalized accounting remains closed.

Recipient identifiers stay in the engine-neutral experiment. The native protocol uses deterministic indices and Python restores the configured identifiers after validating index-specific geometry and uptake parameters.

See [recipient population model baseline](research/recipient-population-model.md).

## Result protocol

The result stream is versioned instead of being silently extended:

- v1 introduced transport summary samples;
- v2 added cumulative internalized quantity;
- v3 adds explicit 2D grid metadata and one complete extracellular field snapshot per sample;
- v4 adds indexed recipient metadata and one cumulative uptake value per recipient and sample.

The current runner/parser require `VESICLESCOPE_BIOFVM_RESULT\t4`.

## What this validates

Passing this integration suite demonstrates that the current VesicleScope contract is mapped consistently into the pinned BioFVM solver for the tested transport, synthetic localized-release, synthetic explicit-volume uptake, and combined donor-recipient cases, and that normalized summaries, 2D spatial fields, and engine metadata are mutually consistent and reproducible.

It does **not** validate:

- a biological EV decay rate;
- a biological EV secretion rate or biological uptake coefficient;
- biologically validated donor/recipient geometry;
- a biological communication range;
- ECM interaction or flow;
- any species, tissue, cell type, cell line or EV preparation.

Those mechanisms require their own research/evidence gate before implementation.
