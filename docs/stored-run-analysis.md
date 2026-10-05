# Offline analysis of stored runs

VesicleScope run bundles preserve the experiment, parameter provenance, numerical settings, normalized BioFVM result and exact VesicleScope revision. A completed bundle can therefore be inspected and visualized without executing BioFVM again.

## Generate an overview

Install optional figure support and render the stored run:

```bash
python -m pip install 'vesicle-scope[figures]'
vesiclescope run-bundle figure run.json --output run.svg
```

The command first reads and verifies the deterministic run bundle, including its payload digest and scientific contracts. It then renders only persisted normalized data.

The overview contains:

- the final extracellular spatial field;
- extracellular and internalized model-quantity time series;
- concentration and quantity units;
- engine and PhysiCell/BioFVM identity;
- numerical grid spacing and timestep;
- exact VesicleScope revision;
- the scientific evidence status of the experiment inputs.

Synthetic-only inputs are labelled **not experimental evidence**. Runs that contain mixed or evidence-backed inputs are still labelled as simulations rather than biological truth.

## Reproducibility boundary

This path does not:

- invoke the native runner;
- fetch PhysiCell;
- change parameters;
- recalculate the transport solution;
- infer new biological meaning.

If a bundle is tampered with or violates its normalized scientific contracts, it is rejected before rendering.

The SVG renderer uses the same optional Matplotlib dependency as VesicleScope's other scientific figures and writes inspectable text labels for provenance and scientific status.
