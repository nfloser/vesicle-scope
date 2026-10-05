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
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("examples", help="List reviewed built-in synthetic examples.")

    run = subparsers.add_parser("run", help="Run a reviewed built-in example.")
    run.add_argument("example", choices=("diffusion-uptake-factor",))
    run.add_argument("--runner", type=Path, required=True)
    run.add_argument("--revision", required=True)
    run.add_argument("--output-dir", type=Path, required=True)

    experiment = subparsers.add_parser(
        "experiment",
        help="Create, validate, inspect and run external experiment documents.",
    )
    experiment_commands = experiment.add_subparsers(dest="experiment_command")

    export = experiment_commands.add_parser("export-example")
    export.add_argument("example", choices=("diffusion-uptake-baseline",))
    export.add_argument("--output", type=Path, required=True)

    validate = experiment_commands.add_parser("validate")
    validate.add_argument("path", type=Path)

    inspect = experiment_commands.add_parser("inspect")
    inspect.add_argument("path", type=Path)

    execute = experiment_commands.add_parser("run")
    execute.add_argument("path", type=Path)
    execute.add_argument("--runner", type=Path, required=True)
    execute.add_argument("--revision", required=True)
    execute.add_argument("--grid-spacing-micron", type=float, required=True)
    execute.add_argument("--time-step-min", type=float, required=True)
    execute.add_argument("--output", type=Path, required=True)

    bundles = subparsers.add_parser(
        "run-bundle",
        help="Inspect or compare completed deterministic run bundles.",
    )
    bundle_commands = bundles.add_subparsers(dest="bundle_command")

    bundle_inspect = bundle_commands.add_parser("inspect")
    bundle_inspect.add_argument("path", type=Path)

    bundle_compare = bundle_commands.add_parser("compare")
    bundle_compare.add_argument("left", type=Path)
    bundle_compare.add_argument("right", type=Path)

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


def _evidence_categories(experiment) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                experiment.diffusion.evidence.value,
                experiment.decay.evidence.value,
                experiment.initial_concentration.evidence.value,
                *(source.release_rate.evidence.value for source in experiment.release_sources),
                *(sink.uptake_rate.evidence.value for sink in experiment.uptake_sinks),
            }
        )
    )


def _inspect_experiment(experiment) -> None:
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
    print(f"evidence_categories: {', '.join(_evidence_categories(experiment))}")


def _inspect_bundle(bundle) -> None:
    final = bundle.result.samples[-1]
    print(f"experiment_id: {bundle.experiment.experiment_id}")
    print(f"vesiclescope_revision: {bundle.vesiclescope_revision}")
    print(
        "engine: "
        f"{bundle.result.engine.engine} "
        f"PhysiCell {bundle.result.engine.physicell_release} "
        f"BioFVM {bundle.result.engine.biofvm_version}"
    )
    print(f"grid_spacing_micron: {bundle.numerics.grid_spacing_micron:g}")
    print(f"time_step_min: {bundle.numerics.time_step_min:g}")
    print(f"samples: {len(bundle.result.samples)}")
    print(
        "final_extracellular_quantity: "
        f"{final.integrated_field_quantity:g} {bundle.result.integrated_quantity_unit}"
    )
    print(
        "final_internalized_quantity: "
        f"{final.internalized_field_quantity:g} {bundle.result.internalized_quantity_unit}"
    )
    print(f"release_sources: {len(bundle.experiment.release_sources)}")
    print(f"uptake_sinks: {len(bundle.experiment.uptake_sinks)}")
    print(f"evidence_categories: {', '.join(_evidence_categories(bundle.experiment))}")


def _print_comparison(summary) -> None:
    print(f"left_experiment_id: {summary.left_experiment_id}")
    print(f"right_experiment_id: {summary.right_experiment_id}")
    print(f"quantity_unit: {summary.quantity_unit}")
    print(
        "grid_spacing_micron: "
        f"left={summary.left_grid_spacing_micron:g}, "
        f"right={summary.right_grid_spacing_micron:g}"
    )
    print(
        "time_step_min: "
        f"left={summary.left_time_step_min:g}, right={summary.right_time_step_min:g}"
    )
    print(f"extracellular_delta_right_minus_left: {summary.extracellular_delta:g}")
    print(f"internalized_delta_right_minus_left: {summary.internalized_delta:g}")
    print(
        "extracellular_ratio_right_over_left: "
        + (
            "undefined"
            if summary.extracellular_ratio_right_over_left is None
            else f"{summary.extracellular_ratio_right_over_left:g}"
        )
    )
    print(
        "internalized_ratio_right_over_left: "
        + (
            "undefined"
            if summary.internalized_ratio_right_over_left is None
            else f"{summary.internalized_ratio_right_over_left:g}"
        )
    )


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
        from vesiclescope.experiment_files import (
            read_experiment_document,
            write_experiment_document,
        )

        try:
            if args.experiment_command == "export-example":
                output = write_experiment_document(args.output, _baseline_experiment())
                print(output)
                return 0
            if args.experiment_command in {"validate", "inspect"}:
                experiment = read_experiment_document(args.path)
                if args.experiment_command == "validate":
                    print(f"valid: {experiment.experiment_id}")
                else:
                    _inspect_experiment(experiment)
                return 0
            if args.experiment_command == "run":
                from vesiclescope.workflows import run_external_experiment

                result = run_external_experiment(
                    experiment_path=args.path,
                    runner=args.runner,
                    revision=args.revision,
                    output_path=args.output,
                    grid_spacing_micron=args.grid_spacing_micron,
                    time_step_min=args.time_step_min,
                )
                print(result.bundle_path)
                return 0
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            print(f"vesiclescope: {exc}", file=sys.stderr)
            return 2

    if args.command == "run-bundle":
        from vesiclescope.analysis import compare_run_bundles
        from vesiclescope.run_bundles import read_run_bundle

        try:
            if args.bundle_command == "inspect":
                _inspect_bundle(read_run_bundle(args.path))
                return 0
            if args.bundle_command == "compare":
                summary = compare_run_bundles(
                    read_run_bundle(args.left),
                    read_run_bundle(args.right),
                )
                _print_comparison(summary)
                return 0
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            print(f"vesiclescope: {exc}", file=sys.stderr)
            return 2

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
