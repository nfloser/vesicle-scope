# Validation plan for the first transport implementation

Status: required before the BioFVM adapter can be called scientifically usable.

## Validation layers

### 1. Contract validation

Verify:
- required fields exist;
- units match the canonical contract;
- all regions lie inside the domain;
- sampling cadence is compatible with duration;
- stochastic experiments specify a seed;
- referenced evidence IDs exist;
- adapter capabilities cover the requested boundary condition and model class.

### 2. Dimensional validation

Every implemented equation and adapter conversion must be checked dimensionally.

Examples:
- `D * laplacian(c)` has concentration/time units;
- `lambda * c` has concentration/time units;
- release conversion into a voxel includes cell count and voxel volume;
- count-to-concentration conversions include the explicit slice thickness.

A test should fail if an adapter silently mixes seconds/minutes, metres/micrometres, or areal/volumetric concentration.

### 3. Analytical limiting cases

#### Pure first-order loss

With uniform concentration, no source, no diffusion gradient, and no uptake:

```text
c(t) = c0 * exp(-lambda * t)
```

Compare numerical samples against the analytical curve.

#### Uniform uptake plus degradation

With a spatially uniform effective uptake rate `k`:

```text
c(t) = c0 * exp(-(lambda + k) * t)
```

This checks sink composition independent of spatial diffusion.

#### Diffusion of a localized pulse

In a sufficiently large domain over a short interval, compare the numerical field to the appropriate Gaussian diffusion solution away from boundaries. The test must state the dimensionality and normalization used.

### 4. Invariants and monotonic properties

Applicable checks include:
- non-negative concentration within declared numerical tolerance;
- total amount remains constant for no-flux diffusion with no sources/sinks;
- total amount decreases monotonically when only non-negative loss terms are active;
- cumulative uptake never decreases;
- zero release produces no newly created EV amount.

If an engine cannot expose a quantity needed for an invariant directly, the adapter must document the approximation used to estimate it.

### 5. Numerical convergence

Run at multiple spatial/time resolutions.

A benchmark is not accepted merely because one grid looks plausible. The observed solution difference should decrease under refinement until the chosen production resolution is justified for the benchmark.

### 6. Adapter regression

Pin:
- engine version;
- test experiment;
- selected output statistics;
- tolerances.

A dependency update that changes validated output outside tolerance requires review rather than an automatic snapshot refresh.

### 7. Continuum vs particle comparison

After the Smoldyn adapter exists, construct matched experiments using the same geometry, release schedule, diffusion coefficient, degradation model, and uptake semantics.

Compare:
- spatial mean concentration / density;
- recipient-region delivered amount;
- time-to-dose summaries;
- replicate variability for the particle model.

The expected scientific question is not "are the engines identical?" but "in which parameter/copy-number regimes does the continuum approximation reproduce particle-level statistics within a declared tolerance?"

## Biological validation boundary

Analytical agreement validates the mathematics and adapter. It does **not** validate that the chosen parameter set represents a real biological system.

Biological validation requires experimental data with documented EV preparation, measurement method, conditions, and uncertainty. That belongs to a later calibration/validation issue.
