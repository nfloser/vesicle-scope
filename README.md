# VesicleScope

VesicleScope is an evidence-grounded computational research platform for studying extracellular-vesicle (EV) transport and cell-to-cell communication.

The project is starting deliberately with a narrow question rather than a large simulator:

> How do recipient-cell density, donor-recipient distance, EV release, extracellular transport and recipient uptake interact to determine the spatial communication range predicted by a tissue-scale EV transport model?

The first milestone is research and architecture, not feature implementation. Before a biological mechanism or parameter enters the software it must have explicit provenance, context and limitations.

## Status

**Research baseline established; first executable verification contracts in progress.**

There is not yet a validated EV simulator in this repository. Any screenshots, benchmarks or numerical results added later must state whether they are analytical, synthetic, fitted, experimentally measured or simulated.

See:

- [research landscape](docs/research/landscape.md)
- [architecture baseline](docs/architecture.md)
- [first engine decision](docs/decisions/0001-first-engine.md)
- [parameter provenance contract](docs/parameter-provenance.md)\n- [synthetic transport benchmark](docs/transport-benchmark.md)

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
