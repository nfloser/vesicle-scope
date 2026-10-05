# VesicleScope

VesicleScope is an evidence-grounded computational research platform for studying extracellular-vesicle (EV) transport and cell-to-cell communication.

VesicleScope was developed deliberately around a narrow research question rather than as an unconstrained large simulator:

> How do recipient-cell density, donor-recipient distance, EV release, extracellular transport and recipient uptake interact to determine the spatial communication range predicted by a tissue-scale EV transport model?

Before a biological mechanism or parameter enters the software it must have explicit provenance, context and limitations. The current product keeps that research gate in the same contracts used by its CLI and local browser workspace.

## Status

**VesicleScope 0.2.0 is the current installable research-product release.** The continuum BioFVM path is numerically verified against analytical/synthetic benchmarks and includes finite donor/recipient geometry, reproducible runs, provenance-aware experiment files, a provenance-safe synthetic editor, explicit experiment batches, conservative stored-run ensemble summaries, rich offline run comparison, a CLI and a local interactive workspace.

VesicleScope is **not yet externally biologically validated as a predictive EV model**. Current reviewed numerical examples are synthetic unless explicitly labelled otherwise. Results must continue to distinguish analytical references, synthetic benchmarks, simulations, fitted values and experimental measurements.

See:

- [research landscape](docs/research/landscape.md)
- [architecture baseline](docs/architecture.md)
- [product readiness](docs/product-readiness.md)
- [deterministic simulation run bundles](docs/run-bundles.md)
- [external experiment documents](docs/experiment-files.md)
- [external experiment execution and run inspection](docs/external-execution.md)
- [explicit experiment batches](docs/experiment-batches.md)
- [offline stored-run analysis](docs/stored-run-analysis.md)
- [interactive synthetic experiment editor](docs/synthetic-experiment-editor.md)
- [first engine decision](docs/decisions/0001-first-engine.md)
- [parameter provenance contract](docs/parameter-provenance.md)
- [synthetic transport benchmark](docs/transport-benchmark.md)
- [BioFVM transport adapter](docs/biofvm-adapter.md)
- [BioFVM engine setup](docs/engine-setup.md)
- [BioFVM diffusion verification](docs/research/biofvm-diffusion-benchmark.md)
- [localized release model baseline](docs/research/localized-release-model.md)
- [finite circular donor footprint](docs/research/finite-donor-footprint.md)
- [donor-boundary radial profile](docs/research/donor-boundary-radial-profile.md)
- [synthetic donor-boundary profile figure](docs/research/synthetic-donor-boundary-figure.md)
- [synthetic diffusion × uptake factor experiment](docs/research/diffusion-uptake-factor-experiment.md)
- [explicit stored-run uncertainty ensembles](docs/research/uncertainty-ensemble.md)
- [recipient uptake model baseline](docs/research/recipient-uptake-model.md)
- [finite circular recipient footprint](docs/research/finite-recipient-footprint.md)
- [recipient population model baseline](docs/research/recipient-population-model.md)
- [recipient count and planar-density analysis](docs/research/recipient-density-analysis.md)
- [finite recipient count and planar-density sweep](docs/research/finite-recipient-count-sweep.md)
- [first reproducible synthetic population figure](docs/research/synthetic-population-figure.md)
- [donor-recipient distance model baseline](docs/research/donor-recipient-distance-model.md)
- [Colombo 2025 tumour-distance validation target](docs/research/colombo-2025-validation-target.md)
- [spatial field result contract](docs/spatial-field-results.md)
- [third-party software record](THIRD_PARTY.md)

## Scientific principles

VesicleScope is designed around a few non-negotiable rules:

- use current EV terminology and reporting guidance, including MISEV2023;
- never silently turn an assumption into a biological constant;
- carry units and evidence provenance with scientifically meaningful parameters;
- make simulation experiments reproducible from model, configuration, solver settings, seed and software version;
- validate numerics before interpreting biology;
- quantify uncertainty rather than hiding it;
- compare model classes when the model choice can change the biological conclusion;
- reuse established scientific software instead of rebuilding solvers without a measured reason.

## v0.1 scope

Version 0.1 provides a verified continuum transport baseline in a bounded 2D tissue-scale domain with:

- explicit physical slice thickness independent from numerical x/y resolution;
- donor and recipient cells;
- EV release represented as a model source term;
- diffusion;
- optional decay/clearance only when its parameterization is supported;
- recipient uptake represented by an explicitly documented model;
- spatial and temporal outputs;
- parameter provenance;
- analytical and numerical verification;
- reproducible headless execution;
- basic scientific figures generated from stored results.

No cargo-mediated phenotype effects, receptor-level biology, ECM binding, interstitial flow, 3D tissue or particle model will be added merely for realism. Those mechanisms are later research questions.

## Generate the synthetic population figure

The first figure is deliberately a **synthetic fixed-grid verification**, not experimental evidence. It now uses the verified finite circular recipient scenarios: the final 8-recipient extracellular concentration field plus the controlled finite 2/4/8 recipient-count sensitivity at the reviewed 10 micron grid. Issue #33 independently confirmed the same qualitative count ordering at 5 micron resolution.

```bash
python -m pip install -r requirements-figures.txt
bash scripts/fetch-physicell.sh
make -f native/biofvm_benchmark/Makefile runner
python -m scripts.generate_population_figure \
  --runner build/native/biofvm_transport_runner \
  --output build/figures/recipient-count.svg
```

Recipient circles are rendered from each scenario's declared 15 micron footprint radius in physical x/y coordinates; the renderer does not infer geometry from voxel size or effective uptake volume.

Matplotlib is an optional visualization dependency; the numerical engine and core analysis layer do not depend on it. CI independently regenerates and validates the SVG.

## Install and first run

VesicleScope now has an installable headless interface. The scientific core has no mandatory Python runtime dependency; figure generation remains optional.

```bash
python -m pip install .
vesiclescope --version
vesiclescope examples
vesiclescope experiment export-example diffusion-uptake-baseline --output experiment.json
vesiclescope experiment validate experiment.json
vesiclescope experiment inspect experiment.json
```

To run the reviewed synthetic diffusion × uptake workflow with figures:

```bash
python -m pip install '.[figures]'
vesiclescope engine status
vesiclescope engine build --output build/native/biofvm_transport_runner

vesiclescope run diffusion-uptake-factor \
  --runner build/native/biofvm_transport_runner \
  --revision "$(git rev-parse HEAD)" \
  --output-dir build/diffusion-uptake
```

The workflow writes a deterministic summary, one SVG interaction figure and nine durable run bundles. It is a controlled synthetic model-behaviour experiment and **not experimental evidence**.

See [product readiness](docs/product-readiness.md) and [v0.2.0 release notes](docs/releases/v0.2.0.md) for the supported product boundary and remaining scientific limitations.


## Local interactive workspace

The same validated experiment documents and deterministic run bundles used by the CLI are available through a loopback-only browser workspace.

```bash
vesiclescope workspace init ./workspace
vesiclescope engine build
vesiclescope ui \
  --workspace ./workspace \
  --runner ~/.cache/vesiclescope/engines/<reviewed-commit>/biofvm_transport_runner \
  --revision "$(git rev-parse HEAD)"
```

The UI binds to `127.0.0.1` by default. It can create/import experiments, derive new provenance-safe variants from synthetic benchmarks, launch runs with explicit numerical settings, inspect stored spatial fields and time series, compare completed runs across their stored quantity series and directly compatible final fields, and download persisted JSON artifacts. Synthetic editing creates a new experiment and refuses evidence-backed parameters rather than silently reusing their provenance. It does not introduce a separate scientific execution path.

## Model-comparison direction

A long-term goal is to run equivalent scenarios through continuum and discrete/stochastic representations and identify regimes where model choice materially changes predicted exposure, uptake, arrival time or communication range.

The current research baseline identifies BioFVM as the first continuum-engine candidate and Smoldyn as a later particle-model candidate. The rationale and licensing caveats are documented before implementation.

## Reproducibility

The experiment contract will be designed with MIASE/SED-ML/COMBINE concepts in mind, without forcing standards where they do not fit the spatial multicellular model. Calibration components will evaluate PEtab before defining a custom fitting format.

## What VesicleScope does not claim

VesicleScope is research software. It is not a medical device, diagnostic system or clinical decision tool.

A simulation result should be read as:

> Under model X, parameterization Y, assumptions Z and numerical method N, the simulation predicts ...

—not as a claim that EVs universally behave that way.

## Repository policy

This repository is intentionally public, but **no open-source license is currently granted**. Source availability does not by itself grant permission to copy, modify, redistribute or create derivative works.

Third-party dependencies remain subject to their own licenses and citation requirements.

## Development

Repository-specific scientific rules are in [AGENTS.md](AGENTS.md). Human contribution guidance is in [CONTRIBUTING.md](CONTRIBUTING.md), and security reporting guidance is in [SECURITY.md](SECURITY.md).

Current work is tracked through GitHub issues and pull requests. Implementation does not proceed directly on `main`.
