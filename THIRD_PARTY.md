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
