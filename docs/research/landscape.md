# Research landscape for the v0.1 transport baseline

Status: baseline research for issue #1  
Reviewed: 2026-09-30

## Scope

This document records the evidence that is allowed to shape the first VesicleScope model. It does **not** assign biological parameter values. Parameter values belong to experiments and require their own provenance.

The v0.1 question is deliberately narrow: model EV release from a donor region, extracellular transport, first-order loss, and uptake by a recipient region; then compare a continuum representation with a particle-based representation in regimes where both are meaningful.

## EV terminology and reporting

MISEV2023 is the current field-consensus baseline for EV terminology and reporting. It emphasizes that EV preparations are heterogeneous, that specific biogenesis labels such as "exosome" should not be used casually, and that experimental methods and controls must be described well enough to support the claimed interpretation.

VesicleScope therefore uses **EV** as the default model entity. A model may use a narrower subtype only when the experiment explicitly supplies evidence supporting that label.

Primary guidance:

- Welsh JA et al. *Minimal information for studies of extracellular vesicles (MISEV2023): From basic to advanced approaches*. Journal of Extracellular Vesicles. 2024;13:e12404. DOI: 10.1002/jev2.12404
- https://isevjournals.onlinelibrary.wiley.com/doi/10.1002/jev2.12404

Implication for software: model names and outputs must not imply a biogenesis pathway or biological function that the input evidence does not establish.

## Transport is not adequately described by particle size alone

Experimental work in engineered hydrogels shows that EV motion through extracellular-matrix-like environments can depend on matrix mechanics, confinement, and vesicle deformability rather than behaving as simple diffusion through a fixed pore network.

- Lenzini S et al. *Matrix mechanics and water permeation regulate extracellular vesicle transport*. Nature Nanotechnology. 2020. DOI: 10.1038/s41565-020-0636-2
- https://pubmed.ncbi.nlm.nih.gov/32066904/

More recent work on wound-derived microvesicles reports matrix-composition-dependent transport and specific binding to type-I collagen in that system.

- https://pmc.ncbi.nlm.nih.gov/articles/PMC11080821/

Implications:

1. A single constant diffusion coefficient is a **model assumption**, not a universal EV property.
2. The first homogeneous-diffusion benchmark is useful as a controlled baseline, not as a general description of tissue transport.
3. ECM-dependent diffusion, anomalous transport, binding/retention, and heterogeneous media belong to later model extensions after the simple benchmark is validated.
4. Any diffusion coefficient used in an experiment must state the EV preparation, medium/matrix, temperature if known, measurement method, and source.

## Uptake is heterogeneous

The literature describes multiple EV-recipient interaction and uptake routes, and current reviews continue to stress that recognition, internalization, trafficking, and cargo release remain context dependent.

- Mulcahy LA, Pink RC, Carter DRF. *Routes and mechanisms of extracellular vesicle uptake*. Journal of Extracellular Vesicles. 2014. DOI: 10.3402/jev.v3.24641
- https://pubmed.ncbi.nlm.nih.gov/25143819/
- Xiang H et al. *Extracellular vesicles' journey in recipient cells: from recognition to cargo release*. 2024. PMID: 39155778
- https://pubmed.ncbi.nlm.nih.gov/39155778/

Implications:

- v0.1 uses a coarse-grained uptake sink only.
- The uptake-rate parameter represents the experiment's chosen effective model, not a universal endocytosis constant.
- Binding, internalization, endosomal processing, cargo escape, and downstream phenotype are outside v0.1 unless explicitly modeled in later issues.
- "Delivered dose" means model-accounted EV amount entering the uptake sink, not proven functional cargo delivery.

## Reproducibility standards

### MIASE and SED-ML

MIASE defines minimum information needed to reproduce a simulation experiment. SED-ML is a machine-readable format designed to encode simulation setups that satisfy that reproducibility goal.

- https://sed-ml.org/
- Current specification listed by the project: SED-ML Level 1 Version 5

VesicleScope should make its internal experiment contract at least as explicit as MIASE even when a selected engine cannot be losslessly exported to SED-ML.

### COMBINE archives

COMBINE archives package models, simulation descriptions, data, and metadata in the OMEX format.

- https://co.mbine.org/standards/

Use them when the experiment can be represented without hiding VesicleScope-specific semantics.

### PEtab

PEtab standardizes parameter-estimation problems in systems biology. The current documentation distinguishes broadly supported PEtab 1.0 from PEtab 2.0, which expands beyond SBML-only model assumptions.

- https://petab.readthedocs.io/en/latest/

PEtab is not required for the first transport benchmark. It becomes relevant when VesicleScope begins fitting parameters against measurements.

### FAIR4RS

FAIR4RS adapts FAIR principles to research software and explicitly includes versioning, metadata, provenance, identifiers, standards, and licensing.

- Barker M et al. *Introducing the FAIR Principles for research software*. Scientific Data. 2022.
- https://pmc.ncbi.nlm.nih.gov/articles/PMC9562067/

VesicleScope can follow the technical FAIR4RS practices while still remaining public-without-an-open-source-license. FAIR does not require that every artifact be permissively licensed; the repository must simply describe its access and licensing state accurately.

## Candidate simulation engines

### BioFVM / PhysiCell

BioFVM solves reaction-diffusion transport with release/secretion, uptake, diffusion, and decay, and can run as a standalone transport solver. This is a direct match for the first continuum benchmark.

- Ghaffarizadeh A et al. *BioFVM: an efficient, parallelized diffusive transport solver for 3-D biological simulations*. Bioinformatics. 2016. DOI: 10.1093/bioinformatics/btv730
- https://pubmed.ncbi.nlm.nih.gov/26656933/
- https://physicell.org/Downloads.html

The BioFVM publication reports Apache-2.0 for BioFVM. The current PhysiCell project website states that PhysiCell is distributed under the 3-Clause BSD license. The exact engine version and license file must be pinned and recorded at integration time.

Strengths for v0.1:
- transport terms map closely to the benchmark;
- can be kept behind a headless adapter;
- established numerical implementation;
- avoids writing a bespoke PDE solver before one is needed.

Limitations:
- BioFVM is fundamentally a continuum transport solver;
- a 2D VesicleScope experiment needs an explicit slice-thickness convention when converting concentration to particle-equivalent counts;
- it cannot establish whether continuum assumptions remain valid at low copy number.

### Smoldyn

Smoldyn is a particle-based spatial stochastic simulator for diffusion, reactions, and surface interactions and supports true 1D/2D/3D simulations.

- https://www.smoldyn.org/
- https://www.smoldyn.org/simulators.html

Its project materials also describe SED-ML / COMBINE execution through a BioSimulators-compatible interface.

Licensing note: the official repository's project-specific `License.txt` states that core Smoldyn is distributed under the LGPL, while the repository also contains a `LICENSE` file containing GPLv3 text. This must be resolved against the exact release/package before distribution or tight linking. Until then, VesicleScope should prefer an external-process adapter boundary and must not vendor Smoldyn code.

Strengths for VesicleScope:
- natural particle-level reference;
- useful for low-copy-number and stochastic comparisons;
- supports surfaces and spatial reactions.

Deferred because:
- v0.1 first needs a validated continuum baseline and a shared result contract;
- a particle model requires additional decisions about particle radius, interactions, boundaries, and uptake semantics that should not be smuggled into the first milestone.

### CompuCell3D

CompuCell3D uses the Cellular Potts Model for cell behavior and also provides diffusion/reaction solvers and a GUI-less execution path.

- https://compucell3d.org/
- https://compucell3d.org/Manuals

It is a strong candidate when cell shape, motility, tissue morphology, and field coupling become central. Those capabilities are unnecessary for the v0.1 transport benchmark and would enlarge the state space before the simpler model is validated.

The project has reported MIT licensing for the CC3D core since the 4.3 series; the exact package and dependency licenses must still be checked when adopted.

### Morpheus

Morpheus combines ODEs, PDEs, and Cellular Potts models in 2D/3D and uses declarative MorpheusML.

- https://morpheus.gitlab.io/

The project states that its source is open under a BSD license. It is attractive for later reproducible multiscale tissue models and parameter scans, but is broader than required for the first transport benchmark.

## Baseline conclusion

The first engine adapter should target **BioFVM** for the continuum benchmark.

Smoldyn should be the first comparison adapter once the shared experiment/result contracts and continuum validation cases are stable.

CompuCell3D and Morpheus remain evaluated, documented options for later work involving explicit cell morphology, motility, or larger multiscale tissue models.

This is a scope decision, not a claim that one engine is universally superior.
