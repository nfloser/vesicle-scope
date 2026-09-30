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

## What comes next

Donor release and recipient uptake should only be introduced after a dedicated evidence review defines the biological mechanism, parameter provenance, observables and validation target. Spatial result storage/export should be added when that first real consumer exists rather than pre-designing a general field format.
