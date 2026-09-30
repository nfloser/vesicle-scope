# Donor-recipient distance model baseline

Status: synthetic verification model for issue #17  
Reviewed: 2026-09-30

## Scientific motivation

Distance between an EV donor and potential recipient is a biologically meaningful variable, but current measurements are highly context dependent.

Colombo et al. directly studied labelled EV exchange in HeLa-based in vitro systems and a tumour model. Their spatial analyses reported strong enrichment near donor cells and a rapid decline of EV-associated signal with distance.

Relevant observations from that specific study include:

- in vitro, 53% of detected EV signal was associated with recipients within the first 14 µm from the donor-cell edge;
- approximately 95% of signal was retained within roughly 56–60 µm from donor cells in that in vitro analysis;
- in the tumour analysis, the fitted distribution retained about 80% of signal within 40 µm, with less than 5% extending beyond 100 µm.

Reference:

- Colombo F, Nimkar K, Norton EG, Lovat F, Cocucci E. *Exploring the Spatial Limits of Extracellular Vesicles-Mediated Intercellular Communication.* Journal of Extracellular Vesicles. 2025;14:e70169.
- DOI: https://doi.org/10.1002/jev2.70169
- PMID: 41167986

These observations motivate donor-recipient separation as a first-class experiment variable. They are **not** parameter defaults or acceptance thresholds for the current synthetic model.

The current VesicleScope benchmark lacks experimentally anchored finite cell geometry, EV-specific transport calibration, ECM interaction, interstitial flow, measured release/uptake parameterization and intracellular degradation. Directly fitting the point-source/point-sink benchmark to the reported distances would therefore overstate what the model represents.

## v0.1 combined model

The combined benchmark reuses the already verified engine-neutral primitives:

- `PointReleaseSource` for constant amount-per-time extracellular release;
- `PointUptakeSink` for explicit-volume first-order uptake;
- BioFVM diffusion in the extracellular field;
- a bounded physical 2D slice with no-flux boundaries.

Exactly one source and one sink are supported by the current BioFVM adapter.

No new biological parameter is introduced by combining them.

## Numerical operator order

For each numerical timestep, the native runner currently applies:

```text
1. source net export
2. recipient uptake
3. diffusion / extracellular decay
```

This is an operator-splitting choice of the runner. It is not a biological claim about an ordering of release, uptake and transport inside a real tissue.

A recipient in a different voxel therefore cannot capture material newly released during the same timestep until diffusion has moved material during that step. Timestep-refinement and later model-validation work must account for this numerical splitting.

## Verification invariants

The first combined experiment uses:

- zero initial extracellular amount;
- zero extracellular decay;
- one constant source;
- one uptake sink;
- no-flux boundaries.

The primary accounting invariant is:

```text
Q_external(t) + Q_internalized(t) = q_release * t
```

where `q_release` is the synthetic source rate.

The benchmark also compares two otherwise identical simulations that differ only in donor-recipient separation. The selected synthetic regime must satisfy:

```text
internalized_near(final) > internalized_far(final)
```

This is a numerical sensitivity check, not a fit to the Colombo et al. distance distribution.

Repeated identical runs must also reproduce the same normalized quantities within the declared tolerance.

## What this does not establish

Passing this benchmark does not establish:

- a biological communication range;
- the 14, 40, 56–60 or 100 µm measurements as VesicleScope predictions;
- a validated EV diffusion coefficient;
- a validated release rate;
- a validated uptake coefficient or recipient volume;
- a population-density effect;
- finite donor or recipient shape;
- ECM trapping, binding or interstitial flow;
- intracellular EV degradation or cargo action.

Those require later evidence-backed scenarios and model extensions.
