"""Serve deterministic synthetic workspace artifacts for browser acceptance tests."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_detailed_run_comparison import bundle  # noqa: E402
from test_interactive_ev_workspace_e2e import measurements, study  # noqa: E402
from test_population_run_bundles import population_run  # noqa: E402
from vesiclescope.engines import SpatialFieldSnapshot2D  # noqa: E402
from vesiclescope.measurement_files import serialize_measurement_document  # noqa: E402
from vesiclescope.perturbation_files import serialize_perturbation_document  # noqa: E402
from vesiclescope.population_run_bundles import write_population_run_bundle  # noqa: E402
from vesiclescope.run_bundles import write_run_bundle  # noqa: E402
from vesiclescope.ui.app import WorkspaceApplication  # noqa: E402
from vesiclescope.ui.server import create_server  # noqa: E402
from vesiclescope.ui.workspace import Workspace  # noqa: E402


def _temporal_bundle(multiplier: float):
    run = bundle(
        sample_times=(0.0, 10.0, 20.0),
        extracellular=(0.0, 900.0 * multiplier, 1800.0 * multiplier),
        internalized=(0.0, 150.0 * multiplier, 600.0 * multiplier),
    )
    grid = run.result.grid
    voxel_volume = grid.grid_spacing_micron**2 * grid.slice_thickness_micron
    weights = tuple(
        1.0 + ((cell % grid.nx) / grid.nx)
        for cell in range(grid.voxel_count)
    )
    fields = []
    for index, time_min in enumerate((0.0, 10.0, 20.0)):
        target = run.result.samples[index].integrated_field_quantity
        scale = target / (voxel_volume * sum(weights))
        fields.append(
            SpatialFieldSnapshot2D(
                time_min=time_min,
                values=tuple(scale * weight for weight in weights),
            )
        )
    return replace(
        run,
        result=replace(run.result, field_snapshots=tuple(fields)),
    )


def _prepare_workspace(root: Path) -> Workspace:
    workspace = Workspace(root).initialize()
    for directory in (
        workspace.experiments_dir,
        workspace.runs_dir,
        workspace.measurements_dir,
        workspace.perturbations_dir,
        workspace.population_runs_dir,
    ):
        for path in directory.glob("*.json"):
            path.unlink()

    workspace.create_baseline_experiment("baseline.json")
    baseline = workspace.read_experiment("baseline.json")
    workspace.import_measurement(
        "synthetic-cortisol.measurements.json",
        serialize_measurement_document(measurements()),
    )
    workspace.import_perturbation(
        "synthetic-cortisol.study.json",
        serialize_perturbation_document(
            study(baseline.release_sources[0].identifier)
        ),
    )
    write_population_run_bundle(
        workspace.population_run_path("synthetic-cortisol.population-run.json"),
        population_run(),
    )

    left = _temporal_bundle(1.0)
    right = _temporal_bundle(1.6)
    right = replace(
        right,
        experiment=replace(
            right.experiment,
            diffusion=replace(
                right.experiment.diffusion,
                value=right.experiment.diffusion.value * 2.0,
            ),
        ),
    )
    write_run_bundle(
        workspace.run_path("synthetic-baseline-full-name.run.json"),
        left,
    )
    write_run_bundle(
        workspace.run_path("synthetic-variant-full-name.run.json"),
        right,
    )
    return workspace


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    workspace = _prepare_workspace(args.workspace)
    runner = args.workspace.parent / "browser-test-unused-runner"
    runner.touch()
    app = WorkspaceApplication(workspace, runner, "3" * 40)
    server = create_server(app, port=args.port)
    print(f"http://127.0.0.1:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
