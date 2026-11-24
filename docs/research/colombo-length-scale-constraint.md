# What the Colombo 2025 landmarks constrain: one transport length scale

Issue: #140
Status: analytical inference from public fit summaries; numerically verified against BioFVM; not a parameter fit to raw data

## Result

Under steady-state linear release, diffusion and first-order loss, the public
Colombo et al. 2025 tumour landmarks constrain exactly one quantity:

```text
lambda = sqrt(D / k_eff) ≈ 17–25 micron
```

where `D` is the effective EV diffusion coefficient and `k_eff` the effective
first-order loss rate (recipient uptake plus any clearance or decay). The range
spans the geometry/measurement assumptions below. The landmarks do **not**
separate `D` from `k_eff` and do **not** constrain release.

This is an inference conditional on the model class. It is not stored as a
VesicleScope parameter.

## Input

From `colombo_2025_tumour_distance_target()` (doi:10.1002/jev2.70169):

| Landmark | Kind |
| --- | --- |
| 50% of signal within 17 micron of the donor boundary | fit-derived summary |
| 80% within 40 micron | fit-derived summary |
| less than 5% beyond 100 micron | fit-derived bound |

Raw tumour images remain available only on request, so the blockers recorded in
[colombo-2025-validation-target.md](colombo-2025-validation-target.md) still
apply to any parameter fit.

## Model

Steady state of `D ∇²c − k_eff c = 0` outside the donor, with signal assumed
proportional to local concentration (linear uptake gives internalized signal
the same spatial shape). The cumulative signal fraction within boundary
distance `d` depends on geometry:

| Geometry | Profile `c(d)/c(0)` | Cumulative fraction `F(d)` |
| --- | --- | --- |
| planar boundary | `exp(−d/λ)` | `1 − exp(−d/λ)` |
| spherical donor, equatorial section | `R/(R+d) · exp(−d/λ)` | `1 − exp(−d/λ)` (perimeter `∝ R+d` cancels the `1/r`) |
| circular donor in a 2D slab (VesicleScope geometry) | `K0((R+d)/λ) / K0(R/λ)` | `1 − b·K1(b) / (a·K1(a))`, `a = R/λ`, `b = (R+d)/λ` |

The slab closed form follows from `∫ r K0(r/λ) dr = −λ r K1(r/λ)`.
`K0` and `K1` are evaluated from their integral representations without a new
runtime dependency and checked against tabulated values.

## Inferred length scale

Least-squares fit of `λ` to both landmarks (`scripts/generate_length_scale_figure.py`):

| Geometry | Assumed donor radius | λ [micron] | λ from 17 µm / 40 µm alone | Beyond 100 µm |
| --- | --- | --- | --- | --- |
| planar / spherical equatorial | – | 24.7 | 24.5 / 24.9 | 1.7% |
| 2D slab | 5 micron | 16.8 | 15.9 / 18.0 | 0.7% |
| 2D slab | 10 micron | 17.9 | 17.3 / 18.9 | 0.9% |
| 2D slab | 15 micron | 18.7 | 18.2 / 19.5 | 1.0% |
| 2D slab | 20 micron | 19.3 | 18.9 / 20.0 | 1.1% |

Every case satisfies the published `<5% beyond 100 micron` bound. The planar /
equatorial-section form matches the two landmarks almost exactly (single-landmark
solutions differ by 1.3%), which is expected because the publication itself
fitted an exponential. The 2D-slab form fits less well (6–13% spread), i.e. the
published curve looks more like a 3D or planar profile than a thin-slab one.
That is a measurement-model observation, not evidence about biology.

Donor radii are assumptions: the publication reports no in-vivo donor radius.

## Numerical verification

`tests/test_reach_biofvm_verification.py` runs the pinned BioFVM runner with a
circular donor (R = 10 micron), D = 100 micron²/min and decay 0.25/min
(λ = 20 micron) to steady state (40 min = 10/k) and compares the simulated
cumulative donor-boundary profile with the analytical slab solution:

| Grid | Max. absolute error in `F(d)` |
| --- | --- |
| 5 micron | 0.013 |
| 2.5 micron | 0.006 |

The error halves with grid refinement, and the inference recovers the simulated
λ within 5%. The analytical layer and the transport engine therefore agree on
the length-scale physics used here.

## What λ implies

`1/k_eff = λ² / D`. Panel (b) of the figure shows this for any assumed `D`.

Free-solution Stokes–Einstein diffusion at 37 °C (water viscosity 0.6913 mPa·s,
reference only, not a tissue value) gives 394 micron²/min for a 100 nm particle.
With that `D`, λ = 17–25 micron would require an effective loss timescale of
**0.7–1.5 minutes**.

Conversely, if effective loss in this tumour occurred over about one hour, the
effective diffusion would have to be about 5–10 micron²/min, roughly 40–80×
below free 100 nm diffusion.

So the landmarks imply at least one of:

1. strongly hindered EV mobility in tumour tissue (matrix confinement or
   binding), or
2. very fast local capture or clearance.

This is a testable prediction. Matrix hindrance of EV transport is an active
experimental topic (for example Lenzini et al., Nat. Nanotechnol. 2020,
doi:10.1038/s41565-020-0636-2; Tam et al., ACS Nano 2024,
doi:10.1021/acsnano.4c07186), but tissue-specific `D` values have not yet been
reviewed through the scientific gate and are not used here.

## Consequence for perturbation and hormone modelling

In this model class, multiplicative effects propagate as (planar steady state,
boundary flux J):

```text
c(0) = J / sqrt(D k_eff)      lambda = sqrt(D / k_eff)
threshold reach d* = lambda · ln(c(0) / c*)
```

| Effect (e.g. of a hormone) | λ changes by | Threshold reach |
| --- | --- | --- |
| release × f | 1 (unchanged) | + λ·ln f (doubling adds ≈ 12–17 micron) |
| uptake/clearance × f | 1/√f | changes through λ and c(0) |
| diffusion × f | √f | changes through λ and c(0) |

Implication for the hormone module: a reported effect on EV **release** alone
(for example glucocorticoid-increased CD63-positive sEV release, see
[hormone-ev-perturbation-model.md](hormone-ev-perturbation-model.md)) cannot
change the spatial shape of communication in a linear model. It only shifts
threshold reach logarithmically. Effects on recipient uptake, clearance or EV
size (through `D`) change the length scale itself. Panel (c) shows this for an
assumed `c(0)/c* = 10`. The threshold ratio is an explicit assumption, not a
measured value.

## Limitations

- Fit-derived landmarks, not raw measurements; no uncertainty on the landmarks
  is published, so no interval is reported for λ beyond the geometry spread.
- Steady state, linear uptake, isolated donors and signal ∝ concentration are
  assumptions.
- Thresholded fluorescence and saturable uptake can distort the mapping.
- HeLa xenograft tumour context only; no generalization to other tissues.

## Next steps that would sharpen this

1. Request the per-sample radial measurements from the corresponding author
   (still the main blocker for a real fit).
2. Add an independent `D` estimate for tumour-like matrix through the scientific
   gate. λ then fixes `k_eff`, and the release question becomes answerable with
   absolute measurements.
3. Use the length-scale relations as the backbone of the dose–response hormone
   module, so each hormone effect is classified as amount-changing or
   range-changing.

## Reproduce

```bash
python -m pip install '.[figures]'
python -m scripts.generate_length_scale_figure --output-dir build/length-scale
VESICLESCOPE_BIOFVM_RUNNER=<runner> python -m unittest tests.test_reach_biofvm_verification -v
```
