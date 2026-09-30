# BioFVM diffusion verification benchmark

**Review date:** 2026-09-30  
**Purpose:** verify the selected continuum engine numerically before any EV-specific interpretation.

## Upstream implementation inspected

VesicleScope targets the PhysiCell **1.14.2** release at commit:

`dbd3499250141b27600e91e501c54c46f68f2763`

Within that pinned tree, `BioFVM/BioFVM_MultiCellDS.cpp` reports:

- program: BioFVM
- BioFVM version: **1.1.7**

The BioFVM public header requests citation of:

Ghaffarizadeh A, Friedman SH, Macklin P. *BioFVM: an efficient parallelized diffusive transport solver for 3-D biological simulations.* Bioinformatics. 2016;32(8):1256-1258. DOI: https://doi.org/10.1093/bioinformatics/btv730

The pinned BioFVM source carries the BSD 3-Clause license. VesicleScope does not vendor that source; the verification build fetches the exact upstream release and verifies its commit before compiling.

## Unit behavior inspected

A raw `BioFVM::Microenvironment` constructor initializes spatial and time units to `none`.

The default microenvironment options in the pinned source use:

- spatial unit: `micron`
- time unit: `min`

Therefore the VesicleScope benchmark sets these units explicitly and checks them before solving. The benchmark does not rely on BioFVM defaults.

For v0.1 engine work, accepting only explicit engine-boundary units is preferable to building a custom conversion framework before a real conversion use case exists.

## Mathematical benchmark

The verification uses a cosine mode in a bounded domain. For diffusion coefficient `D`, domain length `L`, baseline concentration `C0`, and amplitude `A`:

```text
C(x, 0) = C0 + A cos(pi x / L)
```

For the diffusion equation

```text
dC/dt = D * d²C/dx²
```

with zero normal flux at `x = 0` and `x = L`, that mode has the analytical solution

```text
C(x, t) = C0 + A cos(pi x / L) exp(-D (pi/L)² t)
```

The field is constant in the second spatial dimension, allowing the benchmark to exercise BioFVM's 2D LOD diffusion solver while retaining a simple analytical reference.

This equation is used only for mathematical verification. It is not an EV transport claim or biological parameterization.

## Synthetic benchmark configuration

The initial CI benchmark uses:

| Quantity | Value | Unit | Evidence class |
| --- | ---: | --- | --- |
| domain length | 1000 | micron | synthetic benchmark |
| domain width | 100 | micron | synthetic benchmark |
| grid spacing | 20 | micron | synthetic benchmark |
| diffusion coefficient | 1000 | micron²/min | synthetic benchmark |
| timestep | 0.1 | min | synthetic benchmark |
| duration | 60 | min | synthetic benchmark |
| baseline field | 1.0 | dimensionless | synthetic benchmark |
| mode amplitude | 0.5 | dimensionless | synthetic benchmark |

The values are chosen to create a nontrivial, inexpensive numerical verification problem. They must never be reused or displayed as literature-backed EV values.

## Error metric

At the final simulation time, calculate the relative L2 error of the numerical perturbation against the analytical perturbation:

```text
sqrt(sum((C_numeric - C_exact)²) / sum((C_exact - C0)²))
```

Also check conservation of the domain mean because the benchmark has diffusion only and no source, sink, or decay.

Initial acceptance thresholds:

- relative L2 error <= 0.5%
- absolute mean error <= 1e-8

These are numerical acceptance criteria for this specific grid/timestep benchmark, not biological uncertainty bounds.

## What passing this benchmark establishes

A passing run shows that the pinned BioFVM build can be integrated headlessly and that its 2D constant-coefficient diffusion result agrees with a simple analytical reference within the documented tolerance for this discretization.

It also exercises explicit unit assignment and records the exact upstream revision.

## What it does not establish

Passing does **not** validate:

- EV diffusivity values;
- EV release or uptake;
- extracellular degradation;
- cell geometry or density;
- ECM interactions;
- interstitial flow;
- a biological communication-range metric;
- applicability to any species, tissue, cell line, or EV preparation.

Those require separate evidence notes and validation work before interpretation.
