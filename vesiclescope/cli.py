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

    experiment = subparsers.add_parser(
        "experiment",
        help="Create, validate and inspect external experiment documents.",
    )
    experiment_commands = experiment.add_subparsers(dest="experiment_command")

    export = experiment_commands.add_parser(
        "export-example",
        help="Write a reviewed built-in experiment document.",
    )
    export.add_argument(
        "example",
        choices=("diffusion-uptake-baseline",),
        help="Reviewed example experiment to export.",
    )
    export.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output VesicleScope experiment JSON path.",
    )

    validate = experiment_commands.add_parser(
        "validate",
        help="Validate an external experiment document.",
    )
    validate.add_argument("path", type=Path)

    inspect = experiment_commands.add_parser(
        "inspect",
        help="Print a concise scientific summary of an experiment document.",
    )
    inspect.add_argument("path", type=Path)

    return parser


def _print_examples() -> None:
    print("diffusion-uptake-factor")
    print("  3×3 controlled synthetic diffusion × uptake model-behaviour experiment")
    print("  Output: summary.json, diffusion-uptake.svg, and nine deterministic run bundles")
    print("  Scientific status: synthetic benchmark; not experimental evidence")
    print("diffusion-uptake-baseline")
    print("  Single 1× diffusion / 1× uptake experiment document template")
    print("  Export with: vesiclescope experiment export-example diffusion-uptake-baseline")


def _baseline_experiment():
    from vesiclescope.scenarios import diffusion_uptake_factor_conditions

    return next(
        condition.experiment
        for condition in diffusion_uptake_factor_conditions()
        if condition.diffusion_factor == 1.0 and condition.uptake_factor == 1.0
    )


def _inspect_experiment(experiment) -> None:
    evidence = sorted(
        {
            experiment.diffusion.evidence.value,
            experiment.decay.evidence.value,
            experiment.initial_concentration.evidence.value,
            *(source.release_rate.evidence.value for source in experiment.release_sources),
            *(sink.uptake_rate.evidence.value for sink in experiment.uptake_sinks),
        }
    )
    print(f"experiment_id: {experiment.experiment_id}")
    print(
        "domain_micron: "
        f"{experiment.domain.width_micron:g} × {experiment.domain.height_micron:g} "
        f"× {experiment.domain.slice_thickness_micron:g}"
    )
    print(f"duration_min: {experiment.duration_min:g}")
    print(f"sample_every_min: {experiment.sample_every_min:g}")
    print(f"boundary: {experiment.boundary.value}")
    print(f"release_sources: {len(experiment.release_sources)}")
    print(f"uptake_sinks: {len(experiment.uptake_sinks)}")
    print(f"evidence_categories: {', '.join(evidence)}")


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

    if args.command == "experiment":
        if args.experiment_command is None:
            experiment_parser = next(
                action
                for action in parser._actions
                if isinstance(action, argparse._SubParsersAction)
            ).choices["experiment"]
            experiment_parser.print_help()
            return 0

        from vesiclescope.experiment_files import (
            read_experiment_document,
            write_experiment_document,
        )

        try:
            if args.experiment_command == "export-example":
                output = write_experiment_document(args.output, _baseline_experiment())
                print(output)
                return 0

            experiment = read_experiment_document(args.path)
            if args.experiment_command == "validate":
                print(f"valid: {experiment.experiment_id}")
                return 0
            if args.experiment_command == "inspect":
                _inspect_experiment(experiment)
                return 0
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            print(f"vesiclescope: {exc}", file=sys.stderr)
            return 2

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
