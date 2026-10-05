# Explicit experiment batches

Issue: #70  
Status: deterministic product workflow for user-supplied experiment sets

## Purpose

The stored-run ensemble analysis introduced in the 0.2 development line operates on completed run bundles. This workflow closes the preceding product gap: a user can execute an explicit ordered set of validated experiment documents without manually invoking one solver run at a time.

The batch does not create an uncertainty design. It executes the documents it is given.

## Command

```bash
vesiclescope experiment run-batch \
  experiments/member-a.json \
  experiments/member-b.json \
  experiments/member-c.json \
  --runner build/native/biofvm_transport_runner \
  --revision "$(git rev-parse HEAD)" \
  --grid-spacing-micron 10 \
  --time-step-min 0.1 \
  --output-dir build/my-batch
```

The command prints the completed batch manifest followed by member run-bundle paths in the supplied order.

Those runs can be passed directly to:

```bash
vesiclescope run-bundle ensemble build/my-batch/*.run.json
```

When ordering matters, pass the files explicitly or use a stable lexical sort. Batch filenames start with a zero-padded member index so ordinary lexical ordering reproduces the original batch order.

## Preflight behavior

Before BioFVM executes, VesicleScope:

1. reads and validates every experiment document;
2. verifies that experiment IDs are unique within the batch;
3. verifies that the declared native runner exists;
4. determines every output filename;
5. rejects an existing batch manifest or member output collision.

This prevents a late duplicate-ID or overwrite error after several expensive runs have already completed.

## Output naming

Scientific experiment IDs are not changed.

The filesystem filename is derived separately:

```text
001-<safe experiment-id>.run.json
002-<safe experiment-id>.run.json
...
```

Characters outside letters, digits, dot, underscore and hyphen are replaced only in the filename. Very long filename components are deterministically shortened and receive a SHA-256-derived suffix.

The original experiment ID remains unchanged inside the run bundle and is recorded verbatim in the manifest.

## Batch manifest

`batch-manifest.json` is written only after every member succeeds.

It records:

- schema/version;
- explicit-input scientific status;
- exact VesicleScope revision;
- common numerical grid spacing and timestep;
- stable member index;
- input filename;
- original experiment ID;
- run-bundle filename;
- canonical run-bundle payload SHA-256.

The manifest contains no generated timestamp, hostname or absolute machine path.

If a member fails, already completed member bundles may remain available for diagnosis, but no completed batch manifest is written. This avoids representing a partial batch as complete.

## Scientific interpretation

A batch is only orchestration.

It does **not** imply:

- random sampling;
- an uncertainty distribution;
- biological plausibility of the supplied parameter values;
- statistical independence;
- Monte Carlo analysis;
- sensitivity analysis.

Those meanings belong to the experiment inputs and subsequent analysis, not to the batch runner.

## Why sequential execution

The first implementation is intentionally sequential.

The current requirement is a small, auditable local research workflow. A distributed scheduler, multiprocessing abstraction, retry framework or workflow dependency would add failure semantics and reproducibility complexity without a demonstrated workload requirement.

Parallel execution can be reconsidered if measured workloads justify it.
