# Finite circular recipient footprint

Issue: #29  
Status: synthetic finite-footprint numerical verification

## Purpose

The original VesicleScope uptake model represents each recipient as one BioFVM point sink in one numerical voxel.

That model is useful for verifying uptake semantics, recipient identity and population accounting, but its local coupling contains `V_agent / V_voxel`. A smaller x/y grid therefore changes point-sink kinetics even when the declared uptake coefficient and effective recipient volume are unchanged.

The finite circular footprint is the first step toward separating physical recipient geometry from numerical mesh resolution.

It remains a **synthetic numerical coupling model**, not a biological cell-shape claim.

## Engine-neutral recipient

`CircularUptakeSink` declares:

- stable recipient identifier;
- center x/y in micron;
- circular footprint radius in micron;
- explicit effective uptake volume in `micron^3`;
- provenance-bearing uptake coefficient in `1/min`.

The radius and effective volume are independent inputs.

VesicleScope does **not** infer volume from the radius and does not interpret the radius as a measured cell radius unless a later experiment supplies that provenance.

The first contract requires the complete circular footprint to lie inside the rectangular domain. Boundary-clipped recipients are deferred.

## Voxel-center rasterization

At the requested x/y grid spacing, the BioFVM adapter enumerates all voxel centers in deterministic y-row / x-fast order and selects centers satisfying:

```text
distance(voxel_center, recipient_center) <= footprint_radius
```

The selected voxel centers become native BioFVM uptake components.

At least one voxel center must be selected.

This center-inside rule is a documented rasterization convention. It is not a membrane, receptor or subcellular model.

## Effective-volume preservation

If a recipient covers `N` selected voxels, the declared effective uptake volume is divided across those `N` components.

The final component absorbs any floating-point remainder so that the configured component volumes sum back to the declared recipient effective volume.

Therefore:

```text
sum(component effective volumes) = declared recipient effective volume
```

at every supported grid spacing.

Grid refinement changes the spatial sampling of the footprint, not the total configured recipient volume.

## Native BioFVM execution

Every footprint component remains an ordinary pinned BioFVM `Basic_Agent` configured with:

- its component effective volume;
- the recipient's original uptake coefficient;
- the component voxel-center position.

VesicleScope does not reimplement BioFVM's uptake equation.

The native runner tracks every component's internalized substrate, then sums all components belonging to the same recipient before emitting the public recipient uptake record.

The normalized result therefore still contains **one `RecipientUptakeSeries` per scientific recipient**, not one series per implementation component.

## Recipient collisions

Components belonging to one circular recipient must occupy distinct BioFVM voxels by construction.

Components belonging to different recipients may not share a voxel in this milestone.

The Python adapter rejects collisions during deterministic rasterization and the native runner independently verifies actual BioFVM voxel assignment before simulation.

This avoids order-dependent per-recipient attribution.

Overlapping biological footprints are not modeled yet.

## Protocol v5

Protocol v5 extends recipient metadata so geometry can be round-tripped explicitly.

A recipient metadata record is:

```text
recipient<TAB>index<TAB>kind<TAB>x<TAB>y<TAB>radius<TAB>effective_volume<TAB>uptake_rate<TAB>component_count
```

where `kind` is `point` or `circle`.

Python validates:

- geometry kind;
- recipient center;
- radius;
- declared effective volume;
- uptake coefficient;
- expected component count at the returned grid.

The public recipient uptake time-series contract remains unchanged.

## Grid-refinement verification

The first native finite-footprint benchmark uses one synthetic circular recipient and compares x/y grids of 10 and 5 micron while holding fixed:

- donor/source geometry;
- recipient center;
- footprint radius;
- recipient effective volume;
- uptake coefficient;
- diffusion coefficient;
- slice thickness;
- timestep;
- duration.

At both resolutions CI verifies:

```text
extracellular quantity + recipient internalized quantity
= cumulative released quantity
```

The final cumulative uptake at 10 and 5 micron must agree within a relative difference of 10%.

That 10% value is a numerical verification tolerance for this deliberately chosen synthetic benchmark. It is **not** a biological uncertainty bound or a universal convergence criterion.

The finite model should be refined further before any experimental calibration relies on its spatial discretization.

## Backwards compatibility

`PointUptakeSink` remains unchanged.

A point recipient still maps to one native BioFVM uptake component at its declared position, and all historical point-sink, multi-recipient, donor-distance, spatial-field, population-analysis and figure tests remain part of CI.

This gives VesicleScope a retained reference for demonstrating why the finite-footprint model was introduced.

## What this does not establish

Passing this benchmark does not establish:

- a biological recipient-cell radius;
- a relationship between 2D radius and 3D cell volume;
- a membrane or receptor distribution;
- receptor binding or uptake saturation;
- a validated cellular morphology;
- overlapping-cell behavior;
- boundary-clipped cells;
- cell mechanics or migration;
- a biological recipient density;
- an experimentally validated EV communication range.

Those require separate evidence and model decisions.
