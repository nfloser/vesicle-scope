# EV evidence registry

Issue: #146
Status: first curated release (20 sources, 25 records, checked 2026-11-24)

## Purpose

VesicleScope needs biological numbers and effect directions that are traceable
to a source, carry their context and say what they do **not** show. The
registry is the single place for them. It replaces numbers scattered across
research notes with records that code can query, convert into
`ScientificParameter`s and combine.

## Structure

- `vesiclescope/evidence/data/sources.json`: bibliographic identity (DOI,
  PMID, PMCID or URL) and peer-review status.
- `vesiclescope/evidence/data/records.json`: the records.
  - **quantity**: value or range, unit, evidence category, context, locator,
    verification level, paraphrased statement, limitations, tags.
  - **effect**: stimulus, outcome (`EffectOutcome`), direction
    (`EffectDirection`), optional magnitude and time course, mechanism,
    context.
- `vesiclescope.evidence`: loader with validation, query API, conversion to
  `ScientificParameter`, and a derived SQLite export.

The JSON files are the reviewable source of truth. SQLite is generated on
demand (`vesiclescope evidence export-sqlite`).

Validation rejects:

- unknown or missing sources;
- duplicate ids;
- unknown context fields;
- a source without any durable identifier;
- a preprint that is not labelled as such in the record's limitations.

## Rules for adding a record

1. Open the source and verify the number against it. A search snippet of the
   abstract counts as `verification: abstract`. A secondary citation must say
   so and should name the reviewing source in `secondary_sources`.
2. Paraphrase. Never copy text, tables or figures.
3. Choose the evidence category honestly. Model-derived estimates are
   `inferred`, not measured.
4. Record species, cell line or tissue, preparation and method. Cross-context
   use is a modelling decision made elsewhere, not in the record.
5. Record at least one limitation.

## Current contents

| Area | Records | Main sources |
| --- | --- | --- |
| Release / secretion | 4 quantities | Auber 2022 (human blood estimates), Matsumoto 2020 (mouse PK) |
| Blood clearance | 2 quantities, 1 effect | Takahashi 2013 (~2 min), Matsumoto 2020 (~7 min), macrophage dependence |
| Uptake / delivery | 3 quantities | Bonsergent 2021 (~1% at 1 h; 27% cytosolic delivery), Jurgielewicz 2020 |
| Transport / tissue | 2 quantities, 1 effect | Colombo 2025, Sariano 2023 (flow 0.15–0.75 µm/s), Lenzini 2020 |
| Blood concentration / size | 3 quantities | NTA reference interval, literature range, exercise sEV size |
| Hormones and physiological stimuli | 8 effects | glucocorticoids, norepinephrine, physical/psychosocial stress, exercise, insulin (3), estradiol/progesterone |

Evidence categories: 14 measured in related context, 4 measured in target
context, 4 inferred, 3 literature estimates.

## First cross-source result

`vesiclescope evidence synthesize` combines four independent records:

```text
EV diameter 100-130 nm -> free diffusion 303-394 um^2/min (upper bound).
Tumour length scale lambda = 16.8-24.7 um.
At free diffusion this needs local loss k_eff = 0.50-1.40 /min (1/k = 0.7-2.0 min).
Whole-body blood clearance from half-lives: 0.10-0.35 /min; required local loss is 1.4-14.2x that.
Interstitial flow 9-45 um/min gives Pe = 0.38-3.66 at free diffusion; convection dominates (Pe > 1) once D < 151-1110 um^2/min.
```

Interpretation, conditional on the steady-state linear model:

1. **Free diffusion is implausible in tumour tissue.** It would require local
   EV loss 1.4–14× faster than the macrophage-dominated clearance of EVs from
   mouse blood. Hindered mobility or matrix binding, both documented
   experimentally (Lenzini 2020; Sariano 2023), is the more economical
   explanation for the short observed reach.
2. **The current transport model is missing convection.** Even at free
   diffusion, the Péclet number over one length scale reaches about 3.7 at the
   upper physiological interstitial flow. For any hindered diffusion below
   about 150 µm²/min, convection dominates at all flows in the range. This
   matches the conclusion of Sariano 2023 and makes advection plus ECM binding
   the next transport extension with the strongest evidence behind it.
3. **Hormone timing is compatible with fast blood turnover.** A rise in
   circulating sEVs with return to baseline within 40 min (physical stress) or
   90 min (exercise) is consistent with mouse blood half-lives of 2–7 min. The
   observed decay therefore probably tracks the stimulus rather than EV
   clearance. This is an interpretation, not a fitted result.

## Gaps the registry makes visible

- No tissue-specific EV diffusion coefficient (only hydrogel mechanics and
  mucus MSD, which is not mappable; see `measured-mucus-audit.md`).
- No cell-intrinsic uptake rate constant. Culture uptake fractions depend on
  dose and well geometry.
- No human EV circulation half-life.
- Hormone effects are directions in cell lines, or associations in humans. No
  dose–response magnitude exists for any hormone, so the dose-response layer
  must keep using ranges or synthetic values.

## Commands

```bash
vesiclescope evidence list [--quantity Q] [--stimulus S] [--tag T]
vesiclescope evidence show <record-id>
vesiclescope evidence export-sqlite --output evidence.db
vesiclescope evidence synthesize
```
