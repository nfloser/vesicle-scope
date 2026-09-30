# Finite recipient count and planar-density sweep

Issue: #33  
Status: synthetic numerical verification completed

## Purpose

This milestone extends the reviewed 2/4/8 recipient-count sensitivity from historical point sinks to the finite circular recipient representation introduced in issue #29.

It does not introduce a new uptake equation. The existing BioFVM coupling, normalized recipient result contract and engine-independent population analysis are reused unchanged.

## Controlled synthetic geometry

The historical point-sink sweep remains unchanged for reproducibility, but its exact eight-center arrangement cannot be reused with 15 micron finite circles: some historical point centers are only about 14.1 micron apart, so those finite footprints would overlap.

The finite sweep therefore uses a separate deterministic nested ring. Every center remains exactly 50 micron from the donor at (105, 105), every coordinate is on a 5 micron increment, and all 15 micron circular footprints remain non-overlapping. This is a correction of an internally inconsistent geometry constraint, not a biological model change.

Each recipient has:

- circular footprint radius: 15 micron;
- effective uptake volume: 1000 micron^3;
- uptake coefficient: 0.5 1/min.

All are synthetic verification inputs. In particular, the radius is not a measured biological cell radius and no relationship between the planar radius and the effective uptake volume is implied.

The 2, 4 and 8 finite scenarios use stable prefixes of the finite ring and retain the same domain, physical slice thickness, donor, release rate, diffusion coefficient, zero decay, duration and sample cadence as the historical point scenarios. The historical point centers themselves are not modified.

## Why this experiment exists

The historical point-sink sweep demonstrated the population-analysis and figure pipeline but point uptake contains documented mesh sensitivity. Finite recipients distribute a fixed effective uptake volume over a physical circular footprint and have already been checked for volume preservation and self-convergence.

The next numerical question is therefore whether the qualitative 2 < 4 < 8 total-uptake ordering survives at both 10 and 5 micron x/y grids when the finite representation is used.

That ordering is tested as a property of this synthetic scenario, not asserted as a biological law.

## Analysis contract

No finite-recipient-specific analysis is introduced.

The existing `analyze_recipient_population` function derives:

- recipient count;
- planar density in recipient/mm^2;
- total cumulative uptake;
- mean cumulative uptake per recipient;
- donor distance per recipient.

This keeps analysis independent from the native engine representation.

## Verification requirements

At 10 and 5 micron x/y grids, with 0.1 min timestep, the native integration test must verify:

- one public uptake series per scientific recipient;
- all donor-recipient center distances remain 50 micron;
- all 15 micron finite footprints remain non-overlapping;
- the historical point-sweep geometry remains unchanged;
- released quantity equals extracellular plus aggregate internalized quantity at every requested sample;
- repeated runs are deterministic;
- final total uptake increases from 2 to 4 to 8 recipients;
- the ordering is identical at both grid resolutions.

Observed native CI values from the reviewed 20 min synthetic runs are:

| Recipients | Planar density (recipient/mm^2) | Final uptake @ 10 µm grid | Final uptake @ 5 µm grid |
| ---: | ---: | ---: | ---: |
| 2 | 45.3514739229 | 32.1785024274 | 32.1663684343 |
| 4 | 90.7029478458 | 64.1671186996 | 64.1429054128 |
| 8 | 181.4058956916 | 124.2457586250 | 124.9621302193 |

The monotonic ordering `2 < 4 < 8` is preserved on both grids.

The 10→5 micron relative change in final total uptake is approximately:

- 2 recipients: 0.038%;
- 4 recipients: 0.038%;
- 8 recipients: 0.573%.

These are synthetic numerical outputs, not biological uptake measurements.

## Interpretation boundary

Changing recipient count also changes angular occupancy and recipient-recipient spacing around the donor. This is therefore a controlled recipient-count / planar-density sensitivity experiment, not an isolation of density as a single causal variable.

The milestone does not establish:

- biological recipient density;
- a 3D volumetric cell density;
- a measured cell radius;
- random tissue packing;
- a communication-range threshold;
- experimental calibration;
- a biological monotonic uptake law.

A later figure update may replace the historical point-sink sweep only after this finite sweep has passed both numerical resolutions and independent review.
