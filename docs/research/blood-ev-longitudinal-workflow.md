# Blood-derived EV longitudinal measurement workflow

Status: measured-data contract baseline for issue #101  
Reviewed: 2026-10-07

## Product question

VesicleScope should connect a real blood/plasma extracellular-vesicle (EV)
measurement workflow to reproducible simulation without collapsing assay output
into biological truth or solver parameters.

The intended product path is:

```text
blood collection / biological condition
        |
        v
documented plasma or serum pre-analytics
        |
        v
particle + EV-associated measurements at explicit time points
        |
        v
marker / cargo phenotyping
        |
        v
longitudinal measured dataset
        |
        +--> measured-data plots
        |
        +--> explicit calibration / validation boundary
                       |
                       v
                  simulation
                       |
                       v
        model-vs-measurement comparison
```

The simulator and the assay layer remain separate scientific boundaries.

## Why blood pre-analytics are first-class data

MISEV2023 specifically warns that blood-derived EV studies are sensitive to
platelet activation, residual platelets, haemolysis, lipoproteins and other
non-vesicular extracellular particles. Platelets overlap EVs in relevant size
and density ranges and can release large numbers of EVs when activated.

VesicleScope therefore records the biological matrix, anticoagulant when
plasma is used, collection-to-processing delay, each declared centrifugation
step, residual platelet count when measured, haemolysis assessment when
available and explicit limitations.

A longitudinal dataset may contain multiple blood/plasma samples. Every
measurement time point references its exact sample identifier so a baseline
draw, post-stimulation draw or ex-vivo aliquot does not silently inherit the
identity of another specimen. Relative time may be negative when a measurement
precedes the declared stimulation reference.

This is not a prescribed clinical or laboratory protocol. It is a provenance
contract for recording the protocol actually used.

Primary guidance:

- Welsh JA et al. Minimal information for studies of extracellular vesicles
  (MISEV2023). Journal of Extracellular Vesicles. 2024;13:e12404.
  DOI: 10.1002/jev2.12404.
- Bracht JWP et al. Removal of platelets from blood plasma to improve the
  quality of extracellular vesicle research. Journal of Thrombosis and
  Haemostasis. 2022. PMID: 36043239.

## A particle count is not automatically an EV count

Scatter-mode nanoparticle tracking analysis (NTA) can report particle
concentration and size distributions, but particles with EV-like size can
include lipoproteins and other non-EV material. VesicleScope therefore stores
particle concentration separately from EV-associated or marker-positive event
concentrations.

The measurement contract records:

- what quantity was observed;
- its unit;
- the assay method;
- the exact detection/gating/capture semantics;
- markers used to define the event, when applicable;
- technical replicate count and standard deviation when available.

No conversion from `particle/mL` to `EV/mL` occurs implicitly.

Method-comparison evidence:

- Bachurski D et al. Extracellular vesicle measurements with nanoparticle
  tracking analysis. Journal of Extracellular Vesicles. 2019.
  PMID: 30988894.

## Marker panels are phenotypes, not universal identity labels

CD9, CD63 and CD81 are useful EV-associated tetraspanins, but VesicleScope does
not require every EV to express them and does not use a single positive marker
as proof of a universal EV class.

The assay contract supports one or more markers per observation so it can
represent, for example:

- CD9-positive events;
- CD63-positive events;
- CD81-positive events;
- CD9/CD63 co-positive events;
- lineage-associated panels such as CD41a-bearing platelet-associated EV
  events when that assay has measured them.

Single-vesicle work has demonstrated that plasma EV-associated populations can
be resolved by combinations of CD9/CD63/CD81 and lineage-associated markers,
and that their abundance depends on the assay and sample context.

Examples:

- Brahmer A et al. Single vesicle analysis reveals the release of tetraspanin
  positive extracellular vesicles into circulation with high intensity
  intermittent exercise. PMID: 36855276.
- Saftics A et al. Single Extracellular VEsicle Nanoscopy. Journal of
  Extracellular Vesicles. 2023. DOI: 10.1002/jev2.12346.

## Longitudinal stimulation experiments

A stimulation experiment must identify the biologically responsive system.
Cortisol/glucocorticoids or catecholamines are not assumed to reprogram an
already isolated inert EV preparation. The intended causal model is instead
that a stimulus acts on living donor cells, blood-cell populations or another
explicit biological compartment, after which EV release and phenotype are
measured.

Human acute-stress work demonstrates why VesicleScope must preserve explicit
time points rather than only before/after labels. One study measured plasma
sEV-associated markers before stress and at 2, 15, 30 and 40 minutes after the
challenge. Cortisol and catecholamines increased under both physical and
psychosocial stress, while the EV response differed by stress type and marker.

- Stress type-specific small extracellular vesicle signatures reflect
  divergent biological responses to acute psychosocial and physical
  challenges. 2025. PMCID: PMC12511347.

Mechanistic studies are also context specific:

- glucocorticoids increased CD63-associated sEV release in a neuronal cell
  model through nSMase2/Rab27a-associated biology; PMID: 42059363;
- norepinephrine increased small-EV release and ACE cargo in rat adventitial
  fibroblasts in the reported vascular model; PMID: 35832088.

These findings justify modelling perturbations. They do not justify one
universal cortisol or adrenaline multiplier for human blood EVs.

## VesicleScope v1 measurement contract

`vesiclescope.domain.measurements` introduces immutable records for:

- `BloodEVPreanalytics`;
- `CentrifugationStep`;
- `AssayObservation`;
- `MeasurementTimepoint`;
- `LongitudinalEVDataset`.

`vesiclescope.measurement_files` provides deterministic,
integrity-protected JSON documents.

The measurement data are deliberately not `ScientificParameter` objects.
Turning an observation into a fitted or inferred model parameter requires a
future explicit calibration step with its own provenance.

## Planned product view

The workspace should eventually show four linked views of the same experiment:

1. **Sample / assay provenance** — blood matrix, pre-analytics, assay method and
   quality/context warnings.
2. **Measured time series** — particle concentration, marker-defined event
   counts, marker/cargo signals and uncertainty.
3. **Model prediction** — simulated EV populations, release, transport and
   uptake.
4. **Compare view** — control versus stimulus with independent time sliders,
   measured points overlaid on model curves and the corresponding spatial EV
   visualization at each selected time.

A visual difference must remain traceable to either a measured observation or
an explicitly modelled effect. Missing evidence is displayed as unknown; it is
not silently filled in.
