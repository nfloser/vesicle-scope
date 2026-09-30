# VesicleScope

VesicleScope is an evidence-grounded research platform for studying extracellular-vesicle (EV) transport, uptake, and cell-to-cell communication with reproducible virtual experiments.

The project is deliberately **not** a generic biology simulator. Its purpose is to make mechanistic assumptions inspectable, compare model classes, quantify uncertainty, and connect simulation outputs back to the evidence and experiment definitions that produced them.

## v0.1 research question

The first milestone asks a deliberately narrow question:

> In a controlled two-dimensional donor/recipient setup, how do EV diffusion, first-order degradation, release, and recipient uptake determine the spatial concentration field and delivered dose over time, and when does a continuum description stop agreeing with a particle-based reference?

The first verified baseline will use a continuum transport engine. A particle-based reference is deferred until the continuum benchmark, experiment contract, and validation suite are stable.

## Scientific rules

- Use **extracellular vesicle (EV)** as the default term unless a more specific biogenesis-based label is supported by evidence.
- No biological default parameter enters the code without an evidence record, source, unit, scope, and uncertainty/assumption note.
- Distinguish observed, literature-derived, fitted, assumed, and synthetic values.
- Never convert missing biological knowledge into a silent numeric default.
- Report model outputs as model outputs, not biological facts.
- Every experiment must be reproducible from machine-readable inputs, explicit units, engine/version metadata, and a deterministic seed where stochastic behavior exists.
- Prefer established scientific engines and standards over bespoke implementations when they satisfy the requirement.

The terminology and reporting stance follows MISEV2023, which emphasizes rigorous nomenclature, transparent methods, and caution in attributing function specifically to EVs.

## Planned architecture

The scientific core stays headless. User interfaces and visualizations consume experiment outputs rather than owning simulation logic.

```text
vesicle_scope/
  domain/        # typed scientific concepts and units
  experiments/   # experiment definitions and validation
  engines/       # adapters around external simulators
  evidence/      # provenance and evidence registry
  analysis/      # comparison, uncertainty and derived metrics
  visualization/ # render-ready result transformations
  cli/           # reproducible command-line workflows
```

No package skeleton is created yet: issue #1 establishes the research, engine, validation, and reproducibility contracts first.

## Reproducibility direction

VesicleScope will align with established computational-biology standards where they fit the model class:

- MIASE as a minimum-information target for simulation experiments.
- SED-ML / COMBINE archives where an engine can represent the workflow without losing semantics.
- PEtab for future parameter-estimation problems where its model/data assumptions are appropriate.
- FAIR4RS as guidance for versioning, metadata, provenance, identifiers, and reusable research outputs.

Standards are adopted because they improve reproducibility, not as box-checking requirements. Unsupported semantics must remain explicit rather than being forced into a format that changes the scientific meaning.

## Repository status and licensing

This repository is public for visibility and review, but **no open-source license is granted for VesicleScope itself at this time**. Public visibility does not grant general permission to copy, modify, redistribute, or create derivative works beyond rights provided by applicable law and platform terms.

Third-party dependencies keep their own licenses and attribution requirements. Their presence or evaluation does not relicense VesicleScope.

## Current milestone

Development starts with [issue #1](https://github.com/nfloser/vesicle-scope/issues/1): establish the research and architecture baseline before simulator code is added.

See:

- `AGENTS.md` for repository workflow and scientific gates.
- `docs/research/` for the evidence landscape.
- `docs/adr/` for architecture decisions.
- `docs/contracts/` for reproducible experiment contracts.
