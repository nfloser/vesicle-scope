# VesicleScope

VesicleScope is an evidence-grounded computational research platform for studying extracellular-vesicle (EV) transport and cell-to-cell communication.

The project is starting deliberately with a narrow question rather than a large simulator:

> How do recipient-cell density, donor-recipient distance, EV release, extracellular transport and recipient uptake interact to determine the spatial communication range predicted by a tissue-scale EV transport model?

The first milestone is research and architecture, not feature implementation. Before a biological mechanism or parameter enters the software it must have explicit provenance, context and limitations.

## Status

**Research baseline established; the synthetic transport/uptake/geometry pipeline includes verified finite donor and recipient footprints, engine-independent donor-boundary analysis, reproducible scientific figures, deterministic durable run bundles, and an external tumour-distance validation target with explicit readiness blockers.**

There is not yet a validated EV simulator in this repository. Any screenshots, benchmarks or numerical results added later must state whether they are analytical, synthetic, fitted, experimentally measured or simulated.

See:

- [research landscape](docs/research/landscape.md)
- [architecture baseline](docs/architecture.md)
- [product readiness](docs/product-readiness.md)
- [deterministic simulation run bundles](docs/run-bundles.md)
- [external experiment documents](docs/experiment-files.md)
- [external experiment execution and run inspection](docs/external-execution.md)
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

## Planned v0.1

The first implementation milestone is a verified continuum transport baseline in a bounded 2D tissue-scale domain with:

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

See [product readiness](docs/product-readiness.md) for the remaining work between this headless milestone and a finished interactive research product.

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

Repository-specific development and scientific rules are in [AGENTS.md](AGENTS.md).

Current work is tracked through GitHub issues and pull requests. Implementation does not proceed directly on `main`.
