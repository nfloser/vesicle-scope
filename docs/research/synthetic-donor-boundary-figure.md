# Synthetic donor-boundary profile figure

Issue: #43  
Status: reproducible synthetic spatial/radial figure

## Purpose

This figure turns the verified finite-donor geometry and donor-boundary radial analysis into one inspectable research-software output.

It is designed to show two things at once:

1. the simulated extracellular field in physical x/y space;
2. how the **same normalized field** looks when summarized with the two radial bin definitions currently relevant to the Colombo 2025 validation target.

The figure is synthetic verification output. It is not experimental evidence and it does not claim quantitative agreement with Colombo et al.

## Reviewed scenario

The generator uses:

```text
vesiclescope.scenarios.finite_donor_boundary_figure_experiment
```

The scenario is intentionally source-only so transport and boundary geometry remain interpretable.

It uses:

- 240 × 240 micron x/y domain;
- 25 micron physical slice thickness;
- circular donor centered at (120, 120) micron;
- 15 micron donor footprint radius;
- 20 min duration;
- 5 min requested output interval;
- 100 micron^2/min diffusion coefficient;
- zero extracellular decay;
- zero initial extracellular concentration;
- 120 particle_equivalent/min aggregate release;
- no uptake recipients.

Every biological-looking parameter above is marked `synthetic_benchmark` in the experiment contract. The donor radius is **not** a HeLa radius and the transport values are not Colombo tumour parameters.

The rendered run uses:

- 5 micron x/y numerical grid;
- 0.1 min timestep;
- pinned PhysiCell/BioFVM engine metadata.

## Panel 1 — spatial field

The left panel shows the final normalized extracellular concentration field.

It overlays:

- the declared finite circular donor boundary;
- boundary-offset rings at 20, 40, 60 and 80 micron.

Each ring radius is calculated as:

```text
physical donor radius + boundary offset
```

The rings are analysis geometry, not reported biological communication ranges.

The concentration colorbar uses the normalized field unit:

```text
particle_equivalent/micron^3
```

## Panel 2 — radial profiles

The right panel derives mean simulated concentration from the same final field twice:

- 5 micron bins — matching the currently reviewed public Colombo analysis code;
- 10 micron zones — matching the published Methods description.

The two curves are not separate simulations.

They are alternate summaries of the same normalized field and exist specifically so the documented 5-versus-10-micron discrepancy remains visible.

No Colombo experimental data, fitted retention landmarks or fluorescence threshold is plotted.

## Boundary discretization

Spatial membership remains based on **voxel centers**.

For one voxel center:

```text
d_boundary = distance(center, donor_center) - donor_radius
```

Centers at or inside the declared donor boundary are excluded from the extracellular radial profile and remain separately accounted for by the analysis layer.

The renderer does not perform partial voxel-circle overlap or sub-voxel image segmentation.

That matters: the figure demonstrates a reproducible model-space observable, not pixel-exact recreation of microscopy segmentation.

## Measurement limit

The simulation field represents model concentration.

Colombo et al. analyze thresholded CD9-Halo-associated fluorescence.

VesicleScope has not established a validated mapping between those observables.

Accordingly, the figure visibly states:

```text
simulated concentration, not experimental evidence
```

and must not be presented as experimental validation.

## Reproduce locally

From the repository root:

```bash
python -m pip install -r requirements-figures.txt
bash scripts/fetch-physicell.sh
make -f native/biofvm_benchmark/Makefile runner
python -m scripts.generate_donor_boundary_figure \
  --runner build/native/biofvm_transport_runner \
  --output build/figures/donor-boundary-profile.svg
```

The generator fails clearly when the native runner is unavailable.

## CI

The existing figure workflow is extended rather than adding another expensive job.

It:

1. installs the existing pinned Matplotlib dependency;
2. fetches pinned PhysiCell/BioFVM;
3. builds the native runner;
4. runs both population and donor-boundary headless render tests;
5. generates both reviewed SVGs;
6. verifies inspectable scientific-status and unit labels;
7. uploads the donor-boundary SVG as a dedicated workflow artifact.

## Interpretation

The useful result is not that one of the two bin widths is “correct”.

The figure demonstrates that an analysis choice can visibly change the discretized radial representation even when the underlying simulation field is identical.

That distinction is exactly why VesicleScope preserves the paper/public-code discrepancy instead of silently normalizing it.
