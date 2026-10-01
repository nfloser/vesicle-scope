"""Run the reviewed synthetic diffusion × uptake factor experiment."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from vesiclescope.analysis import analyze_diffusion_uptake_condition
from vesiclescope.engines import BioFVMNumerics, run_transport
from vesiclescope.run_bundles import (
    SimulationRunBundle,
    read_run_bundle,
    run_bundle_payload_sha256,
    write_run_bundle,
)
from vesiclescope.scenarios import diffusion_uptake_factor_conditions


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the nine-condition synthetic diffusion × uptake experiment."
    )
    parser.add_argument(
        "--runner",
        default=os.environ.get("VESICLESCOPE_BIOFVM_RUNNER"),
        help="Path to the built native BioFVM transport runner.",
    )
    parser.add_argument(
        "--revision",
        default=os.environ.get("VESICLESCOPE_REVISION"),
        help="Exact VesicleScope commit SHA represented by these runs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for run bundles and deterministic summary.json.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if not args.runner:
        raise SystemExit(
            "native runner is required via --runner or VESICLESCOPE_BIOFVM_RUNNER"
        )
    if not args.revision:
        raise SystemExit(
            "VesicleScope revision is required via --revision or VESICLESCOPE_REVISION"
        )

    runner = Path(args.runner)
    if not runner.is_file():
        raise SystemExit(f"native runner does not exist: {runner}")

    output_dir = args.output_dir
    bundles_dir = output_dir / "runs"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    numerics = BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1)

    rows = []
    for condition in diffusion_uptake_factor_conditions():
        experiment = condition.experiment
        result = run_transport(experiment, numerics, runner)
        analysis = analyze_diffusion_uptake_condition(condition, result)

        bundle = SimulationRunBundle(
            vesiclescope_revision=args.revision,
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
                f"written run bundle did not round-trip exactly: {experiment.experiment_id}"
            )

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
        "vesiclescope_revision": args.revision.lower(),
        "numerics": {
            "grid_spacing_micron": numerics.grid_spacing_micron,
            "time_step_min": numerics.time_step_min,
        },
        "conditions": rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
