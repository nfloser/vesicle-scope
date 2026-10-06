# Public EV transport data review

Issue #91; reviewed 2026-10-06. Dataset rights, publication rights and scientific suitability are separate decisions. No third-party raw data is vendored here.

## Verified primary sources

Steinman et al., *Vaginal bacteria-derived extracellular vesicles diffuse through human cervicovaginal mucus to enable microbe-host signaling*, npj Biofilms and Microbiomes 12, 10 (2026), DOI https://doi.org/10.1038/s41522-025-00866-9. Use the peer-reviewed article rather than its earlier preprint. A June 2026 correction concerns funding acknowledgement.

| Deposit | Evidence collected | Rights and disposition |
| --- | --- | --- |
| Dryad, https://doi.org/10.5061/dryad.cvdncjth8 | Version 3, API version ID 412881; 13-file inventory and repository-reported SHA-256 values | API designates CC0-1.0. CSV download endpoints returned HTTP 401/403 in this review; raw bytes are not locally verified. Preferred snapshot for future reusable ingestion. |
| University of Maryland DRUM, https://doi.org/10.13016/kkai-hwng | Two original October 2025 XLSX files downloaded; byte counts and SHA-256 verified | CC BY-NC-ND 3.0 US, https://creativecommons.org/licenses/by-nc-nd/3.0/us/. Attribution, noncommercial restriction and no redistribution of adaptations. Originals supplied separately with provenance; not committed to this public repository. |

The [machine-readable manifest](public-ev-data-manifest.json) distinguishes locally verified hashes from repository-reported hashes. These deposits are distinct snapshots: CC0 on Dryad does not automatically relicense the DRUM bytes. No equality between their contents has been established.

## What the downloaded workbooks actually provide

`2025_10_01 Data Figs2.xlsx` contains a geometric-mean summary and ten sample sheets of individual one-second mean squared displacement values. Four bacterial EV preparations (L. crispatus, L. iners, G. vaginalis, M. mulieris) and four whole-bacterium preparations occupy separate columns. Whole bacteria must not be pooled with EVs. Ten independent human mucus samples span high and low pH groups.

The other workbook contains characterization and cell uptake measurements, including percentages at 2, 8, 12 and 24 hours. Sheet labels alone do not establish quantity semantics. The paper describes multiple particle tracking and uptake in VK2/E6E7, Ishikawa and BeWo-b30 cells.

Before ingestion, verify the MSD units against the primary figure/methods, preserve exclusion decisions, identify technical versus biological replicates, and map column labels explicitly. A one-second MSD does not supply trajectories, anomalous-diffusion exponents or evidence that normal diffusion applies. The conditional planar relation D = MSD/(4t) is not an automatically validated parameter conversion. Fluorescence uptake percentage cannot directly determine the current first-order sink coefficient.

## Scientific acceptance decision

These are real measurements of bacterial EV transport in human cervicovaginal mucus. They are a potential context-specific transport target, not quantitative validation of HeLa EV spread in tumors. No biological defaults or validation-ready flags change.

Colombo et al. 2025 (DOI 10.1002/jev2.70169) remains the tumor-distance target. Its reviewed public analysis repository supplies scripts rather than raw tumor TIFFs; fitted publication summaries are not raw measurements. The [existing target gate](colombo-2025-validation-target.md) remains open.

Sariano et al. 2023 (DOI 10.1002/jev2.12323) and Lenzini et al. 2020 (PMCID PMC7075670) are relevant primary transport studies, but matrix binding, convection and confinement require separate model semantics. No raw-data acquisition or license clearance is claimed for those studies in this review.

## Next executable step

Obtain the exact Dryad version's CSV bytes through its supported public download or authorized API, verify all repository hashes, audit units and replicate/exclusion structure, and define a mucus-specific observation model before fitting. No core CI job requires network access. A tumor validation still needs the matching raw measurements and fluorescence-to-model observation mapping.
