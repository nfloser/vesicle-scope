# AGENTS.md

## Purpose

VesicleScope is research software for studying extracellular-vesicle-mediated cell-to-cell communication. Scientific correctness, traceability and reproducibility take priority over feature count.

## Workflow

Work through a coherent issue and branch. Do not develop directly on `main`.

For scientifically meaningful work use:

issue → research/evidence review → failing test or benchmark where applicable → implementation → mathematical/numerical validation → documentation → pull request → CI → independent review → corrections → merge.

Do not split one coherent change into artificial issue or pull-request spam.

## Scientific gate

Before changing a biological mechanism, equation, terminology, default parameter, range, distribution or interpretation:

1. inspect current primary literature and relevant consensus guidance;
2. inspect existing computational models and maintained research software;
3. record the evidence and context in `docs/research/`;
4. distinguish measured, literature-derived, fitted, inferred, assumed, synthetic and simulated quantities;
5. only then implement the smallest justified change.

Do not invent plausible-looking biological defaults.

Use extracellular vesicle (EV) as the default term. Use biogenesis-specific terms such as exosome only when the source supports that classification.

## Engineering rules

- Prefer established scientific software over custom solvers or renderers.
- Follow YAGNI. Complexity must be earned by a research requirement.
- Keep the scientific core headless; visualization is a client of reproducible result data.
- Avoid abstractions until at least two real use cases require them.
- Units are part of the model contract. Conversions must be explicit and tested.
- Seeds, solver settings, software versions and source evidence must be captured for reproducible runs.
- Never make core CI depend on live network resources.
- Treat external datasets, software licenses and scientific citations as separate obligations.
- Do not copy code, data or figures without verifying redistribution rights.

## Validation expectations

Tests alone do not establish scientific validity.

When applicable verify:

- analytical behavior;
- mass balance and boundary behavior;
- timestep and spatial-resolution convergence;
- unit and parameter mapping;
- seed propagation;
- output parsing and experiment reproducibility;
- agreement or documented disagreement with relevant experimental evidence.

For stochastic behavior test invariants or distributions unless a deterministic seed makes an exact trajectory meaningful.

## Repository history

Branch names, commits, issues and pull requests should be concise and specific to the work. Avoid generic AI-like boilerplate and empty Conventional Commit prefixes.

Examples:

- `research-architecture-baseline`
- `Verify diffusion baseline against analytical solution`
- `Record evidence behind recipient uptake model`

## Public repository and licensing

The repository is intentionally public. No open-source license is granted by default. Do not add or change a project license without owner approval.

Third-party dependencies retain their own licenses. Record versions, licenses, citations and redistribution implications before adoption.

## Claims

VesicleScope is not a medical device and simulated results are not biological truth.

Scientific output should be framed as a prediction conditional on a model, parameterization, assumptions and numerical method. Do not generalize across species, tissues, cell lines, EV preparations or experimental methods without evidence.
