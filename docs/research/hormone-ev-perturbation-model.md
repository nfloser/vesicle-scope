# Hormone/stimulus perturbation and EV phenotype model

Status: evidence/domain baseline for issue #98  
Reviewed: 2026-10-07

## Scientific question

How should VesicleScope represent a hormone or other biological stimulus,
EV subpopulations, marker profiles and cargo without pretending that one
context-specific experiment defines a universal EV response?

The model separates three concepts:

```text
declared exposure
      |
      v
reported biological effect
      |
      v
optional explicit model mapping
```

An exposure does not alter the transport engine by itself.

## Why the separation matters

Current evidence supports context-specific relationships between stress-related
signals and EV release/phenotype, but it does not support a universal rule such
as "cortisol increases EV release by X percent".

Examples include:

- glucocorticoid exposure increased CD63-associated small-EV release in a
  Neuro2a neuronal cell model and implicated nSMase2/Rab27a-associated
  machinery. The published study used dexamethasone in that model; it is not a
  universal human-blood cortisol calibration. PMID: 42059363.
- norepinephrine increased small-EV release and ACE cargo in rat adventitial
  fibroblasts in the reported vascular model. PMID: 35832088.
- human acute physical and psychosocial stress increased cortisol and
  catecholamines in both conditions, while marker-positive circulating sEV
  profiles differed by stress type and time. PMCID: PMC12511347.

The human study therefore supports longitudinal hormone/EV association and
marker dynamics, but by itself does not establish that each EV change is a
direct causal effect of one hormone.

## Exposure contract

`BiologicalExposure` records:

- stable exposure identifier;
- compound name;
- concentration as a provenance-bearing `ScientificParameter`;
- biological target compartment;
- explicit start/end time;
- evidence category/source;
- species/tissue/cell context when known;
- assumptions and limitations.

Supported target labels include whole blood, blood-cell populations, donor or
recipient cells, cell culture and isolated EV preparations. These labels record
what was exposed; they do not assert that every target can biologically produce
the same response.

For the intended blood experiment, release/biogenesis effects should normally
be attached to living blood/cell compartments before EV harvest. An exposure
of already isolated EVs is a different experiment, for example stability,
binding or uptake-related work, and must not silently become an EV-production
effect.

## EV phenotype contract

`EVPhenotype` represents one named EV subpopulation with explicit features.

Marker features can record states such as positive, negative or unresolved.
CD9, CD63 and CD81 can therefore be represented without declaring any one of
them a universal EV identity marker. Blood lineage/context markers such as
CD41, CD14, CD44, HLA-DR or others are equally representable when actually
measured.

Cargo features support proteins, mRNA, miRNA, other RNA, lipids, metabolites
and an explicit other class. Cargo may be quantitative when a real
provenance-bearing abundance exists or qualitative when the source only
supports statements such as increased/decreased.

MISEV2023 remains the terminology/characterization guardrail:
DOI 10.1002/jev2.12404.

## Effect contract

`PerturbationEffect` records the evidence-backed outcome separately from the
exposure. It stores:

- the exposure that preceded the observation;
- outcome class such as EV release, uptake, clearance, size, marker abundance
  or cargo abundance;
- direction (increase/decrease/no change/mixed/unknown);
- evidence source and context;
- optional EV phenotype/feature;
- optional quantitative magnitude;
- optional explicit model mapping.

A source can therefore support "release increased" even when no defensible
fold-change parameter is available. VesicleScope must preserve that state
instead of inventing one.

## Explicit model mapping

`ModelEffectMapping` is optional. The follow-up execution layer in issue #99
executes only explicit mappings to release rate, uptake rate or decay rate after
checking phenotype assignment, target identifier, operation, units and reported
effect direction. Marker/cargo and phenotype-fraction mappings remain
annotations.

When present it records:

- the model target (release rate, uptake rate, decay rate, phenotype fraction
  or cargo abundance);
- the operation (multiply/add/set);
- a provenance-bearing value;
- an optional target identifier.

Issue #99 implements that execution boundary using independently transported
EV populations and the existing verified BioFVM adapter. It does not infer a
response curve from hormone identity or concentration. See
[executable phenotype-specific perturbation transport](perturbation-transport-execution.md).

## Relationship to longitudinal blood measurements

The perturbation study can reference the measurement dataset identifiers
introduced by issue #101.

This allows the future workspace to connect:

```text
sample/timepoint
    |
    +--> measured particle concentration
    +--> marker-positive populations
    +--> cargo measurements
    +--> cortisol/catecholamine measurements
                 |
                 v
        perturbation evidence
                 |
                 v
        model prediction
```

Measured values are still not copied directly into transport parameters without
an explicit calibration/inference step.

## Product consequence

The eventual compare view can show at the same time:

- control vs stimulated condition;
- measured marker/count points;
- evidence-backed hormone/stimulus information;
- simulated EV population fields;
- per-population uptake/release trajectories;
- unknown effects as unknown rather than silently zero.

This is the scientific basis for the requested time sliders, graphs and visual
EV field without moving biological interpretation into the browser UI.
