# Evidence registry

The registry is intentionally human-readable in the architecture milestone. It will become machine-validated data when the package skeleton is introduced.

| ID | Type | Subject | Source | What it supports | What it does **not** support |
| --- | --- | --- | --- | --- | --- |
| EV-GUIDE-001 | consensus guideline | EV terminology/reporting | MISEV2023, DOI 10.1002/jev2.12404 | default EV terminology; explicit methods/controls; caution around subtype/function claims | a numeric transport or uptake parameter |
| EV-TRANSPORT-001 | primary experiment | ECM transport | Lenzini et al. 2020, DOI 10.1038/s41565-020-0636-2 | matrix mechanics/confinement can alter EV transport | a universal diffusion coefficient |
| EV-TRANSPORT-002 | primary experiment | matrix composition | https://pmc.ncbi.nlm.nih.gov/articles/PMC11080821/ | transport can differ by matrix composition and binding | behavior of every EV subtype/tissue |
| EV-UPTAKE-001 | review | uptake mechanisms | DOI 10.3402/jev.v3.24641 | uptake can occur through multiple routes and depend on EV/cell context | one universal uptake-rate constant |
| EV-UPTAKE-002 | review | recognition-to-cargo-release | PMID 39155778 | recipient-cell journey remains mechanistically complex/context dependent | equivalence of uptake and functional cargo delivery |
| STD-MIASE-001 | community standard | simulation reproducibility | https://sed-ml.org/ | experiment descriptions must contain enough information to reproduce simulations | that every VesicleScope engine can be losslessly exported to SED-ML |
| STD-COMBINE-001 | community standard | model packaging | https://co.mbine.org/standards/ | OMEX can package model/simulation/data/metadata artifacts | that COMBINE is the internal storage format |
| STD-PETAB-001 | community standard | parameter estimation | https://petab.readthedocs.io/en/latest/ | future calibrated models can use a standard parameter-estimation problem representation | that PEtab is required for v0.1 |
| STD-FAIR4RS-001 | community principles | research software | https://pmc.ncbi.nlm.nih.gov/articles/PMC9562067/ | versioning, metadata, provenance, identifiers, standards and clear licensing matter | an obligation to apply a permissive license |
| ENG-BIOFVM-001 | software/paper | continuum engine | DOI 10.1093/bioinformatics/btv730 | diffusion, decay, secretion/release and uptake are directly modeled | particle-level stochastic behavior |
| ENG-SMOLDYN-001 | software/docs | particle engine | https://www.smoldyn.org/ | particle diffusion/reaction/surface simulation in 1D/2D/3D | that its licensing can be ignored; exact release terms must be pinned |
| ENG-CC3D-001 | software/docs | multicellular engine | https://compucell3d.org/ | CPM cell behavior plus field solvers and headless execution | that CPM complexity is needed for v0.1 |
| ENG-MORPHEUS-001 | software/docs | multiscale engine | https://morpheus.gitlab.io/ | ODE/PDE/CPM multiscale modeling and declarative model files | that it is the narrowest transport baseline |

## Rule for future entries

A biologically meaningful numeric value must add at least:

- evidence ID;
- exact source and durable identifier when available;
- value and unit as reported;
- conversion, if any;
- biological system and preparation;
- measurement method;
- uncertainty/error information when reported;
- intended VesicleScope parameter;
- evidence class (`observed`, `literature`, `fitted`, `assumed`, or `synthetic`);
- limitations on transfer to other systems.

A source may justify the *existence* of a mechanism without justifying a parameter value for an unrelated experiment.
