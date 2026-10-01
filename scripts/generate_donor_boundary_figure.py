"""Generate the reviewed synthetic donor-boundary profile figure headlessly."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from vesiclescope.engines import BioFVMNumerics, run_transport
from vesiclescope.figures import render_donor_boundary_figure
from vesiclescope.scenarios import finite_donor_boundary_figure_experiment


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the VesicleScope synthetic donor-boundary figure."
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

    experiment = finite_donor_boundary_figure_experiment()
    result = run_transport(
        experiment,
        BioFVMNumerics(
            grid_spacing_micron=5.0,
            time_step_min=0.1,
        ),
        runner,
    )
    output = render_donor_boundary_figure(
        experiment,
        result,
        args.output,
        time_min=experiment.duration_min,
        max_distance_micron=80.0,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
