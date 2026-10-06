# Measured mucus observation audit gate

Issue #93; reviewed 2026-10-06. Follows the [primary-source inventory](public-ev-data-review.md).

## Questions resolved for this change

- The user explicitly declares noncommercial research use. DRUM's CC BY-NC-ND 3.0 US conditions still travel with the originals; local processing does not grant redistribution rights for adapted measurements. Primary terms: https://creativecommons.org/licenses/by-nc-nd/3.0/us/ and its legal code.
- The primary publication's [Figure 2](https://www.nature.com/articles/s41522-025-00866-9/figures/2) was inspected directly. Its axes label MSD in µm² at lag one second. This supplies the contextual unit mapping absent from workbook headers. No data rescaling or normal-diffusion parameter inference follows.
- The exact source workbook can be audited reproducibly without vendoring data or implementing a spreadsheet parser. openpyxl 3.1.5 provides read-only XLSX access. It is lazy-loaded as an optional data extra. Formula evaluation is disabled and formula cells are rejected.

## Mathematical/statistical scope

For strictly positive supplied values x_i, the independently computed geometric mean is exp(sum(log(x_i))/n). If any supplied value is zero, report zero under the nonnegative-product convention and retain the zero count. No pseudocount or exclusion is applied. This computation is independent of the workbook's stored means and is not presumed to reproduce the authors' full analysis pipeline.

No pooled significance test, fitted model, confidence interval, transport coefficient or biological calibration is produced. Ten donor mucus samples remain the biological grouping level; individual particles are nested measurements.

## Actual-data acceptance and unresolved question

The original hash was verified before parsing and unchanged afterwards. The audit identifies 80 groups and 19,430 particle values with no zeros. Stored sample means are not uniformly reproduced by geometric means across all supplied values. This does not isolate the cause: prior exclusion, aggregation or snapshot differences require additional provenance. The report preserves both summaries and their differences rather than substituting one for the other.

The separate CC0 Dryad v3 inventory remains preferred for future publicly reusable ingestion, but its bytes have not been obtained here. Tumor measurements and fluorescence-to-model mapping remain open. These questions prevent parameter fitting, not this narrower measured-data audit.

## Smoldyn disposition

Noncommercial use does not itself make GPL and LGPL equivalent. The official 2.75 LGPL core evidence supports reviewing a separate user-installed native process; it does not resolve redistribution of a specific mixed-component build. No linking, automatic installation, bundled binary, Python binding or new adapter is introduced. Issue #83 remains the dedicated particle integration gate. No maintainer response is claimed.

## Reader evidence

- https://pypi.org/project/openpyxl/3.1.5/ — version and MIT license.
- https://openpyxl.pages.heptapod.net/openpyxl/tutorial.html — read-only/data-only behavior and workbook handling.

Offline tests use generated synthetic workbooks. The actual original acceptance run remains separate from CI and no source/derived measurement data is added to the repository.
