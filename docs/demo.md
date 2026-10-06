# VesicleScope demonstration

This walkthrough demonstrates a working research product using synthetic inputs.
It does not demonstrate validation against biological measurements.

## Install

Download the v0.3.0 wheel from the repository's GitHub Releases page. In a fresh
Python 3.11+ environment:

```bash
python -m pip install vesicle_scope-0.3.0-py3-none-any.whl
vesiclescope --version
vesiclescope engine build --output biofvm_transport_runner
vesiclescope workspace init workspace
```

The engine build needs Git, a GNU-compatible C++/OpenMP compiler and network access
to the pinned upstream source. On Windows use `biofvm_transport_runner.exe` as the
output name. See [engine setup](engine-setup.md) for the platform prerequisites.

## Start the workspace

```bash
vesiclescope ui --workspace workspace --runner ./biofvm_transport_runner --revision RELEASE_COMMIT_SHA
```

Replace `RELEASE_COMMIT_SHA` with the full commit SHA referenced by the v0.3.0 tag.
For a modified source build, use its actual commit, not the release tag's SHA.
On Windows replace the runner filename with `biofvm_transport_runner.exe`.
Open the loopback URL printed by the command. Stop the server with Ctrl+C.

## Five-minute walkthrough

1. Choose **Create reviewed baseline**. Explain that its values are synthetic
   numerical verification inputs, not biological constants.
2. Select the newly created baseline in the experiment list. Set **Run bundle filename** to `baseline-run.json` and run the selected
   experiment with the displayed grid spacing and timestep.
   Inspect the persisted spatial field, quantity time series and solver provenance.
3. Select the baseline and use **Create synthetic variant**. Give it a distinct
   filename and experiment ID, change one synthetic rate, and save it. Run the
   variant with the same numerical settings and **Run bundle filename**
   `variant-run.json`. Existing run artifacts are never overwritten.
4. Compare the two stored runs. Explain that the curves and compatible-field
   differences show model behaviour, not a biologically superior condition.
5. Inspect each run and use **Add inspected run**. Arrange the two filenames in
   the desired order, then choose **Download batch OMEX**. Import that file through
   **Import experiment batch OMEX** and inspect the recovered experiments/runs.
   No simulation is rerun during exchange.

For individual projects use **Download project OMEX** and the single-experiment
COMBINE import. For headless archive and batch execution see
[archive guide](combine-archives.md) and [experiment batches](experiment-batches.md).

## What is complete and what remains

The selected continuum workflow, reproducible artifacts, numerical checks,
CLI/local workspace, stored-run analysis and archive exchange are integrated.
External biological validation and the particle-engine comparison remain separate
research gates. See [product readiness](product-readiness.md) for the exact boundary.
