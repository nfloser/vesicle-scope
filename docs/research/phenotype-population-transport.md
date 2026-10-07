# Phenotype-specific EV population transport

Status: executable composition baseline for issue #99  
Reviewed: 2026-10-07

## Question

How can VesicleScope simulate several marker/cargo-defined EV populations without
breaking the already verified single-population BioFVM path or pretending that
the populations interact when no interaction mechanism has been justified?

## Composition decision

The first executable multi-population model treats EV phenotypes as independent
transport populations. Each population owns a complete existing
`TransportExperiment` and therefore has its own:

- diffusion coefficient;
- decay/clearance coefficient;
- initial concentration;
- release source/rate;
- recipient uptake configuration;
- provenance-bearing parameters.

All populations share the same physical domain, duration, sampling interval,
boundary condition and concentration unit.

Each population is executed through the existing pinned BioFVM adapter. The
results are composed only after simulation.

For linear, non-interacting transport this is mathematically equivalent to
representing the populations as independent BioFVM substrates in one
microenvironment. It has an important engineering advantage: the reviewed
single-substrate native protocol and all existing v0.3 run bundles remain
unchanged.

This equivalence stops being valid as soon as one population changes another
population's production, transport, conversion or uptake. Such cross-population
reactions require a separate model decision and native verification.

## Result semantics

The primary result remains population-specific:

```text
population / phenotype
    +-- extracellular field over time
    +-- integrated extracellular quantity
    +-- recipient uptake series
    +-- exact transport parameters
```

A total-EV field may be derived by voxel-wise summation only when the population
results share the same grid, sample times and concentration unit. The individual
population fields are retained and are never replaced by the sum.

This is the data needed for the requested workspace behavior: marker-defined
populations can be toggled independently while a total-EV view remains
available.

## Perturbation execution

The evidence layer introduced by issue #98 deliberately does not change solver
parameters by itself.

`apply_model_effects` executes only an explicit `ModelEffectMapping`.
The first supported numerical mappings are multiplicative changes to:

- release rate;
- uptake rate;
- decay/clearance rate.

The mapping must use unit `fold`. Release and uptake mappings must name the
exact source/sink they modify. The effect must also reference exactly one
simulated phenotype.

Direction and magnitude are cross-checked:

- increase requires factor > 1;
- decrease requires 0 <= factor < 1;
- no-change requires factor = 1;
- mixed/unknown directions cannot be represented by one scalar factor.

Marker abundance, cargo abundance and phenotype-fraction effects are preserved
as evidence but are not yet converted into transport changes. No hidden
interpolation or guessed response curve is introduced.

Every applied mapping produces an audit record containing the base value,
mapping value, effective value, target and population. The effective
`ScientificParameter` is labelled as a derived/inferred or synthetic input
according to the mapping evidence; the original source parameter remains
unchanged.

## Persistence

`vesiclescope.population_run_bundles` stores one deterministic top-level
population run bundle. Each population embeds a complete existing
`SimulationRunBundle`, so all existing checks remain active for:

- experiment parameter provenance;
- exact VesicleScope revision;
- BioFVM identity;
- numerical settings;
- spatial grid;
- extracellular fields;
- uptake series;
- payload integrity.

The top-level bundle adds only population and phenotype identity plus the
composition experiment identity.

## Numerical verification

The synthetic two-population benchmark uses two independent release populations
with rates 120 and 40 particle-equivalent/min under zero decay and no-flux
boundaries.

For each population:

```text
M_i(t) = q_i * t
```

For the summed field:

```text
M_total(t) = (q_1 + q_2) * t
```

The native integration test evaluates both timestep refinement and x/y grid
refinement. Aggregate amount must remain unchanged while each population keeps
its own stored field.

This verifies the independent composition strategy. It is not evidence that
real marker-defined EV populations share the synthetic rates or transport
parameters.

## Current limitation

The new layer makes heterogeneous EV populations executable, but does not yet
claim:

- biological parameterization of CD9/CD63/CD81-defined populations;
- hormone-specific human blood response curves;
- interconversion between EV phenotypes;
- competition for receptors or shared uptake capacity;
- cargo-dependent transport physics;
- downstream cellular phenotype response.

Those mechanisms require evidence and explicit model contracts rather than UI
assumptions.
