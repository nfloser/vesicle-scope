# External experiment documents

VesicleScope experiment documents provide a deterministic external file boundary for the current engine-neutral `TransportExperiment` contract.

They exist so users can create, inspect and validate an experiment without writing Python while preserving the same scientific semantics used by durable simulation run bundles.

## Status

Schema: `vesiclescope.experiment`  
Version: `1`

This is a VesicleScope-native JSON format. It is **not SED-ML, OMEX, MultiCellDS or MultiCellML**.

The current spatial BioFVM experiment cannot yet be represented completely and honestly by those standards, so VesicleScope does not label this document as standards-compliant.

## Document structure

```json
{
  "schema": "vesiclescope.experiment",
  "version": 1,
  "payload_sha256": "...",
  "payload": {
    "experiment": {
      "...": "the validated engine-neutral experiment contract"
    }
  }
}
```

The experiment payload uses the same encoding boundary as deterministic run bundles. That prevents file import and completed-run persistence from silently developing different meanings for geometry, parameters or provenance.

The SHA-256 digest covers canonical payload JSON. Accidental or unreviewed payload edits therefore fail validation until the document is deliberately rewritten with a new digest.

## Export a reviewed starting point

```bash
vesiclescope experiment export-example diffusion-uptake-baseline \
  --output experiment.json
```

The exported file is the 1× diffusion / 1× uptake condition from the reviewed synthetic factor experiment.

Every numerical value remains `synthetic_benchmark` and carries the same limitations as the in-code scenario. Exporting it does not turn those values into biological defaults.

## Validate

```bash
vesiclescope experiment validate experiment.json
```

Validation reconstructs the normal `TransportExperiment` domain object, so existing geometry, unit, evidence/provenance and source/sink validation still applies.

Unknown schema versions, invalid JSON, digest mismatch, unsupported boundary/source/sink types and invalid scientific parameters fail rather than being coerced.

## Inspect

```bash
vesiclescope experiment inspect experiment.json
```

The concise summary reports:

- experiment identifier;
- physical domain dimensions;
- duration and output cadence;
- boundary condition;
- release-source count;
- uptake-sink count;
- evidence categories represented by the experiment.

Inspection does not execute the model.

## Editing

Version 1 is deliberately explicit. Editing the JSON by hand invalidates the digest. This is intentional.

The supported product flow is currently:

1. export a reviewed example;
2. use the file as a transparent reference/template;
3. create or modify experiments through a writer that recomputes the document digest;
4. validate before execution.

A future interactive editor can use the same read/write API.

VesicleScope does not currently infer missing units, sources or evidence categories and does not insert biological defaults to make an invalid document run.

## Reproducibility boundary

An experiment document captures the scientific experiment definition. A completed run bundle additionally captures:

- exact VesicleScope revision;
- numerical solver settings;
- pinned engine identity;
- normalized simulation outputs.

Therefore an experiment document is an input artifact, while a run bundle is a completed execution artifact.
