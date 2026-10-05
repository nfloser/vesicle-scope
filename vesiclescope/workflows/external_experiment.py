"""Execute one validated external experiment through the existing BioFVM adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vesiclescope.engines import BioFVMNumerics, run_transport
from vesiclescope.experiment_files import read_experiment_document
from vesiclescope.run_bundles import (
    SimulationRunBundle,
    read_run_bundle,
    write_run_bundle,
)


@dataclass(frozen=True, slots=True)
class ExternalExperimentRunResult:
    bundle_path: Path
    bundle: SimulationRunBundle


def run_external_experiment(
    *,
    experiment_path: Path,
    runner: Path,
    revision: str,
    output_path: Path,
    grid_spacing_micron: float,
    time_step_min: float,
) -> ExternalExperimentRunResult:
    """Load, execute and persist one validated supported experiment."""

    experiment = read_experiment_document(experiment_path)
    runner = Path(runner)
    if not runner.is_file():
        raise ValueError(f"native runner does not exist: {runner}")

    numerics = BioFVMNumerics(
        grid_spacing_micron=grid_spacing_micron,
        time_step_min=time_step_min,
    )
    result = run_transport(experiment, numerics, runner)
    bundle = SimulationRunBundle(
        vesiclescope_revision=revision,
        experiment=experiment,
        numerics=numerics,
        result=result,
    )
    path = write_run_bundle(Path(output_path), bundle)
    restored = read_run_bundle(path)
    if restored != bundle:
        raise RuntimeError("written external-experiment run bundle did not round-trip exactly")

    return ExternalExperimentRunResult(bundle_path=path, bundle=bundle)
