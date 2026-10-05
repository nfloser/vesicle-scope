# COMBINE Archive interoperability decision

**Review date:** 2026-10-05  
**Decision:** support OMEX packaging before claiming SED-ML interoperability.

## Question

VesicleScope can already persist deterministic experiment documents and run bundles. The next interoperability question is whether those artifacts can be packaged using community standards without claiming semantics the current spatial BioFVM model cannot actually provide.

## Reviewed standards

### COMBINE Archive / OMEX

COMBINE defines an archive as a single file containing the documents needed for a modelling/simulation project. The archive is encoded as OMEX and requires a root `manifest.xml` declaring the archive and its contents.

References:

- COMBINE standards overview: https://co.mbine.org/standards/
- COMBINE Archive specification: https://github.com/combine-org/combine-specifications/blob/main/specifications/omex.md
- normative OMEX specification PDF: https://raw.githubusercontent.com/combine-org/combine-specifications/main/specifications/files/omex.version-1.pdf
- OMEX metadata specification: https://github.com/combine-org/combine-specifications/blob/main/specifications/omex-metadata.md

The normative archive specification defines:

- archive namespace: `http://identifiers.org/combine.specifications/omex`;
- manifest namespace: `http://identifiers.org/combine.specifications/omex-manifest`;
- mandatory root `manifest.xml`;
- one manifest content entry representing the archive itself;
- content entries with `location`, `format` and optional `master`.

JSON resources can be declared by media-type URI. VesicleScope therefore does not need to invent a COMBINE specification identifier for its native JSON formats.

### SED-ML

SED-ML Level 1 Version 5 is the current reviewed SED-ML technical specification:

- https://sed-ml.org/documents/sed-ml-L1V5.pdf

SED-ML describes simulation experiments by referencing models, simulations/tasks, algorithms and outputs. Its interoperability value depends on a model representation and execution semantics that another conforming tool can interpret.

BioSimulators also uses SED-ML/OMEX as an interoperability layer across supported model frameworks:

- https://biosimulators.org/

## VesicleScope gap

The current VesicleScope experiment document contains spatial geometry, provenance-aware parameters and BioFVM execution semantics, but it is **not** a standardized model-language document such as SBML or CellML.

The native BioFVM runner is deliberately narrow and VesicleScope-specific. A generic SED-ML executor cannot reconstruct the current spatial model merely from the VesicleScope experiment JSON.

Encoding a SED-ML file that references the VesicleScope JSON as though it were a portable standardized model would therefore imply interoperability that does not exist.

## Decision

Implement **COMBINE Archive / OMEX container support** now.

An archive may contain:

- one deterministic VesicleScope experiment document;
- zero or more deterministic VesicleScope run bundles for that exact experiment;
- `manifest.xml`;
- a human-readable project readme.

The experiment is the manifest's master resource because it is the primary project definition.

The VesicleScope JSON files are declared as JSON media-type resources, not as invented COMBINE model formats.

## Reproducibility choices

VesicleScope writes deterministic archives:

- stable member names/order;
- stored ZIP members rather than compressor-version-dependent output;
- fixed ZIP timestamps and file modes;
- normalized UTF-8 text;
- no wall-clock metadata;
- no absolute filesystem paths.

Archive validation reuses the existing experiment and run-bundle validators. OMEX does not weaken those scientific contracts.

## Safety boundary

Reader validation rejects:

- duplicate ZIP member names;
- absolute, backslash or traversal member paths;
- malformed/unsupported manifests;
- unlisted archive members or manifest entries for missing files;
- corrupted experiment/run payload digests;
- run bundles whose embedded experiment differs from the archive experiment.

Inspection performs no BioFVM execution.

## What would be required for honest SED-ML support

Before VesicleScope claims SED-ML interoperability, a separate research/architecture decision must establish at least one of:

1. a standardized model-language representation that faithfully captures the supported spatial transport experiment, or
2. a community-recognized executable/model format and algorithm mapping that generic SED-ML tooling can identify without VesicleScope-specific hidden semantics.

That future work must define a KiSAO-compatible algorithm identity where applicable, model-variable targets, parameter changes and expected outputs, and must be validated with an independent SED-ML/OMEX tool.

Until then, VesicleScope OMEX files are **portable project containers, not generic SED-ML simulation packages**.
