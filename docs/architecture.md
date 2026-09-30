# Architecture baseline

Status: accepted baseline for issue #1  
Date: 2026-09-30

## Design goal

VesicleScope separates scientific intent from simulator mechanics.

An experiment should be understandable without knowing whether BioFVM, Smoldyn, or a future engine executes it. Engines are implementation details behind adapters; provenance, units, geometry, model assumptions, and result semantics belong to VesicleScope.

## Layering

```text
CLI / future UI
      |
      v
experiment application service
      |
      +--> evidence + provenance
      |
      v
engine-neutral domain model
      |
      v
engine adapter protocol
      |
      +--> BioFVM adapter
      +--> Smoldyn adapter (later)
      +--> other engines only when justified
      |
      v
normalized result + validation metadata
      |
      +--> analysis / comparison
      +--> visualization
      +--> archival/export
```

## Planned package boundaries

### `domain`

Owns:
- quantities and unit-safe scientific values;
- geometries and regions;
- source, transport, loss, and uptake concepts;
- engine-neutral result semantics.

Must not import an engine SDK.

### `experiments`

Owns:
- parsing and validating experiment definitions;
- semantic validation beyond JSON Schema;
- experiment IDs and schema versions;
- reproducibility metadata;
- orchestration of a single run.

### `engines`

Owns:
- adapter protocol;
- engine capability declarations;
- conversion from domain types to engine inputs;
- execution;
- conversion back to normalized results.

An adapter must fail loudly when the requested experiment cannot be represented faithfully.

### `evidence`

Owns:
- evidence records;
- parameter provenance;
- source identifiers;
- evidence class;
- assumptions and transfer limitations.

### `analysis`

Owns:
- continuum-vs-particle comparison;
- uncertainty summaries;
- convergence metrics;
- derived quantities with explicit definitions.

### `visualization`

Owns render-ready transformations only. It may not recalculate scientific model state or hide missing data.

### `cli`

Owns reproducible commands such as validate/run/compare/export. It is an application boundary, not the scientific core.

## Dependency direction

Higher-level layers may depend on lower-level contracts, never the reverse.

```text
cli -> experiments -> domain
                \-> evidence
                \-> engines -> domain

analysis -> domain/result contracts
visualization -> domain/result contracts
```

Third-party engine dependencies remain inside their adapters.

## v0.1 model semantics

The continuum benchmark represents one EV-equivalent concentration field (c(x,y,t)) over a two-dimensional slice with explicit physical thickness (h) whenever conversion between concentration and count is needed.

The conceptual transport equation is:

```text
dc/dt = D * laplacian(c) - lambda * c + source - uptake
```

where:
- `D` is a declared diffusion coefficient;
- `lambda` is a declared first-order loss rate;
- `source` is donor release mapped into the field;
- `uptake` is an effective recipient sink.

This equation defines the shared semantics, not a mandate to implement a custom solver.

### Explicit simplifications

v0.1 does not model:
- EV biogenesis subclasses;
- EV size distributions;
- deformability;
- ECM binding or anomalous diffusion;
- active transport/advection;
- receptor kinetics;
- endocytosis pathway choice;
- endosomal trafficking;
- cargo release;
- downstream phenotype;
- donor/recipient cell motion or morphology changes.

Those are possible later hypotheses, not hidden features of the baseline.

## Canonical units

The domain contract uses:
- `um` for length;
- `min` for time;
- `um^2/min` for diffusion;
- `1/min` for first-order rates;
- `particle_equivalent` for discrete amount;
- `particle_equivalent/um^3` for continuum concentration;
- `particle_equivalent/(cell*min)` for per-cell release.

Adapters may convert to engine-native units internally but must return canonical units and record the conversion.

## Provenance contract

Every result bundle must eventually contain:
- VesicleScope version/commit;
- experiment schema version;
- normalized experiment definition;
- engine name and exact version;
- adapter version;
- random seed if stochastic;
- evidence IDs referenced by biological parameters;
- execution timestamp;
- checksums for external model/config artifacts;
- validation status;
- warnings for assumptions or unsupported optional metadata.

A result with missing required provenance is invalid for scientific comparison.

## Failure policy

The software must prefer an explicit failure over an implicit scientific assumption.

Examples:
- missing diffusion coefficient -> validation error;
- incompatible unit -> validation error;
- unsupported boundary condition -> adapter capability error;
- absent evidence ID for a literature parameter -> validation error;
- engine executable not found -> execution error;
- stochastic run without seed -> validation error.

There is no "best guess" fallback for scientific inputs.
