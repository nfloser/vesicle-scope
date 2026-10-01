"""Generate one durable synthetic donor-boundary BioFVM run bundle."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from vesiclescope.engines import BioFVMNumerics, run_transport
from vesiclescope.run_bundles import (
    SimulationRunBundle,
    read_run_bundle,
    run_bundle_payload_sha256,
    write_run_bundle,
)
from vesiclescope.scenarios import finite_donor_boundary_figure_experiment


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the reviewed VesicleScope synthetic run bundle."
    )
    parser.add_argument(
        "--runner",
        default=os.environ.get("VESICLESCOPE_BIOFVM_RUNNER"),
        help="Path to the built native BioFVM transport runner.",
    )
    parser.add_argument(
        "--revision",
        default=os.environ.get("VESICLESCOPE_REVISION"),
        help="Exact VesicleScope commit SHA represented by this run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output JSON bundle path.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if not args.runner:
        raise SystemExit(
            "native runner is required via --runner or "
            "VESICLESCOPE_BIOFVM_RUNNER"
        )
    if not args.revision:
        raise SystemExit(
            "VesicleScope revision is required via --revision or "
            "VESICLESCOPE_REVISION"
        )

    runner = Path(args.runner)
    if not runner.is_file():
        raise SystemExit(f"native runner does not exist: {runner}")

    experiment = finite_donor_boundary_figure_experiment()
    numerics = BioFVMNumerics(
        grid_spacing_micron=5.0,
        time_step_min=0.1,
    )
    result = run_transport(experiment, numerics, runner)
    bundle = SimulationRunBundle(
        vesiclescope_revision=args.revision,
        experiment=experiment,
        numerics=numerics,
        result=result,
    )

    output = write_run_bundle(args.output, bundle)
    if read_run_bundle(output) != bundle:
        raise RuntimeError("written run bundle did not round-trip exactly")

    print(output)
    print(f"payload_sha256={run_bundle_payload_sha256(bundle)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
