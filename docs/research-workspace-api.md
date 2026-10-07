# EV perturbation workspace API

Status: local workspace contract for issues #100/#106  
Reviewed: 2026-10-07

## Purpose

The local VesicleScope workspace now treats biological measurements,
perturbation evidence and completed phenotype-specific transport runs as
separate scientific artifacts.

The browser is a rendering and interaction layer. It does not decide which
biological effect changes a solver parameter, infer marker identity, interpolate
unmeasured time points, convert assay units or fit model parameters.

## Workspace layout

A workspace may contain five independent artifact classes:

| Directory | Artifact |
| --- | --- |
| `experiments/` | transport experiment documents |
| `runs/` | existing single-population simulation run bundles |
| `measurements/` | longitudinal blood/plasma EV measurement documents |
| `perturbations/` | evidence-aware perturbation studies |
| `population-runs/` | completed phenotype-specific population-run bundles |

All filenames use the same confined `.json` naming rule. Paths cannot escape
their artifact directory.

Measurement and perturbation imports are fully deserialized before they are
written. Successful imports are re-serialized into the canonical deterministic
format, so malformed JSON, bad integrity digests and invalid scientific
contracts do not become workspace artifacts.

## Loopback HTTP surface

The existing loopback-only server and Host-header validation remain unchanged.

### Inspect

- `GET /api/state`
- `GET /api/measurement?name=<file>`
- `GET /api/perturbation?name=<file>`
- `GET /api/population-run?name=<file>`

The population-run response contains both the original perturbation-study
metadata and the executable result:

- exposures with concentration, evidence source, context and limitations;
- phenotype marker/cargo annotations;
- declared effects and model mappings;
- execution audit records with `applied` or `not_executed` status;
- baseline and effective experiment summaries per transported phenotype;
- per-population time series, spatial fields and recipient uptake;
- aggregate time series and aggregate spatial fields derived by the verified
  independent-population composition functions.

The aggregate result is derived from already completed compatible child runs.
It does not introduce population interactions.

### Import

- `POST /api/measurement/import`
- `POST /api/perturbation/import`

Both accept the existing integrity-protected document as text plus a safe
workspace filename. No document is written until validation succeeds.

### Execute

`POST /api/population-run` accepts:

- one perturbation-study filename;
- an explicit object mapping phenotype IDs to transport-experiment filenames;
- a population-run output filename;
- BioFVM grid spacing and time step.

The server resolves mappings through
`resolve_perturbation_transport` and executes the resulting populations
through `run_population_transport`. The JavaScript client does not transform
release, uptake or decay parameters.

A phenotype ID that is not declared by the study is rejected. A study
phenotype may remain annotation-only by simply not assigning a transport
experiment to it.

### Measured versus predicted

`POST /api/measurement-comparison` accepts:

- one measurement dataset;
- one completed population run;
- a condition ID;
- either a phenotype ID or `total`;
- explicit observation-ID to prediction-observable mappings.

The endpoint delegates alignment to
`compare_measurements_to_prediction`.

Consequences:

- only exact stored model times match;
- a missing model time stays missing;
- there is no interpolation;
- there is no implicit unit conversion;
- a numerical residual exists only when measurement and model units are already
  identical;
- measured values never become transport parameters.

For `total`, the server creates a read-only normalized aggregate result from
the verified aggregate samples and fields before calling the same comparison
adapter.

## Measurement display semantics

The server labels every observation with a `display_group` so the browser does
not infer scientific semantics from marker arrays or names:

- `total_or_unmarked`: particle concentration/size or EV-associated event
  concentration without a marker-defined measurement kind;
- `marker_defined`: marker-positive event concentration or marker signal;
- `cargo`: cargo concentration or cargo signal.

The original `kind`, assay method, detection semantics, marker list, replicate
metadata and units remain present alongside the display group.

A `particle_concentration` observation is therefore still explicitly a
particle measurement; grouping it for presentation does not relabel it as an
EV count.

## Downloads

The workspace can return the original deterministic JSON artifacts for
measurements, perturbations and population runs in addition to the existing
experiment/run downloads.

## Verification

The normal unit suite covers:

- separate storage roots;
- filename confinement;
- valid deterministic import/round-trip;
- invalid-document rejection without partial files;
- application-state discovery;
- loopback import and inspection;
- server-side observation grouping.

The native BioFVM CI job additionally executes a full synthetic workflow:

1. create the reviewed transport baseline;
2. import a synthetic longitudinal plasma measurement dataset;
3. import a two-phenotype cortisol-labelled perturbation study;
4. apply an explicit synthetic release multiplier to one phenotype only;
5. execute both phenotype runs through BioFVM;
6. inspect per-population and aggregate fields;
7. verify the effect execution audit;
8. compare an exact measured time point to the aggregate model output;
9. download and deserialize the persisted population-run bundle.

The cortisol label in this test is intentionally accompanied by a
`synthetic_benchmark` effect magnitude. The test verifies software behavior;
it is not evidence that cortisol produces that fold change biologically.
