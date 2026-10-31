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

## Verify a separately obtained Dryad v3 snapshot

Dryad version 3 is a distinct CC0 snapshot. Verify either a flat ZIP containing
its 13 advertised files or the extracted directory. Both paths check inventory,
byte sizes and repository-reported SHA-256 values offline:

```bash
vesiclescope data verify-dryad-v3 /path/to/dryad-v3-files.zip > dryad-v3-verification.json
vesiclescope data verify-dryad-v3 /path/to/extracted-dryad-v3 > dryad-v3-verification.json
```

The command reads but does not modify or extract the files. ZIP inputs must be
flat, unencrypted and free of duplicate names; directory inputs must contain
regular files only. Missing, extra, size-mismatched or digest-mismatched entries
are rejected before a deterministic provenance report is written. The command
does not parse measurements, compare the Dryad and DRUM snapshots, infer
exclusions, convert one-second MSD into a diffusion coefficient or mark the data
ready for fitting. Raw data remain outside this repository and CI uses generated
byte fixtures only.

The official version 3 package was exercised offline on 2026-10-29. All 13
advertised file sizes and SHA-256 values matched. Repeated downloads on
2026-10-30 produced different whole-ZIP hashes because Dryad generated new ZIP
entry timestamps, while every filename, byte size and file SHA-256 remained
identical. The archive hash is therefore not used as a stable source identity;
the verified file-level inventory is authoritative. This establishes source
identity only. The Dryad/DRUM snapshot comparison, measurement hierarchy and
observation model remain unresolved, so the report continues to set
`ready_for_parameter_fitting` to `false`.

## Reconcile the verified one-second MSD snapshots

With both exact sources available locally, compare their ordered, nonempty
one-second MSD values and stored sample summaries without writing either source:

```bash
vesiclescope data reconcile-mucus-snapshots \
  /path/to/2025_10_01\ Data\ Figs2.xlsx \
  /path/to/dryad-v3-files.zip > mucus-snapshot-reconciliation.json
```

The command first enforces both existing source-identity gates. It then checks
the explicit 80-group sample/species/particle mapping, reporting exact values,
small parser-representation differences, substantive differences and unpaired
ordered values separately. The relative tolerance (`1e-12`) classifies only
CSV-decimal versus XLSX-binary representation; it never suppresses a count or
value from the report and is not a biological or fitting tolerance.

The actual-source acceptance run on 2026-10-31 found identical stored summary
cells and no substantive mismatch among 19,281 paired particle values. Four
paired values differed only at floating-point representation scale. DRUM held
149 additional ordered values in Sample 1 / *L. crispatus* bEV (234 versus 85),
for 19,430 DRUM and 19,281 Dryad values overall. This establishes a snapshot
difference, not its cause. It does not show whether values were intentionally
excluded, accidentally omitted or processed by another rule; fitting remains
blocked pending that provenance and an explicit observation model.
