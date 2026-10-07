# Executable phenotype-specific perturbation transport

Status: implementation boundary for issue #99  
Reviewed: 2026-10-07

## Scope

VesicleScope can now execute more than one independently transported EV
population while preserving the evidence model introduced by the hormone/EV
perturbation contract.

The execution path is deliberately narrower than the evidence contract:

```text
PerturbationStudy
      |
      +-- qualitative / marker / cargo evidence --------> annotation only
      |
      +-- explicit ModelEffectMapping
                    |
                    v
          validated transport mapping
                    |
                    v
         phenotype-specific experiment
                    |
                    v
        existing BioFVM single-population path
```

No hormone name, concentration, measured assay value or qualitative direction is
converted into a numerical response curve automatically.

## What can alter transport

The current execution layer accepts only explicit mappings to:

| Model target | Executed quantity | Target identifier |
| --- | --- | --- |
| `release_rate` | one named donor release rate | required release-source ID |
| `uptake_rate` | one named recipient uptake rate | required uptake-sink ID |
| `decay_rate` | the population-wide first-order decay rate | must be absent |

Operations are validated as follows:

- `multiply` requires a dimensionless `fold` mapping value;
- `add` requires the exact same unit as the target parameter;
- `set` requires the exact same unit as the target parameter;
- the effective value must remain finite and non-negative;
- the numerical change must agree with the declared increase/decrease/no-change
  direction;
- a deterministic mapping is rejected when the evidence direction is
  `mixed` or `unknown`;
- release, uptake and clearance effects must map to release, uptake and decay
  respectively;
- two effects may not silently update the same transport parameter in one
  population.

The effective `ScientificParameter` retains the baseline parameter provenance
and adds a limitation describing the explicit transformation. The population
run additionally stores a complete effect-execution audit with mapping
identifier, evidence category/source, operation, baseline value, effective
value and unit.

## What is deliberately not executed

The following stay visible but do not alter BioFVM transport:

- an effect with no `ModelEffectMapping`;
- an effect without a phenotype assignment;
- a mapped phenotype fraction;
- mapped cargo abundance;
- marker identity or marker abundance by itself;
- a measured particle count, marker signal or cargo assay value;
- any inferred cortisol/adrenaline/norepinephrine response curve that was not
  explicitly supplied and provenance-labelled.

An unassigned effect is not broadcast to every EV phenotype. An unsupported
mapping is not treated as zero. Both are represented as `not_executed` with a
reason.

This distinction is important for the current hormone evidence. For example,
the evidence baseline may say that a response increased in a particular source
context without providing a defensible human-blood fold change. VesicleScope
preserves that observation without inventing the missing magnitude.

## Independent EV populations

`PopulationTransportSpec` assigns one baseline `TransportExperiment` to one
declared `EVPhenotype`.

`resolve_perturbation_transport` produces, for each population:

- the unchanged baseline experiment;
- the effective experiment after valid explicit mappings;
- the effect-execution audit.

`run_population_transport` then executes each effective experiment through the
existing verified BioFVM adapter.

This is an **equivalently verified composition strategy**, not a new coupled
native multi-substrate solver. Each EV population is treated as an independent
transported quantity. Population-population reactions, phenotype conversion,
shared receptor competition and cargo-mediated state changes are not modeled.

The strategy is valid only for the declared independent-population scope.
Introducing coupling requires a new scientific mechanism, tests and numerical
verification.

## Aggregate behavior

Per-population results remain authoritative and are never discarded.

When all population results have identical:

- engine identity;
- spatial grid;
- sample times;
- field snapshot times;
- concentration unit;
- integrated-quantity unit;
- internalized-quantity unit;

VesicleScope can derive a total EV field by pointwise summation and total
integrated/internalized quantities by summing the corresponding population
samples.

Incompatible population results fail instead of being resampled or converted.

## Persistence

The deterministic
`vesiclescope.population-simulation-run` version 1 bundle stores:

- the complete integrity-protected perturbation study;
- globally unexecuted effects;
- one record per EV phenotype containing:
  - phenotype ID;
  - original baseline experiment;
  - effect-execution audit;
  - the existing `vesiclescope.simulation-run` v1 child bundle for the
    effective experiment.

The child bundle therefore preserves every population's extracellular fields,
integrated quantities, recipient uptake series, numerical settings, engine
identity and VesicleScope revision.

The existing single-population run-bundle schema is unchanged.

## Longitudinal measured-data comparison

`compare_measurements_to_prediction` is an explicit validation adapter between
`LongitudinalEVDataset` and a normalized simulation result.

A caller must explicitly select:

- a measured condition ID;
- a measured observation identifier;
- the model observable to compare:
  - mean concentration;
  - integrated extracellular quantity; or
  - internalized quantity.

The adapter uses only exact stored simulation times. If a measured point occurs
between stored simulation samples, the prediction is reported as missing and no
interpolation is performed.

The measured and predicted value can always be shown side-by-side. A numerical
residual is emitted only when their unit strings are already identical.
VesicleScope performs no hidden unit conversion and no fitting in this adapter.

Most real blood/plasma assay outputs will therefore still need an explicit,
reviewed observation model before direct numerical residuals are scientifically
meaningful.

## Numerical verification

The two-population synthetic native benchmark uses two independent release
populations with zero decay and zero uptake.

It checks:

1. total extracellular plus internalized quantity equals the analytically known
   cumulative release at each sampled time;
2. the final integrated total is invariant between a coarser grid/timestep and
   a refined grid/timestep within the existing mass-balance tolerance.

Each child population is still executed by the existing single-population
runner, so the benchmark verifies the composition layer without changing the
single-population numerical implementation.

## Current scientific boundary

Simulated now:

- independent phenotype-specific extracellular transport;
- explicit evidence-bearing release-rate mappings;
- explicit evidence-bearing uptake-rate mappings;
- explicit evidence-bearing decay/clearance mappings;
- per-population fields, uptake and integrated quantities;
- total fields/quantities derived from compatible independent populations;
- exact-time model-versus-measurement alignment.

Annotated but not mechanistically simulated:

- marker-state changes;
- cargo abundance changes;
- phenotype fractions;
- hormone receptor signaling;
- dynamic stimulus-response kinetics;
- phenotype transitions;
- interactions among EV populations;
- assay-to-model calibration without an explicit adapter.

This boundary is intentionally strict. It lets the workspace later visualize
cortisol/adrenaline/stress conditions, markers, measured time points and
population-specific model predictions without presenting unsupported biology as
a solved mechanism.
