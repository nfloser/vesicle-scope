# EV evidence registry

Issue: #146
Status: curated release 2 (38 sources, 46 records, checked 2026-11-24)

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
| Hormones and physiological stimuli | 17 effects | glucocorticoids, norepinephrine, histamine, physical/psychosocial stress, exercise, insulin (3), estradiol (3), androgens (2), leptin, melatonin, pregnancy (2) |
| Other stimuli and conditions | 5 effects | hypoxia (HIF-1α), circadian time of day (3), integrin inhibition |
| Human blood kinetics | 2 quantities | transfused platelet microparticles, half-life 5.3–5.8 h (Rank 2011) |
| Tissue geometry and flow | 4 quantities | interstitial flow 0.6 µm/s measured in tissue, albumin interstitial D, brain ECS volume fraction 0.2 and width 38–64 nm |
| Biogenesis | 1 quantity | about 200 CD63+ MVBs per HeLa cell (Verweij 2018) |

Evidence categories: 27 measured in related context, 11 measured in target
context, 5 inferred, 3 literature estimates.

## First cross-source result

`vesiclescope evidence synthesize` combines independent records (release 2 adds human kinetics, in-tissue flow and brain geometry):

```text
EV diameter 100-130 nm -> free diffusion 303-394 um^2/min (upper bound).
Tumour length scale lambda = 16.8-24.7 um.
At free diffusion this needs local loss k_eff = 0.50-1.40 /min (1/k = 0.7-2.0 min).
Mouse small-EV blood clearance: 0.10-0.35 /min; required local loss is 1.4-14.2x that.
Human platelet-microparticle clearance: 0.0020-0.0022 /min; required local loss is 229-704x that.
Interstitial flow 9-45 um/min gives Pe = 0.38-3.66 at free diffusion; convection dominates (Pe > 1) once D < 151-1110 um^2/min.
Measured tissue flow 36 um/min gives Pe = 1.53-2.93 at free diffusion.
Brain extracellular space width 38-64 nm vs EV diameter 100-130 nm: EVs exceed the typical channel width, so unhindered diffusion is not expected there.
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
3. **The in-tissue flow measurement confirms point 2.** At 0.6 µm/s, Pe is 1.5–2.9 even at free diffusion.
4. **Brain geometry excludes free diffusion of small EVs.** The typical channel width is smaller than the EV diameter.
5. **Species and EV type matter for clearance.** Human platelet microparticles persist for hours, mouse small EVs for minutes. Any systemic model must keep these apart.
6. **Hormone timing is compatible with fast blood turnover.** A rise in
   circulating sEVs with return to baseline within 40 min (physical stress) or
   90 min (exercise) is consistent with mouse blood half-lives of 2–7 min. The
   observed decay therefore probably tracks the stimulus rather than EV
   clearance. This is an interpretation, not a fitted result.

## Gaps the registry makes visible

- No tissue-specific EV diffusion coefficient (only hydrogel mechanics and
  mucus MSD, which is not mappable; see `measured-mucus-audit.md`).
- No cell-intrinsic uptake rate constant. Culture uptake fractions depend on
  dose and well geometry.
- No human small-EV circulation half-life (only platelet microparticles).
- No uptake effect of any hormone (the evidence map's uptake column is empty).
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
