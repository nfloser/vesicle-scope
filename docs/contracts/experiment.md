# Experiment contract

The JSON Schema in `experiment.schema.json` is the first machine-readable boundary for v0.1. It validates shape and basic units; semantic validation in code will later enforce cross-field rules.

## Required experiment information

Every v0.1 experiment states:

- stable experiment ID;
- schema version;
- model class;
- 2D domain dimensions;
- explicit slice thickness;
- boundary condition;
- duration and sampling cadence;
- diffusion coefficient;
- first-order degradation/loss rate;
- one or more donor release regions;
- one or more recipient uptake regions;
- engine name and version;
- provenance/evidence IDs for biologically meaningful parameters;
- deterministic seed for stochastic engines.

No numeric biological default is supplied by the schema.

## Evidence references

A parameter block contains:
- `value`;
- `unit`;
- `evidence_id`;
- `evidence_class`.

Allowed evidence classes are:
`observed`, `literature`, `fitted`, `assumed`, and `synthetic`.

`synthetic` is permitted for software/validation fixtures. It must never be silently promoted to biological evidence.

## Geometry

v0.1 deliberately uses simple circles inside a rectangular domain. This is enough to validate release, transport, loss, and uptake without importing microscopy segmentation or cell-shape dynamics prematurely.

A later geometry schema may reference masks or meshes, but that should be introduced only with a concrete experiment that requires it.

## Result contract direction

The first normalized result will eventually contain:

- grid coordinates in `um`;
- sampled time points in `min`;
- concentration field in `particle_equivalent/um^3`;
- integrated field amount;
- cumulative released amount where calculable;
- cumulative uptake amount where calculable;
- validation metrics;
- provenance block.

A particle engine may additionally expose trajectories or event data, but cross-engine comparison must rely on shared normalized quantities.
