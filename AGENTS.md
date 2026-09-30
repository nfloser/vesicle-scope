# AGENTS.md

## Purpose

VesicleScope is research software. Changes must be judged on scientific traceability as well as software correctness.

The project follows:

```text
Issue -> Branch -> Research/Test -> Implementation -> Validation -> Documentation -> PR -> CI -> Review -> Fixes -> Merge
```

Do not work directly on `main` except for unavoidable repository bootstrap operations.

## Before changing scientific behavior

1. Read the relevant issue, architecture decision records, experiment contracts, and evidence registry.
2. Search current primary literature, consensus guidance, and official tool documentation.
3. Check whether an established simulator, standard, or library already solves the problem.
4. Record the evidence and licensing/citation implications before introducing the behavior.
5. Define the validation method before implementation.

No biological default parameter may be introduced merely because a simulator requires one.

## Evidence classes

Every biologically meaningful value or claim used by the software must be identifiable as one of:

- `observed`: measured in the experiment/dataset being modeled;
- `literature`: taken from an external source with scope and citation;
- `fitted`: estimated from declared data by a declared method;
- `assumed`: intentionally chosen for an exploratory scenario and clearly labeled;
- `synthetic`: generated for software tests or demonstrations and never presented as biological evidence.

Unknown values stay unknown until the experiment explicitly supplies or derives them.

## Units and dimensional safety

Canonical units for the first transport benchmark are:

- length: micrometre (`um`);
- time: minute (`min`);
- diffusion coefficient: `um^2/min`;
- first-order decay / uptake rate: `1/min`;
- discrete EV amount: particle-equivalent count;
- continuum concentration: particle-equivalents per `um^3`;
- cell release rate: particle-equivalents per cell per minute.

A two-dimensional simulation is treated as a slice with an explicit physical thickness when concentration-to-count conversion is needed. Never hide a thickness assumption inside an adapter.

## Engine policy

Use adapters around external engines. Do not let third-party engine types leak into the domain model.

The initial continuum benchmark targets BioFVM because its transport model directly covers diffusion, decay, secretion, and uptake. Smoldyn is the planned particle-based comparison engine. CompuCell3D and Morpheus remain evaluated options for later cell-shape and multiscale behavior.

Pin engine versions for reproducible experiments and retain citation/license metadata alongside results.

## Testing and validation

Tests are necessary but not sufficient.

For scientific code, validation should include the strongest applicable combination of:

- dimensional checks;
- analytical or semi-analytical reference solutions;
- invariants such as mass conservation;
- limiting cases;
- grid/time-step refinement;
- deterministic regression tests;
- stochastic replicate checks with declared seeds;
- cross-engine comparison where two model classes claim to represent the same regime.

A passing test suite does not justify a biological claim.

## Implementation style

Keep changes small and purpose-driven. Prefer the simplest design that supports the current research question.

Avoid:
- speculative frameworks;
- placeholder abstractions for hypothetical future engines;
- hidden fallbacks;
- hard-coded biological defaults;
- UI-first architecture;
- duplicated functionality already available in a maintained scientific tool.

Commit messages, issue text, PR descriptions, and review comments should describe the actual work naturally instead of repeating generic templates.

## Pull requests

A PR should explain:

- what scientific or engineering question it addresses;
- what evidence or source material changed the decision;
- what was implemented;
- how it was validated;
- assumptions and limitations;
- relevant dependency licenses/citations;
- remaining risks.

Link the issue with `Closes #...` only when the PR fully satisfies its acceptance criteria.
