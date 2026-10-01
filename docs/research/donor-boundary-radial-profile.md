# Donor-boundary radial profile

Issue: #41  
Status: geometry/analysis baseline; not a quantitative Colombo 2025 comparison

## Purpose

Colombo et al. 2025 measure EV-associated signal by distance from the nearest donor-cell boundary. VesicleScope now has a finite circular donor footprint, so the next reproducibility step is to derive the same *kind of spatial coordinate* from normalized simulation fields.

This analysis deliberately stops before any fluorescence threshold, model fitting or claim that simulated concentration is equivalent to microscopy intensity.

## Distance definition

For a circular donor centered at `(c_x, c_y)` with physical radius `r`, each normalized field voxel center `(x, y)` receives the signed distance

```text
d_boundary = sqrt((x - c_x)^2 + (y - c_y)^2) - r
```

Interpretation:

- `d_boundary < 0`: voxel center is inside the donor footprint;
- `d_boundary = 0`: voxel center lies on the declared donor boundary;
- `d_boundary > 0`: voxel center is extracellular.

The radial profile excludes donor-interior and boundary voxel centers. Their count and integrated field quantity remain explicit in the returned analysis object so the field is not silently truncated.

## Engine independence

The analysis consumes only:

- the engine-neutral `TransportExperiment`;
- normalized `BioFVMRunResult` field/grid contracts.

It does not call BioFVM, inspect native agents or depend on the donor rasterization used internally by the solver.

The same analysis can therefore be reused for a future solver if that solver produces the same normalized result contract.

## Grid reconstruction

The normalized grid declares:

- x/y voxel counts;
- x/y spacing in micron;
- physical slice thickness;
- `x_fastest_then_y` ordering.

Voxel centers are reconstructed as:

```text
x = (x_index + 0.5) * grid_spacing
y = (y_index + 0.5) * grid_spacing
```

Donor/extracellular membership is classified by the voxel center. VesicleScope does not currently compute partial voxel-circle overlap or sub-voxel boundary fractions. That discretization convention is explicit and must be reconsidered if a future microscopy comparison requires image-scale boundary fidelity.

The analysis rejects a result when the normalized grid dimensions or slice thickness do not match the experiment domain.

## Quantity accounting

For one 2D voxel the represented physical volume is:

```text
V_voxel = dx * dy * slice_thickness
```

For the current square grid, `dx = dy = grid_spacing`.

The integrated field quantity contributed by a voxel is therefore:

```text
q_voxel = concentration * V_voxel
```

Before radial analysis, VesicleScope verifies that the complete normalized field reproduces the corresponding transport sample's integrated field quantity within numerical tolerance.

The returned profile accounts separately for:

- donor-interior/boundary voxels;
- extracellular voxels inside the requested radial extent;
- extracellular voxels outside the requested radial extent.

These three groups must account for every voxel and the complete normalized field quantity.

## Bin semantics

Radial bins use explicit half-open intervals:

```text
[lower, upper)
```

VesicleScope does not encode one canonical Colombo bin width.

The reviewed evidence records an unresolved reproducibility difference:

- the paper describes approximately 10 micron zones;
- the currently reviewed public analysis code uses 25 pixels at 0.2 micron/pixel, corresponding to 5 micron bins.

`fixed_width_distance_edges` can therefore construct either definition explicitly. The discrepancy remains visible rather than being normalized away.

## What the bins contain

Each radial bin currently reports:

- lower/upper boundary distance;
- contributing extracellular voxel count;
- mean simulated extracellular concentration;
- integrated simulated field quantity;
- explicit units.

A zero-voxel bin reports zero mean concentration and zero integrated quantity.

## What this does not mean

The Colombo experiment analyzes thresholded CD9-Halo-associated fluorescence pixels.

The current VesicleScope observable is a simulated concentration field.

Those are **not the same measurement model**.

This milestone does not add:

- a fluorescence threshold;
- image formation;
- microscopy noise/background;
- CD9-Halo labeling efficiency;
- concentration-to-intensity conversion;
- a biological donor radius;
- tumour-specific transport parameters;
- fitting to published radial landmarks.

## Updated Colombo readiness

Finite donor geometry and donor-boundary distance are no longer missing software capabilities.

Direct quantitative validation remains blocked because:

1. the raw tumour TIFF/source measurements are not publicly available;
2. the current donor radius is synthetic and simulated concentration has no validated mapping to thresholded CD9-Halo fluorescence;
3. the paper/public-code 10-versus-5-micron bin discrepancy remains unresolved;
4. current transport/release/uptake parameters are synthetic rather than calibrated to the HeLa tumour context.

The correct next step is therefore not automatic parameter fitting. A future issue must decide what defensible comparison can be made with available measurements and whether a measurement model or additional source data are required.
