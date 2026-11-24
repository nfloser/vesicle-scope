# VesicleScope: vision, scope and feasibility

Status: concept of record, revised 2026-11-24

## Vision

VesicleScope is an open, evidence-grounded research platform for the computational study of extracellular vesicles (EVs): how cells release them, how they move through tissue and blood, which cells take them up, and how biological stimuli, especially hormones, change these processes and the EV populations themselves.

It connects experimental EV research with mathematical modelling, numerical simulation, data analysis and interactive visualisation. VesicleScope complements laboratory work. It does not replace it.

## Long-term ambition and an honest feasibility ladder

The long-term ambition is that, for well-characterised systems, questions that today need a new experiment can be answered computationally first. This is the role that molecular simulation and pharmacokinetic models (for example Simcyp or GastroPlus) play in drug development. Unlike quantum chemistry, EV biology cannot be derived from first principles. Rates, binding and hormone responses must be measured. Digital prediction therefore grows only as fast as calibrated evidence accumulates.

| Level | What VesicleScope can do | Requires | Status |
| --- | --- | --- | --- |
| 1. Explain | Show which mechanisms and parameters control a phenomenon; reject inconsistent hypotheses | Model structure + literature bounds | **Reached for transport range** (length-scale and cross-source synthesis) |
| 2. Plan | Choose the experiment that removes the most uncertainty (dose, time points, read-outs) | Uncertainty propagation over evidence ranges | Partly: dose-response scenarios exist, ensembles and sensitivity are next |
| 3. Predict within context | Quantitative prediction in a calibrated system with error bands | Raw data with replicates, fitted parameters | Blocked on data (Colombo raw data requested) |
| 4. Transfer | Predict a new tissue, hormone or species from shared mechanisms | Several calibrated systems + validated mechanism | Research goal |
| 5. Replace selected experiments | Use computation instead of a lab step for a defined question | Prospective validation track record | Long-term |

Each level is earned by evidence, never declared.

## Scientific focus

- Release, spatial spread, degradation, clearance and uptake of EVs under different biological and physical conditions.
- Hormonal stimulation: EV release, uptake, size, marker and cargo changes, time courses, dose and duration, and stimulated versus control groups.
- Population heterogeneity: subpopulations defined by size, markers (CD9, CD63, CD81, …), origin and cargo.
- Tissue geometry: cell density, donor–recipient distance, cell geometry, extracellular matrix and interstitial flow.

## What the evidence currently says (registry, 2026-11-24)

- **Transport range:** tumour EV signal implies a transport length of 17–25 µm. Free diffusion would need local capture 1.4–14× faster than mouse blood clearance. Hindered mobility or matrix binding is therefore the more economical explanation.
- **Missing mechanism:** at physiological interstitial flow, convection is comparable to or stronger than diffusion over that length. The transport model must gain advection and ECM binding next.
- **Geometry:** typical brain extracellular channels (38–64 nm) are narrower than small EVs (100–130 nm). Unhindered diffusion is not expected there.
- **Hormones:** release increases are reported for glucocorticoids, norepinephrine, histamine, androgens, estradiol, leptin, hypoxia (a non-hormonal stimulus) and physiological stress. Insulin, estradiol/progesterone, androgens and melatonin also change size or cargo. **No source yet gives a dose-response magnitude, and none reports an uptake effect.**
- **Human kinetics:** the only human circulation half-life is for transfused platelet microparticles (about 5–6 h). Mouse small EVs clear in 2–7 min. This roughly 45–175× discrepancy is itself an open question.

## Principles

1. Evidence-based: every biological number carries source, context, unit, evidence category and limitations.
2. Measured, literature-derived, inferred, fitted, assumed and simulated values are never mixed. Unknowns stay unknown.
3. Numerical correctness is verified separately from biological validity.
4. Results are conditional statements ("under model X with parameters Y …").
5. Established solvers are reused (BioFVM now; particle engines when licensing allows).
6. Reproducibility: run bundles with revision, solver settings and digests.
7. Local-first: research data stays on the researcher's machine. Windows is a first-class platform.

## Product scope

| Capability | State |
| --- | --- |
| Verified continuum transport engine (BioFVM) | done |
| Release, diffusion, decay, uptake; finite cell geometry; distance and density studies | done |
| Time-dependent release and uptake (rate schedules) | done |
| Hormone exposure → delayed dose-response → transport | done (parameters assumed until evidence exists) |
| Curated evidence registry with cross-source synthesis | done (46 records, 38 sources) |
| Import of longitudinal blood-EV measurements, phenotype and perturbation studies | done |
| Interactive workspace: experiments, runs, two-run comparison with independent time sliders | done |
| Evidence browser and hormone scenario editor in the UI | done |
| Advection and ECM binding | next |
| Uncertainty ensembles over evidence ranges; global sensitivity | next |
| Receptor-gated, population-specific hormone responses; marker dynamics | planned |
| Calibration against raw measurements (Colombo, own lab data) | blocked on data |
| Blood/systemic compartment coupled to tissue | planned |
| Particle-model comparison | blocked on licensing / engine choice |

## What VesicleScope is not

It is not a medical device or diagnostic tool, not a universal biology simulator, and not an animation of vesicles. It does not invent biological parameters, and it is not a substitute for laboratory experiments.

## Audience

Experimental EV researchers, computational biologists, endocrinology and flow-cytometry labs, EV analysis cores, and students. Users with deep biological knowledge should be able to run and interpret studies without writing simulation code.
