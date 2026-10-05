# Changelog

## Unreleased

- add explicit stored-run ensemble summaries for conservative uncertainty propagation without hidden biological distributions.

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
