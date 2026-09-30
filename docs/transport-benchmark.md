# Synthetic transport benchmark

Issue: #5  
Status: first executable verification contract

## Purpose

This benchmark defines the smallest transport problem that VesicleScope can hand to a numerical engine without inventing biological defaults.

It is **synthetic mathematical verification**, not an EV experiment and not evidence that any particular EV population has these parameter values.

The benchmark exists so that a future BioFVM adapter can be checked against engine-neutral inputs and closed-form reference behavior before donor release, recipient uptake, or biological parameterization are introduced.

## v0.1 transport contract

`TransportExperiment` contains:

- a stable experiment identifier;
- a bounded rectangular 2D domain with explicit physical slice thickness;
- duration and output sampling interval in minutes;
- an explicit boundary condition;
- a provenance-bearing diffusion coefficient;
- a provenance-bearing first-order decay rate;
- a provenance-bearing initial concentration.

The currently supported boundary condition is `no_flux`. Additional conditions should be added only when an engine integration and validation case require them.

## Units

The first transport contract uses:

| Quantity | Contract unit |
| --- | --- |
| length | `micron` |
| time | `min` |
| diffusion coefficient | `micron^2/min` |
| first-order rate | `1/min` |

A 2D experiment also declares `slice_thickness_micron`. This is physical geometry, not numerical resolution. The x/y mesh may be refined while the slice thickness stays fixed.

That distinction is required before amount-based sources or sinks can be modeled: BioFVM source/sink coupling uses voxel volume, so silently setting z thickness equal to x/y grid spacing would make physical release or uptake change when the numerical mesh is refined.

Synthetic verification cases choose their slice thickness explicitly. VesicleScope does not provide a biological default.

These names intentionally match the reviewed BioFVM/PhysiCell convention. Current PhysiCell configuration examples express diffusion as `micron^2/min`, decay as `1/min`, spatial units as `micron`, and time units as `min`.

VesicleScope does not perform implicit unit conversion. A transport parameter with a different unit fails validation at this boundary.

The concentration unit is carried by its `ScientificParameter` rather than globally fixed here because BioFVM substrate units are model-defined. A later EV-specific experiment must define its concentration/count semantics explicitly.

## Closed-form decay reference

For a spatially uniform field with no source, no uptake, and first-order loss rate `lambda`, diffusion creates no gradient and the exact solution is:

```text
c(t) = c0 * exp(-lambda * t)
```

`vesiclescope.validation.first_order_decay` implements only this closed-form reference.

It is not a PDE solver. It is used to verify that a numerical engine maps initial concentration, decay rate, and time consistently.

Required invariants include:

- at `t = 0`, `c(t) = c0`;
- at `lambda = 0`, concentration is unchanged;
- non-negative initial value, rate, and time remain finite and non-negative.

## Implemented engine verification

The pinned BioFVM integration now covers two complementary synthetic checks:

- the [spatial cosine-mode diffusion benchmark](research/biofvm-diffusion-benchmark.md), which compares BioFVM against a bounded analytical diffusion solution;
- the [contract-driven uniform-decay adapter](biofvm-adapter.md), which maps this `TransportExperiment` into the native solver and compares sampled output with `first_order_decay`.

Both are numerical verification artefacts. Neither introduces biological EV defaults.

## Localized release benchmark

The first source-side extension adds a synthetic `PointReleaseSource` with amount-rate unit `particle_equivalent/min`.

The source is mapped to BioFVM net export rather than the saturation-based secretion model. Under zero decay, zero uptake and no-flux boundaries, the benchmark verifies:

```text
M(t) = q * t
```

where `M` is the integrated field quantity. In this benchmark the concentration unit is `particle_equivalent/micron^3`, so `∫c dV` has unit `particle_equivalent`.

The benchmark is run across x/y mesh refinement at fixed physical slice thickness. This checks that a numerical resolution change redistributes concentration without changing the physical amount released.

See [localized release model baseline](research/localized-release-model.md) for the evidence boundary and model rationale.

## Localized uptake benchmark

The first sink-side extension adds a synthetic `PointUptakeSink` with:

- explicit effective recipient volume in `micron^3`;
- uptake coefficient in `1/min`;
- explicit x/y location.

The benchmark uses BioFVM's own `Basic_Agent.uptake_rates` update and internalized-substrate tracking.

With zero source, zero extracellular decay and zero diffusion, CI verifies both:

```text
rho[n+1] = rho[n] / (1 + dt * (V_agent / V_voxel) * U)
```

and

```text
extracellular integrated quantity + internalized quantity
= initial integrated quantity
```

A timestep-refinement check confirms the implicit discrete update converges toward its continuous local first-order limit.

Unlike the constant amount-per-time source benchmark, point-sink uptake is not expected to be spatial-resolution invariant because `V_voxel` is part of BioFVM's sink discretization. This limitation is explicit rather than hidden.

See [recipient uptake model baseline](research/recipient-uptake-model.md) for the evidence boundary and model rationale.

## Combined donor-recipient distance benchmark

The first coupled benchmark combines one synthetic `PointReleaseSource` and one explicit-volume `PointUptakeSink`.

With zero initial amount, zero extracellular decay and no-flux boundaries, the global accounting invariant is:

```text
extracellular integrated quantity + internalized quantity
= release rate * time
```

Two otherwise identical runs vary only donor-recipient separation. The verification regime requires the nearer recipient to accumulate more internalized quantity by the final sample than the farther recipient. This is a numerical distance-sensitivity check, not a biological communication-range calibration.

See [donor-recipient distance model baseline](research/donor-recipient-distance-model.md) for the evidence boundary and operator-splitting semantics.

## Spatial result contract

Protocol v3 now exposes the complete extracellular 2D concentration field at every requested sample time, together with explicit grid geometry and ordering.

The normalized Python result cross-checks each field against the corresponding mean/min/max summary and integrated extracellular quantity before analysis can consume it. Uniform transport cases therefore preserve uniform fields, while localized release produces a verified non-uniform field without changing the existing mass-balance invariants.

See [spatial field result contract](spatial-field-results.md) for the protocol, ordering, validation rules and current stdout-size limitation.

## Recipient population benchmark

Protocol v4 extends uptake verification to multiple point recipients with separate cumulative uptake series.

The first population benchmark places two identical recipients in mirror-symmetric, distinct numerical voxels around one donor. CI verifies equal uptake within numerical tolerance, aggregate internalized quantity equal to the per-recipient sum, deterministic reruns, and the existing global mass balance.

Recipients that map to the same numerical voxel are rejected because per-recipient attribution would otherwise depend on sequential sink order.

See [recipient population model baseline](research/recipient-population-model.md).

## Controlled recipient-count analysis

The first population analysis runs 2, 4 and 8 deterministic point recipients at a fixed 50 micron donor radius on one fixed 10 micron grid.

It derives explicit planar density in `recipient/mm^2`, donor distance, total/mean uptake and exhaustive half-open distance bins from normalized result objects only.

In the chosen synthetic regime, CI observes increasing total uptake from 2 to 4 to 8 recipients while every scenario preserves global mass balance. This is documented as a synthetic count sensitivity, not a biological density-response law.

See [recipient count and planar-density analysis](research/recipient-density-analysis.md).

## What comes next

The next useful output is the first reproducible scientific population/distance figure generated from normalized results, followed by finite recipient geometry before any spatial-refinement-independent density claim is made.

A persistent file format should be introduced only when that figure/analysis workflow defines concrete storage requirements.
