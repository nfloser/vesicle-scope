# EV measurement and phenotype workspace

Status: visible client for the server-side research contracts introduced in #106

The local workspace exposes three linked, but scientifically distinct, views:

1. longitudinal blood/plasma measurements and pre-analytical provenance;
2. perturbation evidence, phenotype markers, cargo and limitations;
3. stored phenotype-specific or aggregate simulation fields.

The browser does not classify observations or interpret biological evidence.
The API supplies measurement display groups, evidence categories, sources,
effect status and limitations. The UI renders those values without converting
units or inventing an unchanged response for an unknown effect.

## Measurements

Measurement JSON can be imported through the workspace. The view separates
`total_or_unmarked`, `marker_defined` and `cargo` observations using the
server-provided display group. It exposes specimen, anticoagulant,
collection-to-processing time, centrifugation, residual platelet count,
haemolysis assessment and declared limitations.

Every measurement card belongs to one recorded time point. Missing times are
not connected, interpolated or imputed.

## Phenotypes and evidence

Perturbation studies can be imported and inspected next to their declared
measurement dataset references. Marker and cargo cards retain their evidence
category, source identifier and limitations. Missing cargo, effects or sources
are shown as explicitly unknown rather than silently treated as negative or
unchanged.

## Spatial population comparison

A stored population-run bundle may be inspected as either its derived total or
one declared phenotype. The two maps have independent integer-index sliders.
Each index selects one persisted field snapshot and reports its actual
`time_min`; the client never reconstructs an intermediate field.

When concentration units match, the visible pair uses one concentration scale
calculated from the two selected snapshots. If they differ, each map is
labelled with an independent scale; presenting a shared scale in that case
would be scientifically invalid. A direct comparison is marked compatible only
when concentration units, grids and spatial spacing match. Axes are expressed
in micrometres from the stored grid spacing, and the plotted field keeps the
stored x/y aspect ratio.

This first visible slice does not yet execute a new population study or overlay
measurement residuals. Those remain part of issue #107 and must continue to use
the existing server endpoints rather than implementing scientific logic in
JavaScript.

## Stored-run temporal comparison contract

The run-inspection API returns the complete persisted `fields` sequence in
addition to the legacy-compatible `final_field`. Each field retains its recorded
`time_min`; clients must treat a one-element sequence as an end-field-only run.

The comparison endpoint accepts `left_time_min` and `right_time_min` only as a
pair. A spatial difference is returned only when both requested times exist
exactly in their respective run bundles and the concentration units, grid,
spacing, slice thickness, physical domain and actual times match. Missing or
unequal times produce an explicit incompatibility reason. The endpoint never
interpolates, resamples or silently substitutes a nearby snapshot.
