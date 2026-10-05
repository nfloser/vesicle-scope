# Synthetic diffusion × uptake factor experiment

Issue: #47  
Status: controlled synthetic model-behaviour experiment

## Question

This experiment asks how relative diffusion strength and relative recipient uptake strength interact in one fixed, already-verified finite donor/recipient geometry.

It is **not** a biological sensitivity analysis and does not claim that the tested factors represent physiological EV ranges.

## Fixed model context

Every condition uses the same synthetic setup:

- 210 × 210 micron 2D domain;
- 25 micron physical slice thickness;
- one finite circular donor centered at (105, 105) micron;
- donor radius 15 micron;
- aggregate release 120 particle_equivalent/min;
- eight non-overlapping finite circular recipients;
- recipient radius 15 micron;
- recipient effective uptake volume 1000 micron^3;
- zero initial concentration;
- zero decay;
- no-flux boundaries;
- 20 min duration;
- 5 min output cadence.

These values remain classified as `synthetic_benchmark`. They are verification inputs, not biological defaults.

## Factors

The experiment uses the full Cartesian product of:

- diffusion factors: 0.5×, 1×, 2× around a synthetic 100 micron^2/min baseline;
- uptake factors: 0.5×, 1×, 2× around a synthetic 0.5 1/min baseline.

This gives nine deterministic conditions in stable uptake-major ordering.

Only the diffusion coefficient and recipient uptake rates change between conditions.

## Endpoint and conservation check

For each run VesicleScope computes:

`total_released_quantity = aggregate_release_rate × duration`

and reports:

- final extracellular quantity;
- final internalized quantity;
- extracellular fraction of released quantity;
- internalized fraction of released quantity.

Because the experiment has zero initial quantity, zero decay and no-flux boundaries, the analysis requires:

`extracellular_fraction + internalized_fraction ≈ 1`

within the established numerical tolerance.

The endpoint consumes only the engine-neutral experiment contract and normalized result. It does not inspect native BioFVM state.

## Reproducibility

The reviewed CI demonstrator uses:

- BioFVM/PhysiCell through the pinned VesicleScope runner;
- 10 micron x/y grid spacing;
- 0.1 min timestep;
- the exact VesicleScope commit SHA from the GitHub Actions run.

Run locally after building the native runner:

```bash
python -m pip install -r requirements-figures.txt
bash scripts/fetch-physicell.sh
make -f native/biofvm_benchmark/Makefile runner

VESICLESCOPE_REVISION="$(git rev-parse HEAD)" \
python -m scripts.run_diffusion_uptake_factor_experiment \
  --runner build/native/biofvm_transport_runner \
  --output-dir build/diffusion-uptake
```

The output directory contains:

- `summary.json` with deterministic condition ordering and endpoint values;
- `diffusion-uptake.svg` with an interaction heatmap and interaction lines;
- `runs/` with one deterministic VesicleScope run bundle per condition.

Each summary row also records the SHA-256 of the corresponding canonical run-bundle payload.

## Figure interpretation

Panel A shows the final internalized fraction as a 3 × 3 interaction heatmap.

Panel B plots the same nine analyzed runs as one line per uptake factor across diffusion factors.

The figure is explicitly labelled as:

- a controlled synthetic model-behaviour experiment;
- not experimental evidence;
- relative to synthetic baselines.

It must not be interpreted as an optimum, therapeutic range, physiological range or universal EV communication law.

## What this establishes

This experiment establishes that VesicleScope can run, persist, analyze and visualize a small controlled multi-condition study while preserving:

- fixed geometry;
- isolated factor changes;
- parameter provenance;
- normalized engine-independent outputs;
- conservation checks;
- exact code revision;
- durable run artefacts.

## What remains outside this experiment

This work does not provide:

- biological calibration;
- literature-derived EV parameter ranges;
- global sensitivity analysis;
- uncertainty quantification;
- Monte Carlo analysis;
- optimization;
- communication thresholds;
- external experimental validation.

Those require separate research gates and, where applicable, suitable measured data.
