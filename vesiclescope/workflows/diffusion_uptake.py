"""Product workflow for the reviewed synthetic diffusion × uptake experiment."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from vesiclescope.analysis import analyze_diffusion_uptake_condition
from vesiclescope.engines import BioFVMNumerics, run_transport
from vesiclescope.figures import render_diffusion_uptake_figure
from vesiclescope.run_bundles import (
    SimulationRunBundle,
    read_run_bundle,
    run_bundle_payload_sha256,
    write_run_bundle,
)
from vesiclescope.scenarios import diffusion_uptake_factor_conditions


@dataclass(frozen=True, slots=True)
class DiffusionUptakeWorkflowResult:
    summary_path: Path
    figure_path: Path
    run_bundle_paths: tuple[Path, ...]


def run_diffusion_uptake_factor_experiment(
    *,
    runner: Path,
    revision: str,
    output_dir: Path,
) -> DiffusionUptakeWorkflowResult:
    """Run the reviewed nine-condition experiment and persist all public artifacts."""

    runner = Path(runner)
    if not runner.is_file():
        raise ValueError(f"native runner does not exist: {runner}")

    output_dir = Path(output_dir)
    bundles_dir = output_dir / "runs"
    bundles_dir.mkdir(parents=True, exist_ok=True)

    numerics = BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1)
    rows: list[dict[str, object]] = []
    analyses = []
    bundle_paths: list[Path] = []

    for condition in diffusion_uptake_factor_conditions():
        experiment = condition.experiment
        result = run_transport(experiment, numerics, runner)
        analysis = analyze_diffusion_uptake_condition(condition, result)
        analyses.append(analysis)

        bundle = SimulationRunBundle(
            vesiclescope_revision=revision,
            experiment=experiment,
            numerics=numerics,
            result=result,
        )
        bundle_path = write_run_bundle(
            bundles_dir / f"{experiment.experiment_id}.json",
            bundle,
        )
        if read_run_bundle(bundle_path) != bundle:
            raise RuntimeError(
                "written run bundle did not round-trip exactly: "
                f"{experiment.experiment_id}"
            )
        bundle_paths.append(bundle_path)

        rows.append(
            {
                "experiment_id": experiment.experiment_id,
                "diffusion_factor": analysis.diffusion_factor,
                "uptake_factor": analysis.uptake_factor,
                "diffusion": {
                    "value": analysis.diffusion_value,
                    "unit": analysis.diffusion_unit,
                },
                "uptake": {
                    "value": analysis.uptake_value,
                    "unit": analysis.uptake_unit,
                },
                "total_released_quantity": analysis.total_released_quantity,
                "final_extracellular_quantity": analysis.final_extracellular_quantity,
                "final_internalized_quantity": analysis.final_internalized_quantity,
                "extracellular_fraction": analysis.extracellular_fraction,
                "internalized_fraction": analysis.internalized_fraction,
                "quantity_unit": analysis.quantity_unit,
                "run_bundle_payload_sha256": run_bundle_payload_sha256(bundle),
            }
        )

    summary = {
        "schema": "vesiclescope.synthetic-diffusion-uptake-factor-summary",
        "version": 1,
        "scientific_status": "synthetic_benchmark",
        "interpretation": (
            "Controlled model-behaviour experiment; not experimental evidence "
            "and not a biological parameter-range claim."
        ),
        "vesiclescope_revision": revision.lower(),
        "numerics": {
            "grid_spacing_micron": numerics.grid_spacing_micron,
            "time_step_min": numerics.time_step_min,
        },
        "conditions": rows,
    }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    try:
        figure_path = render_diffusion_uptake_figure(
            tuple(analyses),
            output_dir / "diffusion-uptake.svg",
        )
    except RuntimeError as exc:
        if "Matplotlib is required" in str(exc):
            raise RuntimeError(
                "figure rendering requires the optional figures dependency; "
                "install VesicleScope with 'pip install .[figures]'"
            ) from exc
        raise

    return DiffusionUptakeWorkflowResult(
        summary_path=summary_path,
        figure_path=figure_path,
        run_bundle_paths=tuple(bundle_paths),
    )
