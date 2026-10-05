"""Compatibility entry point for the reviewed diffusion × uptake workflow."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from vesiclescope.workflows import run_diffusion_uptake_factor_experiment


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
        help="Directory for deterministic workflow artifacts.",
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

    result = run_diffusion_uptake_factor_experiment(
        runner=Path(args.runner),
        revision=args.revision,
        output_dir=args.output_dir,
    )
    print(result.summary_path)
    print(result.figure_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
