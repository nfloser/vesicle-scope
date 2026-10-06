# Local measured-data audit

VesicleScope can audit the exact reviewed DRUM Figure 2 workbook for the user's noncommercial research use. It leaves the original unchanged and does not turn measurements into simulation parameters.

```bash
python -m pip install '.[data]'
vesiclescope data audit-mucus /path/to/original-figure2.xlsx > local-mucus-audit.json
```

The filename may differ locally, but the original SHA-256 must match the [source manifest](research/public-ev-data-manifest.json). Obtain the original through https://doi.org/10.13016/kkai-hwng; no network download is required by the command or core CI. The later Dryad snapshot is a separate artifact and cannot be substituted.

The deterministic JSON reports provenance, reader version, source rights, pH, sample identity, species, particle type, counts, zero counts, stored geometric means and independently recomputed means. All ten biological samples remain separate. Particle observations within a sample are not additional independent biological replicates. Whole bacteria and EVs remain distinct.

Column and sheet mappings are checked explicitly. Formulas are not evaluated. Non-numeric, negative or nonfinite measurements, empty groups, reordered sample IDs and unexpected populated columns fail. All numeric values are retained; there is no outlier removal or zero replacement. The nonnegative-product geometric-mean convention gives zero if any observation is zero. Differences from stored means are reported, not automatically accepted or corrected.

## Interpretation and rights

Primary Figure 2 labels MSD as µm² at a one-second lag. The workbook headers omit that unit, so the report records the figure as the mapping source and performs no conversion. This is an observation audit, not a diffusion estimate or tumor validation. No biological defaults or existing validation flags change.

The source license is CC BY-NC-ND 3.0 US. The declared project use is noncommercial research. Keep attribution and source-license information with originals and local audit results. Do not commit modified measurement datasets or distribute adaptations as if they were authorized by that license. This command does not confer additional rights or apply the project's restrictive terms to the source data.

The actual original was exercised offline on 2026-10-06: ten samples, 80 sample/species/particle groups, 19,430 numeric particle values, no zero values. Several stored means differ from a recomputation using all supplied values; exclusion, aggregation, snapshot or rounding provenance must be resolved before fitting. This finding is not an allegation of error in the publication.

The optional openpyxl reader stays outside the dependency-free scientific core. CI generates synthetic workbooks to test mapping, failure behavior, geometric means and deterministic CLI output; it does not download or redistribute the original data. No new native engine path is introduced.
