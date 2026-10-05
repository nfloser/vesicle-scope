# Contributing to VesicleScope

VesicleScope is scientific research software. Correctness, provenance, reproducibility and honest scientific claims take priority over feature count.

This repository is public but does **not** currently grant an open-source license. Do not assume that public source availability grants permission to redistribute the project or derivative works. Third-party software and data keep their own license and citation requirements.

## Before starting work

For a non-trivial bug, feature, refactor or research change:

1. check existing issues and pull requests;
2. open or select one coherent issue;
3. create a branch from the current `main`;
4. read `AGENTS.md` and the relevant architecture/research documentation;
5. keep the scope narrow enough to review and validate independently.

Do not develop directly on `main`.

## Scientific research gate

Before changing any biological mechanism, equation, terminology, default parameter, range, distribution or interpretation:

1. inspect current primary literature and relevant consensus guidance;
2. inspect established computational models/software where applicable;
3. record evidence and context under `docs/research/`;
4. distinguish measured, literature-derived, fitted, inferred, assumed, synthetic and simulated quantities;
5. implement only the smallest change justified by that evidence.

Do not invent plausible-looking EV parameters. Use **extracellular vesicle (EV)** by default and use biogenesis-specific terms only when the evidence supports them.

A synthetic benchmark is a numerical verification input, not experimental evidence.

## Development workflow

Use the repository workflow:

`issue → research/test → implementation → validation → documentation → PR → CI → independent review → corrections → merge`

Prefer tests before implementation when the behavior is testable. Bugs should normally be reproduced by a failing regression test first.

Keep commits small and specific. Avoid generic commit/PR boilerplate.

## Local checks

The scientific Python core intentionally has no mandatory runtime dependencies.

At minimum for Python-only changes run:

```bash
python -m pip install .
python -m compileall -q vesiclescope
python -m unittest discover -s tests -v
python -m pip check
```

For packaging changes also build and install the wheel in a clean environment.

Changes touching the BioFVM adapter, native engine, experiment execution or end-to-end workspace path must run the applicable native tests. The canonical CI workflow documents the exact pinned PhysiCell/BioFVM build and verification commands.

Figure changes require the optional reviewed renderer:

```bash
python -m pip install '.[figures]'
```

Do not replace scientific validation with snapshot tests. Where relevant check analytical behavior, mass balance, units, boundary behavior, resolution/timestep sensitivity and persisted reproducibility.

## User interface changes

The local browser workspace must remain a client of the same experiment/run contracts used by the CLI. Do not add a demo-only scientific path.

Keep the server loopback-only by default, preserve workspace path confinement and Host validation, and keep scientific-status/limitation text visible.

The inline browser client is syntax-checked in CI; backend product behavior is exercised through the real loopback HTTP/native-engine end-to-end tests.

## Documentation and claims

Update documentation with code when behavior changes.

Every user-visible scientific output must make clear whether values are synthetic, simulated, fitted, inferred or experimentally measured. Do not describe model output as biological truth or use clinical/therapeutic language without an explicit, reviewed evidence basis.

VesicleScope is not a medical device, diagnostic system or clinical decision tool.

## Pull requests

A pull request should explain:

- the problem or research question;
- the solution and important design decisions;
- tests and scientific/numerical validation performed;
- provenance/licensing implications where relevant;
- limitations, risks and known follow-up work;
- the issue it resolves.

Merge only after the relevant acceptance criteria and CI are green and an independent review has found no blocking issue.
