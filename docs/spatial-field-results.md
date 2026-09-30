# Spatial field result contract

Issue: #19  
Status: field surface introduced in protocol v3; retained in current protocol v4

## Purpose

Global mean/min/max and integrated quantities are sufficient for solver verification, but they are not sufficient for spatial EV questions.

Distance-binned exposure, recipient-density experiments, heatmaps, and later reproducible figures require the primary extracellular concentration field at each requested output time.

Protocol v3 introduced sampled 2D fields to the normalized BioFVM result contract without introducing a persistence layer or visualization dependency.

## Spatial field records in current protocol v4

The native stdout stream starts with:

```text
VESICLESCOPE_BIOFVM_RESULT<TAB>4
```

It then includes one grid descriptor:

```text
grid<TAB>nx<TAB>ny<TAB>grid_spacing_micron<TAB>slice_thickness_micron<TAB>x_fastest_then_y
```

For every summary sample, the runner emits one field record at the same simulation time:

```text
sample<TAB>time<TAB>mean<TAB>min<TAB>max<TAB>internalized
field<TAB>time<TAB>c0<TAB>c1<TAB>...<TAB>c(nx*ny-1)
```

The field values use the same concentration unit carried by the source experiment.

## Ordering

The current BioFVM runner uses one z layer.

Field values are emitted in the native Cartesian-mesh index order:

1. x index changes fastest;
2. y index changes next;
3. z is fixed because the current contract has exactly one physical slice layer.

For an x index `ix` and y index `iy`, the row-major flattened index is:

```text
index = iy * nx + ix
```

The ordering string is explicit in the protocol and the parser rejects unknown ordering values.

## Normalized Python result

`BioFVMRunResult` carries:

- one immutable `BioFVMGrid2D`;
- the existing ordered summary samples;
- one immutable `SpatialFieldSnapshot2D` per summary sample.

Each field snapshot contains:

- sample time in minutes;
- an immutable tuple of non-negative finite concentration values.

The grid descriptor contains:

- `nx`;
- `ny`;
- x/y grid spacing in micron;
- physical slice thickness in micron;
- ordering identifier.

## Cross-validation

The parser does not trust the summary and field records independently.

For every sample it verifies that the field-derived:

- mean concentration;
- minimum concentration;
- maximum concentration;
- integrated extracellular quantity

agree with the corresponding normalized summary values within numerical tolerance.

It also verifies:

- grid dimensions reproduce the experiment width/height;
- returned x/y grid spacing matches the numerical configuration requested by `run_transport`;
- slice thickness matches the physical experiment;
- field value count is exactly `nx * ny`;
- field times match summary times one-for-one.

This makes spatial analysis depend on internally consistent primary output rather than unchecked simulator text.

## Scope and size limitation

The field records introduced in protocol v3 remain unchanged in protocol v4, which additionally carries per-recipient uptake records. The current protocol still transfers sampled fields through the existing subprocess stdout channel.

That is appropriate for the small v0.1 verification domains and keeps the engine boundary inspectable.

It is **not** a claim that tab-separated stdout is the correct transport for large production fields. Larger 2D/3D studies may require a file-based or binary result transport later.

No HDF5, Zarr, database, compression layer, or remote object store is introduced until a concrete production analysis requires one.

## Non-goals

This result-contract change does not introduce:

- recipient-density biology;
- communication-range thresholds;
- plotting or UI code;
- a persistence schema;
- a 3D field representation;
- new source, sink, transport, or uptake parameters.
