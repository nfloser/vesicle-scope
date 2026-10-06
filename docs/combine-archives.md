# COMBINE / OMEX project archives

VesicleScope can package one validated experiment and its completed run bundles into a deterministic COMBINE Archive (`.omex`).

This feature is for reproducible exchange and storage. It does not change the scientific model and it does not execute BioFVM during archive inspection.

## Create an archive

```bash
vesiclescope archive create \
  experiment.json \
  baseline.run.json variant.run.json \
  --output project.omex
```

Run bundles are optional:

```bash
vesiclescope archive create experiment.json --output experiment-only.omex
```

Every run must contain the exact same experiment as the archived experiment document. VesicleScope rejects mixed projects rather than silently combining incompatible definitions.

## Inspect an archive

```bash
vesiclescope archive inspect project.omex
```

Inspection validates:

- the COMBINE manifest;
- safe archive member paths;
- the experiment document digest and scientific contract;
- each run-bundle digest and scientific/result contract;
- run-to-experiment identity.

It does not rerun the simulation.

## Archive contents

A VesicleScope archive contains:

```text
manifest.xml
README.md
experiment.json
runs/run-001.json
runs/run-002.json
...
```

The experiment is the OMEX master resource. VesicleScope-native JSON is listed using a JSON media-type URI; no custom COMBINE specification URI is invented.

Archives are byte-deterministic for identical logical input on the supported implementation path: names, member order, timestamps and permissions are fixed, and no current time or absolute path is added.

## SED-ML boundary

VesicleScope currently **does not claim SED-ML compatibility**.

OMEX is being used as the standards-oriented container. The current spatial BioFVM experiment itself remains represented by the provenance-aware VesicleScope experiment contract rather than SBML, CellML or another portable standardized model language.

See [the interoperability research decision](research/combine-archive-interoperability.md) for the rationale and the requirements for future honest SED-ML support.


## Local workspace

The loopback browser workspace exposes the same archive contract as the CLI.

For a selected experiment, **Download project OMEX** packages the stored experiment plus completed run bundles whose embedded experiment exactly matches it. Export does not rerun BioFVM.

**Import VesicleScope COMBINE project** accepts a local `.omex` file and sends it directly to the loopback server as a bounded binary upload. The workspace validates the complete archive before writing any artifact. Imported experiment/run filenames are generated deterministically and made collision-safe; an import failure does not leave a partial project behind.

The browser upload path is limited to 64 MB. This is a product-surface limit, separate from the archive reader's defensive uncompressed-size limits.

The same scientific boundary applies in the browser: OMEX is a reproducible project container and **SED-ML compatibility is not claimed**.

## Completed experiment batches

Package all completed runs referenced by an explicit batch manifest:

```bash
vesiclescope archive create-batch results/batch-manifest.json --output batch.omex
vesiclescope archive inspect batch.omex
```

The exporter resolves run filenames beside the manifest and obtains each exact
experiment from its validated run bundle. Original experiment input files need
not remain available after execution. It verifies consecutive member order,
unique experiment IDs and run filenames, payload digests, revision and numerical
settings. Paths cannot escape the manifest directory, including through symlinks.
No solver is invoked.

The archive contains `batch-manifest.json` as its master JSON resource and ordered
`experiments/member-001.json` / `runs/member-001.run.json` pairs, plus the COMBINE
manifest and README. Source filenames are normalized to deterministic archive
basenames; all other batch audit values are retained. Inspection rejects missing,
extra or duplicated members, mismatched experiments, altered digests and unsafe
ZIP paths. The existing size and encryption restrictions apply.

CLI inspection distinguishes batch and single-experiment projects. Browser
import/export currently supports single-experiment projects only. Batch packaging
does not imply a sampled biological distribution or SED-ML portability.
