"""Command-line interface for the installable VesicleScope headless product."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from vesiclescope import __version__


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vesiclescope",
        description=(
            "Evidence-grounded computational research software for "
            "extracellular-vesicle transport."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "examples",
        help="List reviewed built-in synthetic examples.",
    )

    run = subparsers.add_parser(
        "run",
        help="Run a reviewed built-in example.",
    )
    run.add_argument(
        "example",
        choices=("diffusion-uptake-factor",),
        help="Reviewed built-in example identifier.",
    )
    run.add_argument(
        "--runner",
        type=Path,
        required=True,
        help="Path to the built native BioFVM transport runner.",
    )
    run.add_argument(
        "--revision",
        required=True,
        help="Exact 40- or 64-character VesicleScope commit SHA represented by the run.",
    )
    run.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for deterministic run artifacts.",
    )
    return parser


def _print_examples() -> None:
    print("diffusion-uptake-factor")
    print("  3×3 controlled synthetic diffusion × uptake model-behaviour experiment")
    print("  Output: summary.json, diffusion-uptake.svg, and nine deterministic run bundles")
    print("  Scientific status: synthetic benchmark; not experimental evidence")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "examples":
        _print_examples()
        return 0

    if args.command == "run":
        if args.example != "diffusion-uptake-factor":
            parser.error(f"unsupported example: {args.example}")

        from vesiclescope.workflows import run_diffusion_uptake_factor_experiment

        try:
            result = run_diffusion_uptake_factor_experiment(
                runner=args.runner,
                revision=args.revision,
                output_dir=args.output_dir,
            )
        except (RuntimeError, ValueError) as exc:
            print(f"vesiclescope: {exc}", file=sys.stderr)
            return 2

        print(result.summary_path)
        print(result.figure_path)
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
