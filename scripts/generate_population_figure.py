"""Generate the reviewed synthetic recipient-count figure headlessly."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from vesiclescope.analysis import analyze_recipient_population
from vesiclescope.engines.biofvm import BioFVMNumerics, run_transport
from vesiclescope.figures import render_recipient_count_figure
from vesiclescope.scenarios import finite_recipient_count_sweep_experiment


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the VesicleScope synthetic population figure."
    )
    parser.add_argument(
        "--runner",
        default=os.environ.get("VESICLESCOPE_BIOFVM_RUNNER"),
        help="Path to the built native BioFVM transport runner.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output SVG path.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if not args.runner:
        raise SystemExit(
            "native runner is required via --runner or "
            "VESICLESCOPE_BIOFVM_RUNNER"
        )

    runner = Path(args.runner)
    if not runner.is_file():
        raise SystemExit(f"native runner does not exist: {runner}")

    experiments = tuple(
        finite_recipient_count_sweep_experiment(count)
        for count in (2, 4, 8)
    )
    numerics = BioFVMNumerics(
        grid_spacing_micron=10.0,
        time_step_min=0.1,
    )
    results = tuple(
        run_transport(experiment, numerics, runner)
        for experiment in experiments
    )
    summaries = tuple(
        analyze_recipient_population(
            experiment,
            result,
            time_min=experiment.duration_min,
        )
        for experiment, result in zip(experiments, results)
    )

    output = render_recipient_count_figure(
        experiments,
        results,
        summaries,
        args.output,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
