# Parameter provenance contract

VesicleScope treats provenance as part of a scientific parameter, not as an optional comment attached later.

The first executable domain contract lives in `vesiclescope.domain.parameters`. It is intentionally small: it validates identity, numerical finiteness, explicit units, evidence classification and source requirements without yet attempting unit conversion, persistence or ontology work.

## Evidence categories

`ScientificParameter.evidence` must be one of:

- `measured_target_context` — measured in the biological/experimental context being modelled;
- `measured_related_context` — measured in a related but non-identical context;
- `literature_estimate` — quantitative value taken or derived from scientific literature;
- `fitted` — estimated by fitting a model to data;
- `inferred` — inferred from other observations or quantities;
- `assumed` — an explicit modelling assumption;
- `synthetic_benchmark` — a value chosen only for a mathematical/numerical verification scenario.

Measured, related-context, literature, fitted and inferred parameters require an `EvidenceSource`.

Assumed and synthetic benchmark values may be source-free because their classification is itself the important provenance statement. They must not later be relabelled as evidence-backed values merely because a simulation using them produced plausible output.

## Source information

`EvidenceSource` currently stores:

- a durable identifier, preferably a DOI, PMID or stable official source;
- an optional source location such as a table, figure or supplement.

This is intentionally not a bibliography manager. More fields should be added only when a real parameter-evidence workflow requires them.

## Biological and experimental context

`ParameterContext` can record:

- species;
- tissue;
- cell type;
- cell line;
- EV preparation/fraction context;
- measurement method;
- experimental conditions.

Context is optional at the type level because a synthetic mathematical benchmark may legitimately have no biological context.

A later evidence-backed experiment should make relevant context mandatory at a higher experiment-validation boundary rather than fabricating context for synthetic tests.

## Units

Every `ScientificParameter` requires a non-blank unit string.

The current contract does **not** parse or convert units. Unit canonicalization belongs at the numerical-engine boundary once that boundary exists. This avoids choosing a unit library or internal unit system before the BioFVM adapter has a concrete requirement.

The absence of conversion support does not permit implicit conversion: numerical code must not consume a parameter until the engine boundary can verify and canonicalize its unit.

## Immutability

The contract uses frozen dataclasses. A validated parameter cannot be mutated in place.

A changed value, evidence category or source is a new scientific input and should therefore produce a new parameter object and, eventually, a different reproducibility record.

## Example

The example below is deliberately synthetic; it is not an EV biological default.

```python
from vesiclescope.domain import EvidenceCategory, ScientificParameter

grid_spacing = ScientificParameter(
    identifier="benchmark.grid_spacing",
    scientific_name="synthetic benchmark grid spacing",
    value=10.0,
    unit="um",
    evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
    limitations=("Numerical verification fixture; not biologically parameterized.",),
)
```

## Deferred by design

This first contract does not yet implement:

- unit conversion;
- distributions or intervals;
- parameter serialization;
- DOI metadata resolution;
- controlled biological vocabularies;
- evidence-quality scoring;
- experiment-level compatibility checks between species/tissue/cell contexts.

Those features should only be added in response to concrete research workflows.
