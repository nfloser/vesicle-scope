# Colombo 2025 tumour-distance validation target

Issue: #37  
Review date: 2026-09-30  
Status: external validation target defined; quantitative comparison blocked

## Why this is the first external target

The synthetic VesicleScope baseline now verifies release, continuum transport, finite recipient uptake, multi-recipient accounting, spatial fields, count sensitivity and reproducible figures.

The next scientific step is to define a real external observable before calibrating parameters.

Colombo et al. provide a particularly relevant target because their tumour experiment measures EV-associated fluorescent signal as a function of distance from donor cells in tissue-like geometry.

Reference:

- Colombo F, Nimkar K, Norton EG, Lovat F, Cocucci E. *Exploring the Spatial Limits of Extracellular Vesicles-Mediated Intercellular Communication.* Journal of Extracellular Vesicles. 2025;14:e70169.
- DOI: https://doi.org/10.1002/jev2.70169
- PMID: 41167986
- PMCID: PMC12575057

## Experimental observable

The in-vivo experiment used HeLa donor cells expressing CD9-Halo and HeLa recipient cells expressing Staygold in subcutaneous tumour xenografts in athymic nude mice.

The published analysis measures EV-associated CD9-Halo signal as a function of distance from the **nearest donor-cell boundary**.

The Methods report:

- confocal pixel size: 0.2 micron;
- donor and recipient cells injected at 1:100 or 1:200 donor:recipient ratios;
- donor-cell masks used as the spatial reference;
- concentric distance zones around donor-cell boundaries;
- zones described as 50 pixels, approximately 10 micron.

The paper reports signal above background through approximately the first 40 micron from donor boundaries.

An exponential fit to above-background tumour data is reported to predict:

- 50% cumulative retention within 17 micron;
- 80% cumulative retention within 40 micron;
- less than 5% of signal beyond 100 micron.

These are **fit-derived publication summaries**. VesicleScope does not store them as transport, release or uptake parameters.

## Public analysis code

The paper Methods link the authors' repository:

```text
CocucciLab/spatial-limits-of-extracellular-vesicles
```

Reviewed pin:

```text
repository commit:
ed9e28173929c9f896d16658781d7a4b9cc2297c

analysis path:
in vivo/distTraAnalysis.py

file/blob SHA:
16744cd7d0eb0271ce5a8c3949b84e7cb86d8933
```

The upstream repository is MIT licensed.

The public pipeline reads thresholded microscopy frames, computes a Euclidean distance transform from manually selected/loaded donor masks and counts non-zero signal pixels by distance.

VesicleScope does not vendor this code. The pin exists so the reviewed external analysis semantics can be identified later.

## Paper/code binning discrepancy

A reproducibility discrepancy is intentionally retained rather than normalized away.

The paper Methods describe:

```text
50 pixels * 0.2 micron/pixel ~= 10 micron zones
```

The current public `distTraAnalysis.py` uses:

```text
histogram bins: 25 pixels
pixel scale: 0.2 micron/pixel
=> 5 micron increments
```

Without the exact raw dataset/workflow version used for the published figures, VesicleScope cannot defensibly decide that one representation should silently replace the other.

Any future comparison must either:

1. obtain the authors' source measurements / workflow clarification; or
2. explicitly report results under both bin definitions as a sensitivity analysis.

## Raw-data availability

The publication Data Availability Statement says that supporting data are available from the corresponding author upon reasonable request.

The public GitHub repository contains analysis code, but the raw tumour TIFF dataset required to recreate the published Figure 5m / Supplementary Figure S6 distributions is not included.

Accordingly, the machine-readable target records raw-data availability as:

```text
on_request
```

—not public.

## Why quantitative validation is blocked

Four blockers are explicit in the code contract.

### 1. Raw measurements are unavailable publicly

The fit summaries alone are not a replacement for the per-sample radial signal measurements, uncertainty and background distributions.

### 2. Donor geometry does not yet match

The experiment measures distance from a finite, segmented donor-cell **boundary**.

The current VesicleScope donor remains a point release source. Comparing centre-distance from that point directly with donor-boundary distance would introduce an unreported geometric offset.

### 3. Binning semantics differ

The paper describes approximately 10 micron zones; the public code currently implements 5 micron bins.

### 4. Model parameters remain synthetic

The current release rate, transport coefficient and uptake parameters are numerical verification inputs. They are not calibrated to this HeLa tumour system.

## What can be tested now

VesicleScope can currently assert, from public material:

- the publication identity and biological context;
- the measured class of observable;
- the distance reference;
- microscopy pixel scale;
- published segmentation-zone description;
- current public code binning;
- current public analysis-code version and license;
- fit-derived radial summary landmarks;
- raw-data access status;
- blockers preventing a direct fit.

That information is exposed through:

```python
from vesiclescope.validation import colombo_2025_tumour_distance_target

target = colombo_2025_tumour_distance_target()
assert not target.quantitatively_ready
```

## Next prerequisite

The next model-side prerequisite is a **finite donor geometry plus a donor-boundary radial-profile observable** derived from normalized VesicleScope spatial fields.

That work should reproduce the geometry of the observable—not the published values—before any parameter-estimation problem is introduced.

Parameter fitting remains out of scope until the missing measurement data and analysis-bin discrepancy are resolved.
