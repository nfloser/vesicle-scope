# Smoldyn particle-comparison research gate

**Issue:** #83  
**Review date:** 2026-10-05; upstream pin and license discrepancy rechecked 2026-10-06
**Upstream reviewed:** `ssandrews/Smoldyn` at commit `e21d6dd2c0411f5624b6da88c323597d6a92ee92`  
**Status:** scientific comparison plan defined; official 2.75 native candidate documented; distributed integration remains blocked

## Research question

VesicleScope eventually needs to answer whether a continuum representation and a discrete Brownian-particle representation make materially different predictions for the same transport experiment.

That comparison is useful only if the engines implement the same scientific problem. It must not compare two superficially similar demonstrations with different source, sink, geometry or boundary semantics.

Smoldyn is the leading particle-engine candidate because it is a maintained spatial stochastic simulator and its current upstream project documents a BioSimulators/SED-ML/COMBINE execution surface.

No Smoldyn code or runtime dependency is added by this research note.

## Upstream technical review

At the reviewed upstream commit:

- the CMake development fallback reports the line as `2.76.dev...`;
- Python installation is documented with `pip install smoldyn`;
- Smoldyn provides a BioSimulators-compliant interface;
- Smoldyn configuration files use SED-ML model language `urn:sedml:language:smoldyn`;
- its documented COMBINE media type is `http://purl.org/NET/mediatypes/text/smoldyn+plain`;
- Brownian diffusion / Smoluchowski simulation is identified with KiSAO `KISAO_0000057`;
- the BioSimulators layer exposes a random-seed algorithm parameter.

Reviewed upstream material:

- repository: https://github.com/ssandrews/Smoldyn
- SED-ML/COMBINE guidance: https://github.com/ssandrews/Smoldyn/blob/master/Using-Smoldyn-with-SED-ML-COMBINE-BioSimulators.md
- Python package metadata: `source/python/pyproject.toml.in`
- top-level build metadata: `CMakeLists.txt`

## Licensing gate

The reviewed upstream tree is internally inconsistent about the license that should govern a downstream integration.

Evidence for LGPL:

- current `source/python/pyproject.toml.in` declares `LGPL-3.0-or-later`;
- current CMake headers state that Smoldyn project files are licensed under LGPL;
- numerous core source headers explicitly say GNU Lesser General Public License;
- current BioSimulators container metadata identifies LGPL;
- historical `License.txt` text says the compiled version and Steve Andrews-owned source are distributed under LGPL.

Conflicting evidence:

- the current repository root `LICENSE` is the full GNU GPL v3 text;
- commit `83ef2f671aeb6d2d44a1f93fb7b1c14531ea7b5b` explicitly replaced the root LGPL v3 license text with GPL v3;
- nearby 2020 packaging commits removed an LGPL classifier while adding/updating the root license.

The later source/package metadata was not made consistent with that root-license change.

This ambiguity matters because VesicleScope intentionally does not currently grant an open-source license. Until the exact license applicable to a selected Smoldyn release/artifact is clarified, VesicleScope must not:

- vendor Smoldyn source or binaries;
- link Smoldyn into a VesicleScope-distributed binary;
- declare Smoldyn as a required or bundled runtime dependency;
- redistribute a Smoldyn wheel/container as part of VesicleScope.

This is a project licensing-risk record, not legal advice. An implementation release should obtain explicit upstream clarification and, where appropriate, legal review.

## First fair model-class benchmark

The first continuum-versus-particle comparison should use the already verified diffusion-only cosine benchmark, **not** the current donor/recipient uptake experiment.

Reason: the current BioFVM recipient implementation is an effective first-order sink coupled through an explicit effective volume. A naive Smoldyn absorbing circle/surface would represent a different microscopic mechanism. Comparing those outputs before deriving an equivalent sink mapping would confound engine class with model semantics.

The diffusion-only benchmark avoids that problem.

### Shared physical problem

Use the existing BioFVM analytical verification problem:

| Quantity | Shared value |
| --- | ---: |
| x length | 1000 micron |
| y width | 100 micron |
| diffusion coefficient | 1000 micron^2/min |
| duration | 60 min |
| boundary | reflecting / zero normal flux |
| baseline field | 1.0 normalized density |
| mode amplitude | 0.5 normalized density |
| initial profile | `1 + 0.5 cos(pi x / L)` |

The exact reference remains:

```text
c(x,t) = 1 + 0.5 cos(pi x/L) exp(-D (pi/L)^2 t)
```

This is mathematical verification only and has no EV-specific biological interpretation.

### Dimensional semantics

Smoldyn must run this first benchmark in **2D**, not in a 3D slab.

The BioFVM benchmark exercises x/y diffusion while the VesicleScope slice-thickness concept is used later to convert concentration fields to integrated physical amounts. Adding z diffusion to a Smoldyn slab would change the mathematical problem.

For this dimensionless diffusion benchmark, compare normalized 2D density rather than integrated particle-equivalent volume quantities.

### Initial particle representation

A particle simulator cannot represent the continuous cosine field exactly with a finite number of molecules.

For each stochastic realization:

1. sample initial x/y particle positions from the normalized target density;
2. record the exact random seed;
3. retain reflecting x/y boundaries;
4. evolve Brownian particles with the declared diffusion coefficient;
5. histogram the particle positions into the same 20-micron x/y analysis bins used by the reviewed continuum benchmark;
6. normalize histogram density so the domain mean is one.

The initialization method must be deterministic for a given seed and particle count.

Do not tune initial particle positions to make the final Smoldyn field resemble BioFVM.

## Required stochastic/numerical verification

A single seeded particle trajectory is not evidence of engine agreement.

The implementation gate requires:

### Particle-count convergence

Run an explicit increasing sequence of particle counts. The exact production counts should be selected from measured runtime/noise behavior, not invented in this note.

For each count report:

- number of seeds;
- mean field across seeds;
- standard deviation / sampling variability per spatial bin;
- relative L2 error of the ensemble-mean perturbation against the analytical solution;
- domain-mean conservation.

The expected behavior is decreasing sampling noise with increasing particle count. No monotonic per-seed error claim is required.

### Timestep sensitivity

Run at least one timestep refinement sequence for Smoldyn. Record the Brownian displacement scale relative to the spatial analysis scale.

Do not force Smoldyn and BioFVM to use identical numerical timesteps if their methods require different convergence settings. The comparison target is the same physical model after numerical convergence, not identical integrator internals.

### Seed reproducibility

Every stochastic run must persist:

- seed;
- particle count;
- Smoldyn version/commit or BioSimulators image identity;
- timestep and algorithm settings;
- exact VesicleScope revision;
- model/configuration digest.

Repeating a run with the same inputs and seed must reproduce its normalized output.

### Analytical comparison

For both engines compare the perturbation against the same analytical cosine solution.

Report separately:

- BioFVM discretization error;
- Smoldyn ensemble-mean error;
- Smoldyn sampling variability.

Do not subtract a single noisy Smoldyn realization from the BioFVM field and call that a model-class difference.

## Later release/uptake comparison gate

Only after diffusion-only equivalence is established should donor release and recipient uptake be considered.

Before that extension, define engine-neutral semantics for each mechanism.

### Release

The current VesicleScope finite donor declares one aggregate amount-per-time source distributed over a physical circular footprint.

A Smoldyn mapping must preserve:

- aggregate released amount per unit time;
- donor footprint;
- release timing;
- seed behavior of discrete particle creation;
- total mass/particle accounting.

The mapping must not infer secretion from donor area.

### Uptake

The current BioFVM finite recipient declares:

- physical 2D footprint;
- separate effective uptake volume;
- first-order uptake coefficient in `1/min`;
- cumulative internalized quantity.

An absorbing Smoldyn surface is not automatically equivalent.

A future gate must derive and verify a particle capture/reaction rule that corresponds to the intended macroscopic first-order sink, or explicitly define the two uptake models as different model classes and avoid claiming parameter equivalence.

### Decay

First-order extracellular decay can be represented stochastically as particle removal with the correct exponential survival law.

That mapping needs its own analytical survival verification before combined model comparison.

## Preferred integration boundary after licensing clarification

Technically, the cleanest current candidate is a **separate process boundary**, preferably via Smoldyn's documented BioSimulators/SED-ML interface or a user-installed executable/package.

Reasons:

- keeps the VesicleScope scientific core engine-independent;
- keeps Smoldyn-specific dependencies out of the mandatory Python core;
- makes the exact external simulator identity explicit;
- supports deterministic configuration/seed capture;
- aligns with the COMBINE/OMEX interoperability work already present in VesicleScope;
- avoids copying Smoldyn source into this repository.

This is not approval to distribute or depend on Smoldyn. The licensing gate remains prior to implementation.

## SED-ML opportunity

Unlike the current BioFVM path, Smoldyn already documents a recognized SED-ML model language and algorithm mapping.

If the particle adapter proceeds, the Smoldyn side can therefore be a useful first **genuine** SED-ML execution path in VesicleScope.

That must not be generalized into a claim that the existing VesicleScope BioFVM experiment is itself SED-ML portable.

A future comparison archive may legitimately contain:

- VesicleScope-native BioFVM experiment/run artifacts;
- a Smoldyn model;
- a SED-ML task for the Smoldyn model;
- provenance explaining the engine-neutral comparison mapping.

The two execution representations should remain explicit.

## Gate outcome

### Resolved

- candidate particle engine identified;
- current upstream commit reviewed;
- current technical SED-ML/BioSimulators support verified;
- first equivalent mathematical benchmark selected;
- 2D dimensional semantics selected;
- stochastic seed/particle-count/timestep validation plan defined;
- donor, uptake and decay semantic risks identified;
- preferred future process boundary identified.

### External blocker

The applicable Smoldyn distribution/license terms for the exact artifact VesicleScope would adopt are not internally consistent in the upstream repository.

No particle-engine implementation or redistribution should proceed until this is clarified.

Once that clarification exists, open a dedicated implementation issue for the diffusion-only particle adapter. Keep release/uptake comparison as a later research gate.


## Artifact-specific follow-up (2026-10-06)

The [official 2.75 archive review](smoldyn-2.75-license-review.md) supplies a verified archive hash and an express LGPL statement for the author-owned native core. It narrows the preferred candidate to a user-provided standalone native executable. The older development-tree conflict above remains applicable to that tree; Python/BioSimulators/container artifacts are not interchangeable with the reviewed native candidate. No dependency, adapter or redistribution is introduced. Bundling still requires exact build/component clearance.
