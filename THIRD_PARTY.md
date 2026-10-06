# Third-party software record

VesicleScope source is public but does not currently grant an open-source license for its own code. Third-party software retains its own license and citation requirements.

## BioFVM / PhysiCell

**Use:** continuum diffusion engine for the first numerical verification benchmark  
**Distribution:** fetched during build/test; not vendored into this repository  
**PhysiCell release:** 1.14.2  
**Pinned commit:** `dbd3499250141b27600e91e501c54c46f68f2763`  
**BioFVM version reported by pinned source:** 1.1.7  
**Upstream:** https://github.com/MathCancer/PhysiCell  
**License:** BSD 3-Clause in the pinned BioFVM source

Scientific citation:

Ghaffarizadeh A, Friedman SH, Macklin P. *BioFVM: an efficient parallelized diffusive transport solver for 3-D biological simulations.* Bioinformatics. 2016;32(8):1256-1258. DOI: https://doi.org/10.1093/bioinformatics/btv730

The upstream copyright and license text must be preserved if BioFVM source or binaries are redistributed in a way that triggers those conditions. VesicleScope's current verification workflow downloads upstream source for CI compilation and does not copy it into this repository.


The canonical reviewed pin used by the fetch script, native build and Python adapter is stored in `vesiclescope/engines/physicell.env`. The fetch step verifies both the Git commit and the BioFVM version declared by the pinned source before compilation.


## Matplotlib

**Use:** headless rendering of reproducible scientific figures from normalized VesicleScope results  
**Distribution:** installed as an optional figure-generation dependency; not vendored into this repository  
**Pinned version:** 3.11.2  
**Upstream:** https://matplotlib.org/ and https://pypi.org/project/matplotlib/  
**License:** Matplotlib License / Python Software Foundation based, BSD-compatible

Matplotlib is confined to the visualization layer. Numerical engines, scientific domain contracts, result parsing and engine-independent analysis do not import or depend on Matplotlib.

The figure workflow pins the reviewed version in `requirements-figures.txt` so CI and local figure generation use the same renderer version.


## CocucciLab spatial-limits-of-extracellular-vesicles

- Purpose in VesicleScope: external analysis-method reference for the Colombo et al. 2025 tumour-distance validation target; not a runtime dependency and not vendored.
- Repository: `CocucciLab/spatial-limits-of-extracellular-vesicles`
- Reviewed commit: `ed9e28173929c9f896d16658781d7a4b9cc2297c`
- Reviewed analysis file: `in vivo/distTraAnalysis.py`
- Reviewed file/blob SHA: `16744cd7d0eb0271ce5a8c3949b84e7cb86d8933`
- License: MIT
- Publication: Colombo et al. 2025, DOI `10.1002/jev2.70169`

VesicleScope records this pin to identify the public analysis semantics reviewed for external validation. No upstream source code is copied into the VesicleScope runtime.


## Smoldyn (candidate; not a dependency)

**Status:** research candidate for future continuum-versus-particle comparison; not installed, linked, vendored or redistributed by VesicleScope  
**Upstream:** https://github.com/ssandrews/Smoldyn  
**Reviewed commit:** `e21d6dd2c0411f5624b6da88c323597d6a92ee92` (2026-10-02 upstream commit)  
**Reviewed development line:** CMake fallback `2.76.dev...`  
**Potential use:** separate stochastic Brownian-particle engine for model-class comparison after research/licensing gates

Upstream currently documents:

- Python installation via `pip install smoldyn`;
- a BioSimulators interface;
- SED-ML language `urn:sedml:language:smoldyn`;
- Brownian diffusion / Smoluchowski algorithm mapping to KiSAO `KISAO_0000057`;
- COMBINE media type `text/smoldyn+plain`.

### License status

Do not treat the applicable Smoldyn license as resolved from one metadata field.

At the reviewed commit:

- repository root `LICENSE` contains GNU GPL v3;
- current Python package metadata declares `LGPL-3.0-or-later`;
- core source and CMake headers state LGPL;
- BioSimulators container metadata states LGPL;
- historical commit `83ef2f671aeb6d2d44a1f93fb7b1c14531ea7b5b` changed the root license text from LGPL v3 to GPL v3.

No Smoldyn dependency or distributed integration should be added until the exact applicable terms for the selected release/artifact are clarified.

See [the particle-comparison research gate](docs/research/smoldyn-particle-comparison-gate.md).


### Official 2.75 release evidence (2026-10-06)

The official source archive was downloaded and hashed separately from the development tree. Its author-owned native core has an express LGPL statement; the official page assigns GPL v3 to Python bindings and identifies additional component exceptions. See [the artifact-specific review](docs/research/smoldyn-2.75-license-review.md). A user-supplied standalone native executable is the narrowed candidate. This does not authorize vendoring, linking, required installation or redistribution, and does not resolve the development-tree metadata conflict.

## External measurement deposits

The [public EV data review](docs/research/public-ev-data-review.md) records Dryad CC0 metadata and separately downloaded DRUM CC BY-NC-ND 3.0 US originals. No raw data is vendored; different snapshots and different rights must not be conflated. These bacterial mucus measurements do not validate the tumor target.


## openpyxl

**Use:** optional read-only audit of the exact reviewed external MSD workbook.
**Version:** 3.1.5, pinned in the `data` extra.
**Upstream:** https://pypi.org/project/openpyxl/3.1.5/
**License:** MIT; not vendored.

No spreadsheet dependency is imported by the numerical core. The audit verifies the original byte digest before passing those exact bytes to the reader, disables external-link retention and never evaluates formulas. This is not a general untrusted workbook uploader; arbitrary files are rejected before parsing. Source measurement rights remain separately documented.
