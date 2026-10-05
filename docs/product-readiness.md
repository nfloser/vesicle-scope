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

Users still need a stable, validated external experiment/project format rather than only reviewed built-in scenarios. It must preserve parameter provenance and reject unsupported or ambiguous scientific inputs.

### Run inspection and comparison

A user should be able to open existing run bundles, inspect provenance and solver metadata, compare completed runs and regenerate supported analyses/figures without rerunning the solver.

### Native engine installation

The pinned BioFVM runner currently has a reproducible repository build path, but installation/distribution of the native dependency is not yet a polished end-user workflow.

### Interactive product surface

The scientific core is intentionally headless. A finished product still needs an interactive workflow that lets users define/load experiments, launch runs, inspect spatial fields/time series, compare results and export artifacts without editing Python.

This surface must consume the same contracts and workflows as the CLI rather than duplicating model logic.

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
