# Product readiness

This document tracks the gap between the verified research core and a finished VesicleScope product.

## Product surfaces already available

- evidence/provenance-aware scientific parameter contracts;
- verified BioFVM transport adapter and pinned upstream identity;
- finite donor and finite recipient geometries;
- release, diffusion, decay and uptake pathways used in reviewed synthetic verification;
- normalized spatial fields and recipient uptake time series;
- deterministic run bundles with exact VesicleScope revision and payload digest;
- engine-independent analyses and reproducible SVG figures;
- controlled multi-condition diffusion × uptake workflow;
- installable Python package and headless `vesiclescope` CLI.

## Remaining product gaps

The installable CLI is a product milestone, not the finished product.

### User-defined experiments

A deterministic external experiment document is available for export, validation and inspection, and supported documents can now be executed directly through the installed CLI with explicit numerical settings. The remaining gap is a user-facing interactive editor rather than file editing.

### Run inspection and comparison

Completed run bundles can be verified, inspected and compared at their normalized final endpoints without rerunning the solver. A verified bundle can also regenerate a deterministic offline SVG containing its final spatial field, normalized extracellular/internalized time series, units, engine/numerical settings and exact VesicleScope revision. Richer multi-run spatial/time-series comparison remains later analysis work rather than a blocker for single-run reproducibility.

### Native engine installation

The installed CLI can report engine readiness, fetch/verify the exact reviewed PhysiCell checkout and compile the packaged canonical BioFVM transport runner. Linux and Windows paths use platform-appropriate cache/output naming and are continuously verified with GNU-compatible C++/OpenMP toolchains. Prebuilt binary distribution and macOS validation remain later packaging work rather than blockers for the first Linux/Windows research release.

### Interactive product surface

A local browser-based workspace is now implemented on top of the same experiment documents, run bundles and execution/comparison services as the CLI. It is loopback-only by default, confines artifacts to explicit workspace directories and can create/import experiments, launch runs, inspect stored spatial/time-series outputs, compare runs and download persisted JSON artifacts.

Remaining work is product hardening and usability validation rather than inventing a second scientific path: broader end-to-end browser coverage, cross-platform native-engine validation, and later scientific capabilities that require their own research gates.

### Uncertainty and calibration

Uncertainty propagation and parameter inference remain future scientific capabilities. They require a separate research gate and, for calibration, suitable measured data. Synthetic inputs may verify generic mechanics but cannot establish biological validity.

### External biological validation

The Colombo 2025 target documents the first external validation context and its blockers. A finished research product can ship with clearly documented validation limits, but biological claims cannot be upgraded until suitable data and experimental context are available.

### Alternate model classes

Continuum-versus-particle comparison remains a research objective, not a current product capability. Adding Smoldyn or another engine requires a separate evidence/architecture decision and equivalent experiment semantics.

## Release gate

A production-quality VesicleScope release requires all dataset-independent product capabilities selected for that release to be:

1. integrated through one scientific contract;
2. installable through a documented route;
3. exercised end to end;
4. covered by appropriate unit/integration/regression tests;
5. reproducible from persisted inputs and outputs;
6. documented for users and contributors;
7. explicit about scientific limitations;
8. free of known critical defects or placeholder behavior.

External data-dependent validation may remain a documented blocker for stronger biological claims; it is not a reason to leave generic product mechanics unfinished.
