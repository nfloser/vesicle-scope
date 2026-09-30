# Recipient population model baseline

Issue: #21  
Status: synthetic point-recipient population verification

## Purpose

VesicleScope now needs more than one recipient in a simulation so recipient count, spacing and later density can become explicit experiment variables.

This milestone does **not** turn the existing point-sink model into a finite-cell model. It only extends the already verified BioFVM uptake mapping from one explicit-volume point sink to several independently identified point sinks.

## Recipient identity

Every engine-neutral `PointUptakeSink` keeps its stable identifier in the `TransportExperiment`.

The native runner uses deterministic recipient indices rather than embedding arbitrary identifiers in its tab-separated protocol. Python validates each indexed native recipient record against the corresponding configured sink and then restores the original experiment identifier in the normalized result.

This avoids imposing an unnecessary escaping/character restriction on scientific identifiers.

## Distinct numerical voxels

Two point recipients are rejected when they map to the same x/y BioFVM voxel for the selected grid spacing.

BioFVM applies each uptake agent sequentially. Two sinks in the same voxel would therefore make the **per-recipient** attribution depend on sink ordering, even though aggregate removal can still be calculated.

Until recipients have a finite spatial representation, VesicleScope fails clearly instead of presenting that arbitrary attribution as a meaningful cell-specific result.

This is a numerical-model limitation, not a statement that biological cells cannot be close to one another.

For the current rectangular domain whose lower x/y bounds are both zero, VesicleScope mirrors the pinned BioFVM Cartesian-mesh lookup exactly:

```text
ix = floor(x_micron / grid_spacing_micron)
iy = floor(y_micron / grid_spacing_micron)
```

The pinned BioFVM implementation computes the same rule as `floor((position - bounding_box_min) / d*)`. A regression test covers an exact grid boundary so this attribution rule cannot silently drift during adapter refactors.

## Protocol v4

Protocol v4 extends the v3 grid/field result stream with recipient metadata and recipient-specific cumulative uptake records.

Static recipient metadata:

```text
recipient<TAB>index<TAB>x_micron<TAB>y_micron<TAB>effective_volume_micron3<TAB>uptake_rate_per_min
```

At every requested output time:

```text
recipient_uptake<TAB>time_min<TAB>index<TAB>internalized_quantity
```

The existing summary sample still carries aggregate internalized quantity.

The Python parser requires:

- exactly one recipient metadata record for every configured sink;
- metadata to match the engine-neutral sink parameters;
- exactly one uptake value per recipient and sample;
- recipient sample times to match summary times;
- every recipient series to start at zero;
- every recipient cumulative series to be finite, non-negative and non-decreasing;
- aggregate internalized quantity to equal the sum of recipient-specific quantities within numerical tolerance.

## Synthetic symmetry benchmark

The first population benchmark uses:

- one centered synthetic release source;
- two identical uptake sinks mirrored around the source;
- equal source-recipient distance;
- distinct recipient voxels;
- no extracellular decay;
- no-flux boundaries.

The domain uses dimensions that place the donor and the two recipient voxels in exact mirror symmetry at the tested grid spacing.

The verification invariant is:

```text
uptake_left(t) = uptake_right(t)
```

within numerical tolerance at every requested sample, while:

```text
extracellular quantity + uptake_left + uptake_right
= cumulative released quantity
```

also remains closed.

This verifies deterministic recipient attribution and symmetry. It is not evidence that real recipient cells have the chosen uptake coefficient, effective volume or spacing.

## What this does not establish

Passing this benchmark does not establish:

- a biological recipient density;
- finite cell radius or membrane geometry;
- spatial-resolution-independent point-sink uptake;
- receptor/endocytosis kinetics;
- competition between overlapping cells;
- random tissue packing;
- a biological communication range.

Those remain later model/evidence decisions.
