# External experiment execution and run inspection

VesicleScope supports a complete headless file-based workflow for model features already represented by the current `TransportExperiment` contract.

## Execute a validated experiment

Start from a reviewed experiment document or another document produced through the VesicleScope writer:

```bash
vesiclescope experiment run experiment.json \
  --runner build/native/biofvm_transport_runner \
  --revision "$(git rev-parse HEAD)" \
  --grid-spacing-micron 10 \
  --time-step-min 0.1 \
  --output run.json
```

Grid spacing and timestep are mandatory. VesicleScope does not silently insert numerical defaults into an external user run.

The command:

1. verifies and loads the experiment document;
2. constructs explicit BioFVM numerical settings;
3. runs through the existing pinned BioFVM adapter;
4. constructs the standard deterministic `SimulationRunBundle`;
5. writes and rereads the bundle to verify exact round-trip persistence.

The command does not introduce mechanisms beyond those already supported by the engine adapter.

## Inspect a completed run

```bash
vesiclescope run-bundle inspect run.json
```

Inspection verifies the bundle before displaying its contents. It reports the experiment identifier, exact VesicleScope revision, pinned engine identity, numerical settings, sample count, final extracellular/internalized quantities, source/sink counts and experiment evidence categories.

Inspection does not rerun the simulation and does not require Matplotlib.

## Compare two completed runs

```bash
vesiclescope run-bundle compare left.json right.json
```

The comparison reports:

- both experiment identifiers;
- both numerical settings;
- final extracellular quantity delta;
- final internalized quantity delta;
- right/left endpoint ratios when the left endpoint is nonzero.

Compatible quantity units are required. No result is labelled better, optimal, therapeutic or biologically superior. This is a numerical result comparison only.

## Scientific boundary

External execution makes the software more usable; it does not make arbitrary inputs biologically valid.

The experiment document remains responsible for explicit units and provenance. A synthetic value remains synthetic after execution. A completed run remains a conditional model prediction under its recorded experiment, numerical settings, engine and VesicleScope revision.
