# First reproducible synthetic population figure

Issue: #27  
Status: headless synthetic fixed-grid figure workflow

## Purpose

VesicleScope now has enough verified primary output to produce a scientific figure without reading BioFVM internals or reproducing its equations.

The first figure is intentionally narrow. It now visualizes the reviewed finite-recipient 2/4/8 count benchmark and demonstrates that normalized fields, declared recipient geometry and engine-independent population analysis can feed a reproducible scientific output.

It is **not** an experimental figure and it does not define a biological communication range.

## Shared scenario

The default figure uses the reviewed finite 2/4/8 recipient sweep defined in:

```text
vesiclescope.scenarios.finite_recipient_count_sweep_experiment
```

The historical point-sink factory remains available as `recipient_count_sweep_experiment` for reproducibility, but the primary SVG no longer uses it.

Native integration tests and figure generation call the finite factory.

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

Only the reviewed recipient population changes from 2 to 4 to 8 finite circular recipients.

Each displayed recipient has a declared 15 micron footprint radius. That radius is a synthetic verification input and is drawn directly from the experiment contract; it is not inferred from effective uptake volume or numerical grid spacing.

## Figure data boundary

`prepare_recipient_count_figure_data` accepts only:

- `TransportExperiment` objects;
- normalized `BioFVMRunResult` objects;
- immutable `RecipientPopulationSummary` objects.

It cross-checks scenario/result identity, recipient counts and ordering, final-time summaries, quantity units, aggregate uptake and spatial-field dimensions before rendering.

The heatmap uses the final normalized field of the finite 8-recipient scenario. Protocol ordering is `x_fastest_then_y`, so each y row is reconstructed from one contiguous `nx` span.

Figure data also carries the declared center and footprint radius for every displayed recipient. Point or mixed recipient geometry is rejected rather than silently rendered as finite geometry.

The count-sensitivity panel obtains both axes from analysis outputs:

```text
x = planar recipient density [recipient/mm^2]
y = total cumulative internalized quantity [explicit result unit]
```

No uptake value is duplicated as a plotting constant.

## Panels

The SVG contains:

1. the final extracellular concentration field for the finite 8-recipient scenario, with the donor point and eight circular recipient footprints overlaid;
2. total cumulative uptake versus planar recipient density for the finite 2/4/8 scenarios.

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

The generator runs the finite 2/4/8 scenarios at the reviewed 10 micron x/y grid, analyzes each final sample through the public analysis layer and then renders the SVG.

Issue #33 independently ran the same finite count sweep at 5 micron x/y resolution and preserved the qualitative `2 < 4 < 8` total-uptake ordering. The figure remains a 10 micron visualization; it does not hide or replace the refinement check.

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

The right-hand curve is the result of one deterministic synthetic finite-recipient arrangement at the displayed 10 micron numerical resolution.

Although recipient count and planar recipient density increase together in the fixed domain, angular occupancy around the donor also changes. The curve must therefore not be presented as an experimentally calibrated or arrangement-independent biological density-response relationship.

Finite-footprint uptake has separate rasterization and grid-refinement verification, but the displayed geometry and uptake parameters remain synthetic rather than experimentally calibrated.

The figure demonstrates a reproducible software/scientific-analysis pipeline, not biological validation.
