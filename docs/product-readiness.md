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

## v0.1.0 release assessment

The dataset-independent v0.1.0 product surface is now complete enough for a first Linux/Windows research release, subject to green release-candidate CI from the built wheel.

The remaining items below are either usability/packaging follow-ups or scientific extensions that require their own evidence/data gates; they are not hidden placeholders in the released execution path.

### User-defined experiments

A deterministic external experiment document is available for export, validation and inspection, and supported documents can be executed directly through the installed CLI with explicit numerical settings. The local workspace now also provides a provenance-safe interactive editor for fully synthetic benchmarks: edits create a new immutable experiment, preserve units/geometry/synthetic evidence, and refuse evidence-backed parameters rather than silently carrying old provenance onto new values.

### Run inspection and comparison

Completed run bundles can be verified, inspected and compared at their normalized final endpoints without rerunning the solver. A verified bundle can also regenerate a deterministic offline SVG containing its final spatial field, normalized extracellular/internalized time series, units, engine/numerical settings and exact VesicleScope revision. Richer multi-run spatial/time-series comparison remains later analysis work rather than a blocker for single-run reproducibility.

### Native engine installation

The installed CLI can report engine readiness, fetch/verify the exact reviewed PhysiCell checkout and compile the packaged canonical BioFVM transport runner. Linux and Windows paths use platform-appropriate cache/output naming and are continuously verified with GNU-compatible C++/OpenMP toolchains. Prebuilt binary distribution and macOS validation remain later packaging work rather than blockers for the first Linux/Windows research release.

### Interactive product surface

A local browser-based workspace is now implemented on top of the same experiment documents, run bundles and execution/comparison services as the CLI. It is loopback-only by default, confines artifacts to explicit workspace directories and can create/import experiments, launch runs, inspect stored spatial/time-series outputs, compare runs and download persisted JSON artifacts.

The loopback HTTP product path is exercised end to end in native-engine CI: a fresh workspace creates the reviewed baseline through the HTTP API, and the v0.2 path also derives a new synthetic variant through the same provenance-safe domain boundary, executes it with explicit numerics, persists the deterministic run bundle, reopens normalized spatial/time-series output and downloads the validated artifact. Remaining work is primarily broader browser usability validation, macOS/prebuilt-engine packaging, richer multi-run analysis and later scientific capabilities that require their own research gates.

### Uncertainty and calibration

The 0.2 development line now includes the first engine-independent uncertainty-propagation boundary: an explicit ordered ensemble of stored run bundles can be summarized at final extracellular/internalized endpoints without rerunning BioFVM or inventing parameter distributions. It reports descriptive statistics and, only for sufficiently large supplied ensembles, a clearly labelled empirical percentile interval that is not presented as a confidence interval.

Users can also execute an explicit ordered set of validated experiment documents as one deterministic batch. Every member remains a normal run bundle, while the completed batch manifest preserves input order, experiment identity, numerics, revision and bundle digest. This connects user-supplied finite designs to the stored-run ensemble analysis without introducing a sampler or hidden parameter mutation.

Random sampling, evidence-backed parameter distributions, formal sensitivity indices and parameter inference remain separate scientific capabilities. They require their own research gate; calibration additionally requires suitable measured data. Synthetic inputs may verify generic mechanics but cannot establish biological validity.

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


## Final dataset-independent gap audit for v0.1.0

The release candidate is expected to satisfy the current release gate as follows:

- **one scientific contract:** CLI, browser workspace and stored-run tools reuse the same experiment and run-bundle models;
- **installable route:** standard Python wheel plus automated pinned BioFVM source/build path;
- **end-to-end execution:** external experiment and local HTTP workspace paths execute the real pinned native runner in CI;
- **tests:** unit, analytical, native integration, figure, Linux product, Windows product and HTTP end-to-end coverage are active;
- **reproducibility:** exact VesicleScope revision, engine identity, numerics, parameter provenance and deterministic artifact digests are persisted;
- **offline inspection:** completed runs can be validated, inspected, compared and rendered without solver reruns;
- **documentation:** first-run, engine setup, experiment format, execution, stored-run analysis, research assumptions and release limitations are documented;
- **scientific claims:** synthetic/numerical verification is explicitly separated from external biological validation;
- **release artifact:** CI builds a 0.1.0 wheel, installs it into a clean environment and verifies CLI, UI asset, native runner source and experiment-document workflow.

No known critical dataset-independent v0.1.0 product gap remains if that release-candidate CI passes.

The following are intentionally outside the v0.1.0 release claim:

- external biological validation beyond currently available/public context;
- measured-data calibration and uncertainty inference;
- particle/continuum model comparison;
- macOS validation and prebuilt native-engine binaries;
- medical, diagnostic or clinical use.
