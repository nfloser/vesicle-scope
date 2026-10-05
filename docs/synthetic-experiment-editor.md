# Interactive synthetic experiment editor

Issue: #72  
Status: v0.2 product workflow

## Purpose

The local VesicleScope browser workspace can derive a new experiment from an existing synthetic benchmark without requiring manual JSON editing.

This editor is deliberately provenance-safe. It is a convenience surface over the same immutable Python domain contracts and experiment-document serializer used by the CLI.

## Scientific boundary

The editor accepts a source experiment only when every scientifically meaningful parameter is classified as `synthetic_benchmark`.

It refuses measured, literature-derived, fitted, inferred, assumed or mixed-provenance experiments. Changing an evidence-backed value while retaining its old provenance would create a scientifically misleading document, so that workflow requires a future explicit provenance-editing design.

Editing never mutates or overwrites the source document.

## Editable values

For a synthetic source experiment the editor can derive a new experiment with:

- a new experiment ID;
- a new workspace filename;
- duration and sample cadence;
- diffusion;
- decay;
- initial concentration;
- release rates keyed by source identifier;
- uptake rates keyed by recipient identifier.

The editor preserves:

- canonical units;
- source and recipient geometry;
- source and recipient identifiers;
- synthetic evidence classification;
- parameter limitations, including the statement that reviewed synthetic values are not biological defaults.

The normal `TransportExperiment` and parameter validators remain authoritative for invalid values.

## Browser workflow

Start the local product as documented in the README:

```bash
vesiclescope workspace init ./workspace
vesiclescope engine build
vesiclescope ui \
  --workspace ./workspace \
  --runner ~/.cache/vesiclescope/engines/<reviewed-commit>/biofvm_transport_runner \
  --revision "$(git rev-parse HEAD)"
```

Then:

1. create the reviewed synthetic baseline or import a valid synthetic experiment;
2. select the experiment;
3. use **Create synthetic variant**;
4. choose a new filename and experiment ID;
5. modify scalar, donor-release or recipient-uptake values;
6. save the new variant;
7. run that derived experiment through the existing BioFVM execution path;
8. inspect and download the persisted run bundle.

The browser explicitly labels the workflow as synthetic and not experimental evidence.

## Architecture

The browser and HTTP API do not implement scientific mutation rules themselves.

`vesiclescope.experiment_editing.derive_synthetic_experiment` performs the derivation. The workspace service writes the returned immutable experiment document only after collision checks.

This keeps the scientific boundary shared across tests, HTTP, future CLI surfaces and any later frontend.

## Validation

Coverage includes:

- immutable source experiment;
- preservation of units, geometry and synthetic provenance;
- exact source/recipient identifier maps;
- rejection of non-synthetic provenance;
- rejection of invalid values;
- collision-safe workspace persistence;
- HTTP derivation round trip;
- static scientific-status language;
- native end-to-end derive → run → persisted deterministic run bundle.

## Non-goals

This editor does not yet provide:

- evidence-source editing;
- measured/literature parameter authoring;
- geometry drag-and-drop;
- new biological mechanisms;
- automatic parameter recommendations;
- optimization;
- biological validation.

Those require separate scientific and product decisions.
