# Changelog

## Unreleased

- package one VesicleScope experiment plus optional validated run bundles in a deterministic COMBINE/OMEX archive;
- inspect OMEX projects without solver execution while reusing experiment/run integrity and scientific contracts;
- import and export COMBINE/OMEX projects through the local browser workspace without a separate scientific path;
- explicitly defer SED-ML compatibility until the spatial BioFVM experiment has an honestly portable model/execution representation.


## 0.2.0

Completes the current dataset-independent Linux/Windows VesicleScope research-product scope.

### Product

- add a provenance-safe interactive editor for deriving new immutable variants from fully synthetic benchmark experiments;
- execute explicit ordered experiment batches and persist a deterministic member manifest consumable by ensemble analysis;
- add explicit stored-run ensemble summaries for conservative uncertainty propagation without hidden biological distributions or confidence-interval claims;
- compare completed run bundles across their recorded extracellular/internalized time series without interpolation;
- subtract directly compatible final spatial fields as right minus left, with explicit incompatibility reasons instead of silent resampling;
- export deterministic full run-comparison JSON with source-bundle payload digests and exact revisions;
- expose the richer stored-run comparison through the loopback browser workspace.

### Reproducibility and quality

- retain the complete Linux/Windows package, native BioFVM, figure and HTTP/native end-to-end CI matrix;
- add installed-wheel dependency consistency checks;
- syntax-check the packaged inline browser client in CI;
- add contributor and security-reporting policies for the public research repository;
- publish v0.1.0 from its immutable historical release boundary before finalizing 0.2.0.

### Scientific limits

Version 0.2.0 remains a research tool whose reviewed examples are numerical/synthetic unless explicitly documented otherwise. Empirical ensemble summaries are not confidence intervals, numerical run comparisons are not biological rankings, and stronger external validation/calibration remains gated on suitable experimental data and context.

## 0.1.0

First installable VesicleScope research-product release.

### Product

- installable Python package with the `vesiclescope` CLI;
- deterministic external experiment documents with validation and inspection;
- execution of supported experiment files through the pinned BioFVM path;
- deterministic run bundles with integrity digest and exact VesicleScope revision;
- offline run inspection, comparison and SVG regeneration;
- loopback-only interactive workspace for experiment import/creation, execution, run inspection and download;
- automated pinned BioFVM setup on verified Linux and Windows product paths.

### Scientific and numerical core

- explicit provenance-aware scientific parameters and units;
- verified diffusion/decay transport baseline;
- finite circular donor release geometry;
- finite circular recipient uptake geometry;
- normalized spatial fields and identifier-stable uptake time series;
- recipient population, donor-distance and donor-boundary analyses;
- controlled synthetic diffusion × uptake interaction experiment;
- reproducible scientific SVG figures.

### Reproducibility and quality

- analytical and native BioFVM verification;
- mass-accounting checks;
- spatial/timestep refinement checks where applicable;
- deterministic artifact serialization;
- end-to-end HTTP workspace regression using the real native runner;
- Linux and Windows CI product paths;
- explicit scientific-status labels separating synthetic simulation from experimental evidence.

### Scientific limitations

Version 0.1.0 is a research tool, not a biologically validated universal EV predictor. The first external Colombo 2025 validation context still has documented data/calibration blockers. Uncertainty propagation, measured-data calibration and continuum-versus-particle model comparison remain separate research milestones.
