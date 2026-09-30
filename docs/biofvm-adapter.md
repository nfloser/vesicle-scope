# BioFVM transport adapter

Issue: #8

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

- rectangular 2D domain;
- `no_flux` boundary;
- diffusion in `micron^2/min`;
- first-order decay in `1/min`;
- explicit initial-concentration unit;
- duration and output interval in minutes.

There is no implicit unit conversion.

The numerical configuration is separate from biological/model parameters:

- grid spacing in micron;
- numerical timestep in min.

Grid spacing must tile both domain dimensions exactly. The timestep must tile both the total duration and output-sampling interval exactly. This prevents silent rounding of the requested experiment.

## Native runner

The runner:

1. constructs a BioFVM microenvironment;
2. explicitly sets spatial units to `micron` and time units to `min`;
3. maps diffusion and decay from the experiment contract;
4. initializes a spatially uniform field;
5. uses the pinned BioFVM 2D constant-coefficient LOD solver;
6. samples the field at every requested output time and at the final time;
7. returns mean/min/max concentration summaries plus exact engine metadata.

Only the BioFVM transport translation units required by these verification targets are linked. Unused MultiCellDS, MATLAB I/O, agent-container and XML components are not part of this executable.

## Result contract

`BioFVMRunResult` contains:

- experiment identifier;
- concentration unit from the source experiment;
- exact engine metadata;
- ordered `TransportSample` records.

Each sample contains:

- time;
- mean concentration;
- minimum concentration;
- maximum concentration.

The parser rejects:

- missing or unknown result headers;
- missing/changed engine metadata;
- malformed or non-finite samples;
- non-monotonic sample times;
- sample times that do not match the requested experiment.

This summary contract is sufficient for the current uniform-field verification. Spatial field export is intentionally deferred until the first real spatial result consumer exists.

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

## What this validates

Passing this integration suite demonstrates that the current VesicleScope contract is mapped consistently into the pinned BioFVM solver for the tested transport-only cases, and that result/metadata mapping is reproducible.

It does **not** validate:

- a biological EV decay rate;
- secretion or uptake;
- donor/recipient geometry;
- communication range;
- ECM interaction or flow;
- any species, tissue, cell type, cell line or EV preparation.

Those mechanisms require their own research/evidence gate before implementation.
