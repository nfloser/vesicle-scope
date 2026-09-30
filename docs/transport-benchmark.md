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
- a bounded rectangular 2D domain;
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

## What comes next

The next engine-integration milestone can construct a uniform BioFVM field using this contract and compare sampled numerical concentration against the closed-form decay curve.

A later spatial benchmark should add a diffusion reference with a known solution and resolution-refinement checks. Donor release and recipient uptake should be introduced only after the transport-only adapter is verified.
