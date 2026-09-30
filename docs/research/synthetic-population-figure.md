# First reproducible synthetic population figure

Issue: #27  
Status: headless synthetic fixed-grid figure workflow

## Purpose

VesicleScope now has enough verified primary output to produce a scientific figure without reading BioFVM internals or reproducing its equations.

The first figure is intentionally narrow. It visualizes the already reviewed synthetic recipient-count benchmark and demonstrates that normalized fields and engine-independent population analysis can feed a reproducible scientific output.

It is **not** an experimental figure and it does not define a biological communication range.

## Shared scenario

The reviewed 2/4/8 recipient sweep is defined once in:

```text
vesiclescope.scenarios.recipient_count_sweep_experiment
```

Native integration tests and figure generation both call this factory.

Across all three scenarios the following remain fixed:

- 210 × 210 micron x/y domain;
- 25 micron physical slice thickness;
- centered donor;
- 50 micron donor-recipient radius;
- release rate;
- diffusion coefficient;
- zero extracellular decay;
- recipient uptake coefficient;
- effective recipient volume;
- 10 micron numerical x/y grid;
- 0.1 min timestep;
- 20 min duration.

Only the reviewed recipient population changes from 2 to 4 to 8 point recipients.

## Figure data boundary

`prepare_recipient_count_figure_data` accepts only:

- `TransportExperiment` objects;
- normalized `BioFVMRunResult` objects;
- immutable `RecipientPopulationSummary` objects.

It cross-checks scenario/result identity, recipient counts and ordering, final-time summaries, quantity units, aggregate uptake and spatial-field dimensions before rendering.

The heatmap uses the final normalized field of the 8-recipient scenario. Protocol ordering is `x_fastest_then_y`, so each y row is reconstructed from one contiguous `nx` span.

The count-sensitivity panel obtains both axes from analysis outputs:

```text
x = planar recipient density [recipient/mm^2]
y = total cumulative internalized quantity [explicit result unit]
```

No uptake value is duplicated as a plotting constant.

## Panels

The SVG contains:

1. the final extracellular concentration field for the 8-recipient scenario, with donor and recipient positions overlaid;
2. total cumulative uptake versus planar recipient density for the 2/4/8 scenarios.

The figure carries the explicit title:

```text
Synthetic fixed-grid verification
```

and states that the benchmark is not experimental evidence.

No threshold or biological communication-range label is shown.

## Renderer

Matplotlib 3.11.2 is the reviewed optional figure renderer.

The renderer:

- is imported lazily only when figure generation is requested;
- forces the non-interactive `Agg` backend;
- writes SVG;
- fixes the SVG hash salt for stable element identifiers;
- keeps text as SVG text so units and scientific-status labels remain inspectable;
- supplies deterministic metadata rather than a generation timestamp.

The dependency pin and licensing record are in `requirements-figures.txt` and `THIRD_PARTY.md`.

## Reproduce locally

From the repository root:

```bash
python -m pip install -r requirements-figures.txt
bash scripts/fetch-physicell.sh
make -f native/biofvm_benchmark/Makefile runner
python -m scripts.generate_population_figure \
  --runner build/native/biofvm_transport_runner \
  --output build/figures/recipient-count.svg
```

The generator runs the same 2/4/8 scenarios, analyzes each final sample through the public analysis layer and then renders the SVG.

It fails clearly if the native runner is missing.

## CI

Core unit tests still run without Matplotlib.

A dedicated `population-figure` job:

1. installs the pinned figure dependency;
2. fetches the pinned PhysiCell/BioFVM source;
3. builds the native runner;
4. executes a native end-to-end render test;
5. generates `build/figures/recipient-count.svg`;
6. verifies inspectable synthetic/unit labels;
7. uploads the SVG as the `vesiclescope-synthetic-population-figure` workflow artifact.

## Interpretation limit

The right-hand curve is the result of one deterministic synthetic spatial arrangement at one numerical resolution.

Although recipient count and planar recipient density increase together in the fixed domain, angular occupancy around the donor also changes. The curve must therefore not be presented as an experimentally calibrated or arrangement-independent biological density-response relationship.

Point-recipient uptake also retains the documented `V_agent / V_voxel` dependence.

The figure demonstrates a reproducible software/scientific-analysis pipeline, not biological validation.
