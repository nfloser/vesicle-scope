# Deterministic simulation run bundles

Issue: #45  
Status: VesicleScope-native v0.1 persistence boundary

## Why this exists

The verified transport pipeline can now produce normalized spatial fields, analyses and reproducible figures. Future model comparison, validation and uncertainty work also needs a durable result that can be inspected without silently rerunning a changed model.

A run bundle therefore preserves:

```text
experiment + provenance
        +
BioFVM numerical settings
        +
pinned engine identity
        +
normalized result
        +
exact VesicleScope revision
```

The bundle contains scientific/runtime contracts only. It does not serialize native BioFVM memory or temporary build state.

## Standards review

Reviewed on 2026-10-01 before the format was designed:

- **MIASE** — minimum information for describing simulation experiments so model, procedures and output processing can be reproduced:
  https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1001122
- **SED-ML** — current official release is Level 1 Version 5 and provides a machine-readable simulation-experiment description:
  https://sed-ml.org/
- **COMBINE Archive / OMEX** — a container for the documents belonging to a modelling/simulation project:
  https://co.mbine.org/standards/
- **COMBINE Multicell / MultiCellML** — active work on interoperable multicellular-model descriptions:
  https://multicellml.org/wiki/doku.php?id=start

The current VesicleScope BioFVM model is defined by engine-neutral Python contracts plus a pinned native adapter. It is not currently available as a complete SBML, CellML or other standardized model document.

Creating a SED-ML file that described only the time course while omitting finite source/sink geometry and the spatial model would therefore give a false impression of interoperability.

VesicleScope consequently uses a small native bundle first.

This format is **MIASE-informed**, but it is not called MIASE-compliant merely because it stores many MIASE-relevant fields.

It is also **not SED-ML, OMEX, MultiCellDS or MultiCellML**.

A future OMEX wrapper is reasonable only when all documents needed to reproduce the model can be represented honestly.

## Format

The v0.1 file is deterministic UTF-8 JSON.

Top-level structure:

```json
{
  "schema": "vesiclescope.simulation-run",
  "version": 1,
  "payload_sha256": "...",
  "payload": {
    "vesiclescope_revision": "...",
    "experiment": {},
    "numerics": {},
    "result": {}
  }
}
```

No creation timestamp, hostname, absolute path or machine identifier is injected into canonical content.

Identical inputs therefore produce identical bytes.

## Integrity

`payload_sha256` is calculated from a canonical compact JSON representation of the scientific payload using:

- UTF-8;
- sorted object keys;
- JSON numeric representation;
- no NaN/infinity;
- compact separators.

The digest detects accidental or untracked edits.

It is an integrity mechanism, not a digital signature and not a security/authenticity guarantee.

A reader validates the digest before reconstructing domain objects.

## VesicleScope revision

A run bundle requires an explicit 40- or 64-character hexadecimal VesicleScope commit SHA.

The library does not call Git or infer a revision from the current directory.

That keeps serialization deterministic and usable from installed packages.

Application/CI code is responsible for supplying the revision that was actually executed.

## Experiment content

The current schema preserves:

- experiment ID;
- rectangular 2D domain;
- physical slice thickness;
- duration;
- sample cadence;
- boundary condition;
- diffusion;
- decay;
- initial concentration;
- point/circular release geometry;
- point/circular uptake geometry;
- complete `ScientificParameter` evidence category;
- evidence source/location;
- biological/experimental context;
- assumptions;
- limitations;
- explicit units.

No missing provenance is invented during serialization.

## Numerics

The bundle stores the current BioFVM numerical contract:

- x/y grid spacing;
- timestep.

These remain separate from biological/model parameters.

## Normalized result

The bundle stores:

- concentration/integrated/internalized quantity units;
- exact PhysiCell release/commit and BioFVM version;
- normalized 2D grid;
- declared x-fastest-then-y field ordering;
- transport summary samples;
- complete field snapshots;
- identifier-stable recipient uptake series.

It does not store native rasterized agents because those are adapter implementation state, not the scientific result contract.

## Cross-contract validation

A `SimulationRunBundle` rejects inconsistent inputs before writing or after reading.

Current checks include:

- result/experiment identity;
- result grid spacing equals requested numerics;
- result physical slice thickness equals the experiment;
- grid dimensions cover the declared domain;
- each field snapshot has exactly one grid value per voxel;
- field snapshot times correspond to normalized result samples;
- result recipient uptake series match configured recipients in stable identifier order;
- engine and unit strings are non-blank.

Normal domain/result dataclass validation remains authoritative for individual values.

## Atomic writes

`write_run_bundle` writes to a temporary file in the destination directory, flushes/fsyncs it and atomically replaces the requested output path.

A partial write therefore does not intentionally replace an existing completed bundle.

## Reproduce the synthetic demonstrator

Build the existing pinned native runner, then:

```bash
bash scripts/fetch-physicell.sh
make -f native/biofvm_benchmark/Makefile runner

python -m scripts.generate_donor_boundary_bundle \
  --runner build/native/biofvm_transport_runner \
  --revision "$(git rev-parse HEAD)" \
  --output build/runs/donor-boundary-run.json
```

The generator:

1. runs the reviewed finite-donor synthetic scenario;
2. builds the immutable bundle;
3. writes it atomically;
4. reads it back;
5. requires exact object round-trip;
6. prints the canonical payload SHA-256.

## CI

The native BioFVM workflow generates the same synthetic run bundle with the exact GitHub Actions revision and uploads it as:

```text
vesiclescope-synthetic-donor-boundary-run
```

This is a reproducibility artefact, not experimental data.

## Limitations

The first schema deliberately uses JSON because the current verified spatial fields are small enough that a binary scientific format is not justified yet.

Potential future reasons to change include:

- 3D fields;
- large ensembles;
- long time series;
- multiple substrates;
- measured performance/storage pressure.

Do not migrate to HDF5, Zarr or another binary container without measuring that need.

Schema migration is also deliberately absent. An unknown version fails rather than being silently coerced.

## Future standards path

A likely future progression is:

```text
lossless VesicleScope run bundle
        ↓
stable experiment/model representation
        ↓
evaluate complete SED-ML mapping
        ↓
package interoperable documents in OMEX where honest
```

The goal is real interoperability, not standards-shaped files that omit important model semantics.
