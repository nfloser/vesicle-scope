# Time-resolved dose-response for exposures

Issue: #144
Status: model structure and verified workflow; all hormone-specific parameters remain unknown/synthetic

## Question

How should a declared exposure, for example a hormone pulse with a
concentration and a time window, change EV release or recipient uptake *over
time* without inventing a hormone calibration?

## Model structure

VesicleScope uses the established pharmacokinetic/pharmacodynamic
effect-compartment link: a hypothetical compartment coupled to the exposure by
a first-order process, whose concentration drives the effect (Sheiner et al.,
*Clin Pharmacol Ther* 1979;25:358–371, doi:10.1002/cpt1979253358). It is the
simplest standard model that separates sensitivity (EC50, Hill coefficient,
Emax) from the temporal delay (ke0). This matters for EVs because biogenesis
and release follow a stimulus with a lag.

```text
C(t)   = baseline + exposure inside [start, end), baseline otherwise
dCe/dt = ke0 (C(t) − Ce),          Ce(0) = baseline
H(Ce)  = Ce^n / (EC50^n + Ce^n)
m(t)   = (1 + Emax·H(Ce)) / (1 + Emax·H(baseline))
```

- `m(t)` multiplies either every release-source rate or every recipient uptake
  rate through a `RateSchedule` (see `docs/biofvm-adapter.md`).
- It is normalized to 1 at the baseline steady state, so an endogenous hormone
  with a non-zero baseline (for example cortisol) is handled explicitly instead
  of being assumed to be zero.
- `Emax > 0` stimulates. `−1 < Emax < 0` inhibits, and the lower bound keeps
  rates non-negative.
- `Ce(t)` is solved exactly for piecewise-constant input. Each schedule segment
  carries the Simpson time average of `m(t)`, so the integral of the multiplier
  is preserved within quadrature accuracy (checked to 4 decimals against a
  24 000-point reference).
- The schedule inherits the **weakest** evidence category of its inputs and
  records every parameter in its derivation text.

## What is not supplied

No hormone-specific `ke0`, `EC50`, `Emax`, Hill coefficient or baseline is
provided. The existing evidence in
[hormone-ev-perturbation-model.md](hormone-ev-perturbation-model.md) supports
effect directions in specific cell contexts, for example dexamethasone
increasing CD63-positive sEV release in Neuro2a cells. It does not support
human dose-response parameters. Each future hormone mapping must pass the
scientific gate with its own source note.

## Verified behaviour

Unit tests (`tests/test_dose_response.py`):

- `Ce(t)` matches the closed-form rise and decay;
- zero exposure gives `m = 1`;
- a long exposure converges to the steady Hill ratio;
- a slower `ke0` lags during the pulse and persists after it;
- inhibition lowers rates;
- unit mismatches are rejected.

BioFVM workflow (`tests/test_dose_response_biofvm_integration.py`, synthetic
scenario: 2 h pulse, 1/ke0 = 30 min):

- before the exposure the recipient internalization rate is identical to
  baseline (exact ratio 1);
- an **uptake** effect changes recipient internalization immediately, while a
  **release** effect reaches recipients only after transport. This is the
  dynamic counterpart of the steady-state result in
  [colombo-length-scale-constraint.md](colombo-length-scale-constraint.md):
  release changes amount, uptake changes both amount and range;
- the uptake response is partly buffered (simulated ratio 0.69 for a rate
  multiplier of 0.67), because reduced uptake leaves more EVs extracellular.

Reproduce:

```bash
python -m scripts.generate_dose_response_figure --runner <runner> --output build/dose-response.svg
```

## Limitations

- One exposure and one target rate per schedule. Combined release and uptake
  effects need two schedules, which the contract supports, but they are not yet
  generated together.
- The exposure acts uniformly on all donors or all recipients. There is no
  receptor gating by cell type yet.
- Hormone kinetics in the exposure itself, such as clearance or a circadian
  profile, are not modelled. `C(t)` is a declared rectangular window.

## Next steps

1. Receptor-gated mapping per recipient population, reusing the existing
   phenotype/population workflow.
2. Exposure profiles beyond a single window, for example measured time series.
3. The first literature-reviewed parameter set (glucocorticoid release effect)
   through the scientific gate, with unknown parameters as explicit ranges and
   an ensemble instead of point values.
