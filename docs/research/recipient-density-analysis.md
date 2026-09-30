# Recipient count and planar-density analysis

Issue: #23  
Status: synthetic fixed-grid population sensitivity

## Purpose

Protocol v4 provides recipient-specific cumulative uptake and protocol v3/v4 provides sampled extracellular fields. This milestone adds an engine-independent analysis layer that turns those normalized primary results into explicit population observables.

It does not add transport, source or uptake equations.

## Planar density terminology

Recipients are positioned in the x/y plane of the current physical slice model.

VesicleScope therefore reports:

```text
planar recipient density = recipient count / x-y domain area
```

with unit:

```text
recipient/mm^2
```

The conversion uses `1 mm² = 1,000,000 micron²`.

This is deliberately **not** called volumetric cell density. Slice thickness remains part of concentration/amount accounting, but the current recipient placement process is two-dimensional.

## Population summary

`vesiclescope.analysis.analyze_recipient_population` consumes only:

- the engine-neutral `TransportExperiment`;
- a normalized `BioFVMRunResult`;
- one requested sampled time.

It derives:

- recipient count;
- planar recipient density;
- quantity unit;
- total and mean cumulative uptake;
- one recipient observation per configured sink;
- Euclidean x/y donor-recipient distance in micron.

The analysis requires exactly one release source when donor distance is requested.

Recipient identifiers must match the experiment ordering, and the summed recipient uptake must agree with the normalized aggregate internalized quantity.

## Distance bins

`bin_recipient_uptake_by_distance` uses explicit half-open intervals:

```text
[lower, upper)
```

No recipient is silently discarded. If the supplied edges do not cover every observation, analysis fails.

Each bin records:

- bounds in micron;
- recipient count;
- total cumulative uptake;
- mean cumulative uptake;
- explicit quantity unit.

No threshold-based communication range is introduced.

## Controlled synthetic count sweep

The native integration benchmark fixes:

- one 210 × 210 micron x/y domain;
- physical slice thickness;
- one centered donor;
- release rate;
- diffusion coefficient;
- zero extracellular decay;
- uptake coefficient;
- effective recipient volume;
- 10 micron x/y grid;
- 0.1 min timestep;
- 20 min duration.

Recipient populations of 2, 4 and 8 are placed on lattice-compatible positions at exactly 50 micron donor distance.

The 2- and 4-recipient configurations use subsets of the deterministic ring position set; the 8-recipient case fills all configured ring positions.

For every scenario CI verifies:

- every recipient remains at 50 micron donor distance;
- planar density increases with count;
- released quantity equals extracellular plus total internalized quantity.

In this chosen synthetic regime the executed benchmark also gives:

```text
total uptake(2 recipients)
< total uptake(4 recipients)
< total uptake(8 recipients)
```

This ordering is a property of this verified synthetic setup. It is **not** asserted as a universal biological law.

## Interpretation limit

Changing recipient count necessarily changes angular occupancy around the donor, even though donor radius and all other declared model parameters are fixed.

The benchmark therefore demonstrates controlled count sensitivity at one fixed numerical resolution; it does not identify a unique biological density-response function independent of spatial arrangement.

Point-sink kinetics also retain the documented `V_agent / V_voxel` resolution dependence. Density scenarios must not be compared across grid refinement as though they were the same finite-cell model.

## What this does not establish

This milestone does not establish:

- a biological recipient density;
- a 3D volumetric cell density;
- finite cell geometry or packing;
- a communication-range threshold;
- experimentally calibrated density response;
- a density-independent spatial arrangement effect;
- a persistence or plotting format.

Those require later model and evidence decisions.
