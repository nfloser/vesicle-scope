# COMBINE / OMEX project archives

VesicleScope can package one validated experiment and its completed run bundles into a deterministic COMBINE Archive (\`.omex\`).

This feature is for reproducible exchange and storage. It does not change the scientific model and it does not execute BioFVM during archive inspection.

## Create an archive

\`\`\`bash
vesiclescope archive create \
  experiment.json \
  baseline.run.json variant.run.json \
  --output project.omex
\`\`\`

Run bundles are optional:

\`\`\`bash
vesiclescope archive create experiment.json --output experiment-only.omex
\`\`\`

Every run must contain the exact same experiment as the archived experiment document. VesicleScope rejects mixed projects rather than silently combining incompatible definitions.

## Inspect an archive

\`\`\`bash
vesiclescope archive inspect project.omex
\`\`\`

Inspection validates:

- the COMBINE manifest;
- safe archive member paths;
- the experiment document digest and scientific contract;
- each run-bundle digest and scientific/result contract;
- run-to-experiment identity.

It does not rerun the simulation.

## Archive contents

A VesicleScope archive contains:

\`\`\`text
manifest.xml
README.md
experiment.json
runs/run-001.json
runs/run-002.json
...
\`\`\`

The experiment is the OMEX master resource. VesicleScope-native JSON is listed using a JSON media-type URI; no custom COMBINE specification URI is invented.

Archives are byte-deterministic for identical logical input on the supported implementation path: names, member order, timestamps and permissions are fixed, and no current time or absolute path is added.

## SED-ML boundary

VesicleScope currently **does not claim SED-ML compatibility**.

OMEX is being used as the standards-oriented container. The current spatial BioFVM experiment itself remains represented by the provenance-aware VesicleScope experiment contract rather than SBML, CellML or another portable standardized model language.

See [the interoperability research decision](research/combine-archive-interoperability.md) for the rationale and the requirements for future honest SED-ML support.
