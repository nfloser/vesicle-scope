# Initial research and software landscape

**Review date:** 2026-09-30  
**Scope:** evidence and software needed to choose the first VesicleScope transport model.  
**Status:** baseline review; parameter-level evidence review is intentionally deferred until a concrete model term is proposed.

## Research question

The first implementation should test a bounded, tissue-scale question:

> How do recipient-cell density, donor-recipient distance, EV release, extracellular transport and recipient uptake interact to determine the spatial communication range predicted by a continuum EV transport model?

This is a model question. It is not a claim that one continuum representation captures EV transport in every tissue.

## Terminology and reporting discipline

MISEV2023 is the primary nomenclature/reporting reference for EV work.

Reference:

- Welsh JA et al. *Minimal information for studies of extracellular vesicles (MISEV2023): From basic to advanced approaches.* Journal of Extracellular Vesicles. 2024;13:e12404. DOI: https://doi.org/10.1002/jev2.12404

Implementation consequences:

- use **extracellular vesicle (EV)** unless evidence supports a more specific biogenesis label;
- preserve experimental context such as source cells, species, preparation/separation method, size/fraction definition and measurement method;
- do not convert association into mechanism;
- do not treat one preparation or cell line as a universal EV parameter source.

## Evidence that motivates the first question

The literature does not support treating EV spatial range as a single universal number.

A recent study directly examined spatial limits of EV-mediated communication and reported that recipient-cell density can restrict dissemination through uptake/degradation, making cell density a first-class variable for the initial model.

- Colombo F, Nimkar K, Norton EG, Lovat F, Cocucci E. *Exploring the Spatial Limits of Extracellular Vesicles-Mediated Intercellular Communication.* Journal of Extracellular Vesicles. 2025;14:e70169. DOI: https://doi.org/10.1002/jev2.70169

Transport can also be strongly shaped by extracellular context. Experimental studies have reported matrix-dependent transport and, in a microfluidic interstitial-flow model, a dominant contribution from convection with ECM binding affecting spatial distributions.

- Lenzini S et al. *Matrix mechanics and water permeation regulate extracellular vesicle transport.* Nature Nanotechnology. 2020. DOI: https://doi.org/10.1038/s41565-020-0636-2
- *Convection and extracellular matrix binding control interstitial transport of extracellular vesicles.* PMID: 37073802. https://pubmed.ncbi.nlm.nih.gov/37073802/
- Arif S et al. *The diffusion of normal skin wound myofibroblast-derived microvesicles differs according to matrix composition.* Journal of Extracellular Biology. 2023. DOI: https://doi.org/10.1002/jex2.131

These findings are a reason to **defer**, not prematurely include, ECM binding and flow. The first baseline should isolate release, diffusion and uptake so later mechanisms can be added and tested against a verified reference.

## Existing EV transport models

There is precedent for continuum transport modeling of EVs in tissue-like environments.

- Koomullil R et al. *Computational Simulation of Exosome Transport in Tumor Microenvironment.* Frontiers in Medicine. 2021;8:643793. DOI: https://doi.org/10.3389/fmed.2021.643793

There is also precedent for stochastic reaction-diffusion treatment of vesicle-mediated communication in bacterial systems.

- *Stochastic effects in bacterial communication mediated by extracellular vesicles.* Physical Review E. 2023;107:024409. DOI: https://doi.org/10.1103/PhysRevE.107.024409

These studies support the project direction of comparing representation classes, but their biological contexts must not be silently generalized to the initial mammalian tissue-scale use case.

## Candidate simulation software

### BioFVM / PhysiCell

PhysiCell is an actively maintained multicellular simulation framework for 2D/3D tissues. BioFVM provides the extracellular diffusive-transport layer and supports source/sink coupling to agents. BioFVM exposes 2D problem access and simulation options, so a thin 2D transport baseline is feasible without writing a custom PDE solver.

Key references:

- Ghaffarizadeh A et al. *PhysiCell: an Open Source Physics-Based Cell Simulator for 3-D Multicellular Systems.* PLoS Computational Biology. 2018;14:e1005991. DOI: https://doi.org/10.1371/journal.pcbi.1005991
- Ghaffarizadeh A, Friedman SH, Macklin P. *BioFVM: an efficient parallelized diffusive transport solver for 3-D biological simulations.* Bioinformatics. 2016;32:1256-1258. DOI: https://doi.org/10.1093/bioinformatics/btv730
- Project: https://physicell.org/
- Source: https://github.com/MathCancer/PhysiCell

Current source carries a BSD 3-Clause license and explicit citation guidance.

**Fit for v0.1:** strong. It already provides diffusion/decay fields and agent source/sink behavior, which maps closely to the narrow transport baseline.

### CompuCell3D

CompuCell3D combines cell-based modeling with Python/C++ extension points and PDE fields. Its Cellular Potts representation is useful when cell shape, adhesion and lattice-based tissue dynamics are central.

- Swat MH et al. *Multi-Scale Modeling of Tissues Using CompuCell3D.* Methods in Cell Biology. 2012;110:325-366.
- Project: https://compucell3d.org/
- Source: https://github.com/CompuCell3D/CompuCell3D

**Fit for v0.1:** capable but broader than required. The first experiment does not yet need deformable-cell/CPM mechanics.

**License note:** exact current distribution terms must be verified from the release/source package before adoption; the top-level GitHub repository does not expose a simple root license file.

### Morpheus

Morpheus integrates ODE, PDE/reaction-diffusion and cell-based models with a model-oriented environment and supports SBML core.

- Starruß J et al. *Morpheus: a user-friendly modeling environment for multiscale and multicellular systems biology.* Bioinformatics. 2014;30:1331-1332.
- Project: https://morpheus.gitlab.io/

The project states that Morpheus is available under the 3-clause BSD license.

**Fit for v0.1:** scientifically capable, especially for rapid multiscale model definition, but the first VesicleScope milestone benefits from a small headless engine adapter and direct control over result/provenance contracts.

### Smoldyn

Smoldyn is a particle-based stochastic simulator for diffusion, reactions and surface interactions. It is a strong candidate for the later independent discrete representation.

- Andrews SS, Bray D. *Stochastic simulation of chemical reactions with spatial resolution and single molecule detail.* Physical Biology. 2004;1:137-151.
- Andrews SS et al. *Detailed simulations of cell biology with Smoldyn 2.1.* PLoS Computational Biology. 2010;6:e1000705.
- Project: https://www.smoldyn.org/
- Source: https://github.com/ssandrews/Smoldyn

Smoldyn also documents BioSimulators/SED-ML/COMBINE execution support.

**Fit for v0.1:** not as the primary continuum baseline; strong later comparison engine.

**License note:** the current GitHub repository contains a GPL-3.0 `LICENSE` file while the published/manual material has historically described LGPL licensing. This discrepancy must be resolved against the exact version adopted before integration or redistribution. Do not infer obligations from an older manual alone.

### Simple SciPy implementation

A small finite-difference implementation would be easy to understand but would make VesicleScope responsible for solver correctness, stability, boundary handling and performance that mature scientific software already addresses.

**Fit for v0.1:** useful only as an independent analytical/numerical reference where that makes validation clearer. It should not become the production solver merely because it is easy to code.

## Initial engine conclusion

Use **BioFVM as the first continuum transport engine**, behind a narrow VesicleScope adapter/runner.

Do not adopt the full PhysiCell behavioral stack unless the first real use cases require it. BioFVM already provides the part currently needed: diffusive fields plus source/sink coupling.

Reserve **Smoldyn** for the later model-class comparison milestone after the continuum baseline is verified and there is a concrete experiment that requires a discrete representation.

This is an engineering/modeling decision, not a claim that BioFVM is biologically more correct than the alternatives.

## Reproducibility standards

### MIASE

MIASE defines the minimum information needed to reproduce a simulation experiment. VesicleScope should use it as a design checklist even where the exact model type does not map cleanly to existing exchange formats.

### SED-ML

SED-ML encodes simulation experiment setups and is explicitly intended to support exchange and reproducibility.

- Specification: https://sed-ml.org/
- Current specification page: https://sed-ml.org/specifications.html

### COMBINE / OMEX

COMBINE archives package models, simulation experiment descriptions and associated files into a single reproducible archive.

- Specification: https://github.com/combine-org/combine-specifications/blob/main/specifications/omex.md

**Decision:** do not invent a large VesicleScope archive format yet. First define the minimal information the v0.1 runner actually needs; map it against MIASE/SED-ML/OMEX and document any gaps.

### PEtab

PEtab standardizes parameter-estimation problems around model, measurements, observables, noise models, conditions and parameter bounds.

- Specification/source: https://github.com/PEtab-dev/PEtab

**Decision:** no calibration layer exists yet. Evaluate PEtab when the first real fitting problem is introduced rather than inventing a custom calibration format now.

### FAIR4RS

FAIR4RS provides community principles for findable, accessible, interoperable and reusable research software.

- Chue Hong NP et al. *FAIR Principles for Research Software (FAIR4RS Principles).* 2022. DOI: https://doi.org/10.15497/RDA00068
- Katz DS et al. *Introducing the FAIR Principles for research software.* Scientific Data. 2022. DOI: https://doi.org/10.1038/s41597-022-01710-x

The public repository can follow FAIR4RS metadata/version/provenance practices without implying that VesicleScope itself is open-source licensed.

## Parameter evidence still missing

No biological numerical default is approved by this document.

Before implementation, separate evidence notes are still required for any proposed numerical value or distribution for:

- EV release rate;
- effective diffusivity in the chosen experimental context;
- extracellular degradation/clearance;
- recipient uptake kinetics;
- cell density/geometry;
- simulation duration and spatial scale when presented as biologically motivated rather than synthetic.

Synthetic benchmark values may be used for solver verification only when clearly labeled as synthetic and dimensionally consistent.

## Open research questions

1. Which experimentally tractable context should anchor the first biologically parameterized demonstration after the synthetic verification benchmark?
2. Is linear uptake sufficient for the first identified dataset, or does the evidence require saturation/other kinetics?
3. Which observable best defines "communication range" for v0.1: concentration threshold, cumulative exposure, uptake, or a family of metrics?
4. Which parts of the v0.1 experiment contract can be represented directly in SED-ML/OMEX without inventing VesicleScope-specific semantics?
5. Which exact Smoldyn release/license combination is appropriate if the particle comparison proceeds?
