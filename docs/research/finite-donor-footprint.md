# Finite circular donor footprint

Issue: #39  
Status: synthetic finite-source numerical verification

## Purpose

The Colombo 2025 external validation target measures EV-associated signal by distance from the **boundary of a finite donor-cell mask**.

The original VesicleScope source model is a single point net-export agent. Before a donor-boundary radial observable can be compared meaningfully, donor release needs an explicit physical footprint that is independent from numerical mesh resolution.

This milestone adds that geometry without claiming a biological HeLa donor size.

## Engine-neutral source

`CircularReleaseSource` declares:

- stable source identifier;
- center x/y in micron;
- circular footprint radius in micron;
- provenance-bearing aggregate release rate in `particle_equivalent/min`.

The radius and release rate are independent inputs.

VesicleScope does **not** infer release rate from donor area, perimeter, voxel count or slice thickness.

`PointReleaseSource` remains supported unchanged.

## Footprint rasterization

For one requested x/y grid, the BioFVM adapter enumerates voxel centers in deterministic y-row / x-fast order and selects centers satisfying:

```text
distance(voxel_center, donor_center) <= footprint_radius
```

At least one voxel center must be selected.

The complete physical circle must lie inside the rectangular experiment domain.

This is the same explicit center-inside rasterization convention already used for finite recipient footprints. It is a numerical representation of the declared footprint, not a membrane model.

## Aggregate amount-per-time preservation

The source's declared release rate is the **total amount released per minute by the scientific source**.

If the footprint covers `N` native components, VesicleScope divides the aggregate rate across those components.

The final component absorbs any floating-point remainder so:

```text
sum(component release rates)
= declared aggregate source release rate
```

Changing grid resolution may change component count and the local concentration pattern. It must not change the total amount released.

The source rate is therefore not an areal secretion density.

## Native BioFVM mapping

Every rasterized source component becomes one pinned BioFVM `Basic_Agent`.

VesicleScope configures the existing BioFVM `net_export_rates` field for each component and calls the existing source/sink update. No custom source equation is implemented.

Source components are required to map to distinct BioFVM voxels.

During source updates, global BioFVM internalized-substrate tracking is temporarily disabled so net export cannot enter recipient-uptake accounting.

## Verification invariant

The first finite-source benchmark uses:

- one synthetic circular donor;
- zero initial extracellular concentration;
- zero extracellular decay;
- no uptake;
- no-flux boundaries.

For declared aggregate release rate `q`:

```text
M_external(t) = q * t
```

at every sampled time.

The benchmark runs at 10 and 5 micron x/y grid spacing while holding fixed:

- physical donor center;
- physical donor radius;
- aggregate release rate;
- physical slice thickness;
- diffusion coefficient;
- timestep;
- duration.

The final field must be spatially non-uniform, but integrated released amount must agree across the two grids within numerical tolerance.

## Relationship to Colombo 2025

This closes only the **geometry prerequisite** identified by the validation target.

Colombo et al. measured distance from segmented donor-cell boundaries. A finite circular source lets VesicleScope define a donor boundary in physical coordinates, but the current radius is still a synthetic verification value.

It is not a measured HeLa radius and should not be used to calibrate the Colombo experiment.

The next separate milestone is an engine-independent donor-boundary radial-profile observable derived from normalized 2D concentration fields.

## Non-goals

This milestone does not establish:

- a biological donor-cell radius;
- secretion from a cell membrane rather than over a footprint;
- spatially heterogeneous release over the donor;
- stochastic EV release;
- donor morphology from microscopy;
- multiple donor cells;
- experimentally calibrated release rate;
- a biological communication range.
