"""Command-line interface for the installable VesicleScope headless product."""

from __future__ import annotations

import argparse
import json
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

    execute_batch = experiment_commands.add_parser(
        "run-batch",
        help="Execute an explicit ordered set of experiment documents.",
    )
    execute_batch.add_argument("paths", type=Path, nargs="+")
    execute_batch.add_argument("--runner", type=Path, required=True)
    execute_batch.add_argument("--revision", required=True)
    execute_batch.add_argument("--grid-spacing-micron", type=float, required=True)
    execute_batch.add_argument("--time-step-min", type=float, required=True)
    execute_batch.add_argument("--output-dir", type=Path, required=True)

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
    bundle_compare.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional deterministic JSON file with full stored-run comparison detail.",
    )

    bundle_figure = bundle_commands.add_parser(
        "figure",
        help="Render a completed run bundle without rerunning BioFVM.",
    )
    bundle_figure.add_argument("path", type=Path)
    bundle_figure.add_argument("--output", type=Path, required=True)

    bundle_ensemble = bundle_commands.add_parser(
        "ensemble",
        help="Summarize an explicit empirical ensemble of completed run bundles.",
    )
    bundle_ensemble.add_argument(
        "paths",
        type=Path,
        nargs="+",
        help="Stored run bundles in the intended stable ensemble order.",
    )

    engine = subparsers.add_parser(
        "engine",
        help="Inspect or build the pinned BioFVM transport engine.",
    )
    engine_commands = engine.add_subparsers(dest="engine_command")

    engine_commands.add_parser(
        "status",
        help="Show the reviewed engine pin, toolchain and default cache paths.",
    )

    engine_build = engine_commands.add_parser(
        "build",
        help="Verify/fetch PhysiCell and compile the pinned transport runner.",
    )
    engine_build.add_argument(
        "--physicell-dir",
        type=Path,
        default=None,
        help="Existing verified PhysiCell checkout; omit to use/fetch the default cache.",
    )
    engine_build.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Runner output path; omit to use the default VesicleScope cache.",
    )
    engine_build.add_argument(
        "--no-fetch",
        action="store_true",
        help="Fail instead of fetching when the PhysiCell checkout is missing.",
    )

    workspace = subparsers.add_parser(
        "workspace",
        help="Initialize a local VesicleScope workspace.",
    )
    workspace_commands = workspace.add_subparsers(dest="workspace_command")
    workspace_init = workspace_commands.add_parser(
        "init",
        help="Create experiments/ and runs/ directories.",
    )
    workspace_init.add_argument("path", type=Path)

    ui = subparsers.add_parser(
        "ui",
        help="Start the loopback-only local VesicleScope workspace UI.",
    )
    ui.add_argument("--workspace", type=Path, required=True)
    ui.add_argument("--runner", type=Path, required=True)
    ui.add_argument("--revision", required=True)
    ui.add_argument("--port", type=int, default=8765)
    ui.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the local UI in the default browser.",
    )

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



def _comparison_payload(summary, *, left_digest: str, right_digest: str) -> dict[str, object]:
    endpoint = summary.endpoint
    spatial = summary.spatial
    return {
        "schema": "vesiclescope.stored-run-comparison",
        "version": 1,
        "interpretation": "numerical stored-run comparison only; no biological ranking implied",
        "left_run_payload_sha256": left_digest,
        "right_run_payload_sha256": right_digest,
        "left_experiment_id": endpoint.left_experiment_id,
        "right_experiment_id": endpoint.right_experiment_id,
        "left_revision": summary.left_revision,
        "right_revision": summary.right_revision,
        "quantity_unit": endpoint.quantity_unit,
        "left_numerics": {
            "grid_spacing_micron": endpoint.left_grid_spacing_micron,
            "time_step_min": endpoint.left_time_step_min,
        },
        "right_numerics": {
            "grid_spacing_micron": endpoint.right_grid_spacing_micron,
            "time_step_min": endpoint.right_time_step_min,
        },
        "endpoint": {
            "extracellular_delta_right_minus_left": endpoint.extracellular_delta,
            "internalized_delta_right_minus_left": endpoint.internalized_delta,
            "extracellular_ratio_right_over_left": endpoint.extracellular_ratio_right_over_left,
            "internalized_ratio_right_over_left": endpoint.internalized_ratio_right_over_left,
        },
        "left_series": [
            {
                "time_min": item.time_min,
                "extracellular_quantity": item.extracellular_quantity,
                "internalized_quantity": item.internalized_quantity,
            }
            for item in summary.left_series
        ],
        "right_series": [
            {
                "time_min": item.time_min,
                "extracellular_quantity": item.extracellular_quantity,
                "internalized_quantity": item.internalized_quantity,
            }
            for item in summary.right_series
        ],
        "spatial": {
            "compatible": spatial.compatible,
            "reason": spatial.reason,
            "nx": spatial.nx,
            "ny": spatial.ny,
            "concentration_unit": spatial.concentration_unit,
            "time_min": spatial.time_min,
            "values": list(spatial.values),
            "minimum_difference": spatial.minimum_difference,
            "maximum_difference": spatial.maximum_difference,
            "mean_absolute_difference": spatial.mean_absolute_difference,
        },
    }


def _write_comparison_json(path: Path, payload: dict[str, object]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, allow_nan=False, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output


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




def _print_empirical_quantity(name: str, summary, unit: str) -> None:
    print(f"{name}_member_count: {summary.member_count}")
    print(f"{name}_minimum: {summary.minimum:g} {unit}")
    print(f"{name}_maximum: {summary.maximum:g} {unit}")
    print(f"{name}_mean: {summary.mean:g} {unit}")
    print(f"{name}_median: {summary.median:g} {unit}")
    interval = summary.empirical_percentile_interval_95
    if interval is None:
        print(f"{name}_empirical_percentile_interval_95: unavailable")
    else:
        print(
            f"{name}_empirical_percentile_interval_95: "
            f"[{interval[0]:g}, {interval[1]:g}] {unit}"
        )


def _print_ensemble(summary) -> None:
    print("interpretation: empirical stored-run ensemble; not a confidence interval")
    print(f"quantity_unit: {summary.quantity_unit}")
    print(f"member_count: {len(summary.member_experiment_ids)}")
    print("member_experiment_ids: " + ", ".join(summary.member_experiment_ids))
    _print_empirical_quantity(
        "final_extracellular",
        summary.final_extracellular,
        summary.quantity_unit,
    )
    _print_empirical_quantity(
        "final_internalized",
        summary.final_internalized,
        summary.quantity_unit,
    )


def _print_engine_status(status) -> None:
    print(f"physicell_release: {status.metadata.physicell_release}")
    print(f"physicell_commit: {status.metadata.physicell_commit}")
    print(f"biofvm_version: {status.metadata.biofvm_version}")
    print(f"git: {status.git_path or 'missing'}")
    print(f"g++: {status.compiler_path or 'missing'}")
    print(f"default_physicell_dir: {status.default_physicell_dir}")
    print(f"default_runner_path: {status.default_runner_path}")
    print(f"runner_exists: {'yes' if status.runner_exists else 'no'}")


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
            if args.experiment_command == "run-batch":
                from vesiclescope.workflows import run_experiment_batch

                result = run_experiment_batch(
                    experiment_paths=tuple(args.paths),
                    runner=args.runner,
                    revision=args.revision,
                    output_dir=args.output_dir,
                    grid_spacing_micron=args.grid_spacing_micron,
                    time_step_min=args.time_step_min,
                )
                print(result.manifest_path)
                for path in result.run_paths:
                    print(path)
                return 0
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            print(f"vesiclescope: {exc}", file=sys.stderr)
            return 2


    if args.command == "engine":
        from vesiclescope.engines.installation import (
            build_biofvm_runner,
            engine_setup_status,
        )

        try:
            if args.engine_command == "status":
                _print_engine_status(engine_setup_status())
                return 0
            if args.engine_command == "build":
                output = build_biofvm_runner(
                    physicell_dir=args.physicell_dir,
                    output_path=args.output,
                    fetch_if_missing=not args.no_fetch,
                )
                print(output)
                return 0
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            print(f"vesiclescope: {exc}", file=sys.stderr)
            return 2

    if args.command == "run-bundle":
        from vesiclescope.analysis import compare_run_bundles_detailed, summarize_run_ensemble
        from vesiclescope.run_bundles import read_run_bundle, run_bundle_payload_sha256

        try:
            if args.bundle_command == "inspect":
                _inspect_bundle(read_run_bundle(args.path))
                return 0
            if args.bundle_command == "compare":
                left_bundle = read_run_bundle(args.left)
                right_bundle = read_run_bundle(args.right)
                detailed = compare_run_bundles_detailed(left_bundle, right_bundle)
                _print_comparison(detailed.endpoint)
                print(f"left_series_samples: {len(detailed.left_series)}")
                print(f"right_series_samples: {len(detailed.right_series)}")
                print(
                    "spatial_difference: "
                    + (
                        "compatible"
                        if detailed.spatial.compatible
                        else f"unavailable ({detailed.spatial.reason})"
                    )
                )
                if args.output is not None:
                    output = _write_comparison_json(
                        args.output,
                        _comparison_payload(
                            detailed,
                            left_digest=run_bundle_payload_sha256(left_bundle),
                            right_digest=run_bundle_payload_sha256(right_bundle),
                        ),
                    )
                    print(output)
                return 0
            if args.bundle_command == "figure":
                from vesiclescope.figures import render_stored_run_figure

                output = render_stored_run_figure(
                    read_run_bundle(args.path),
                    args.output,
                )
                print(output)
                return 0
            if args.bundle_command == "ensemble":
                summary = summarize_run_ensemble(
                    tuple(read_run_bundle(path) for path in args.paths)
                )
                _print_ensemble(summary)
                return 0
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            print(f"vesiclescope: {exc}", file=sys.stderr)
            return 2

    if args.command == "workspace":
        from vesiclescope.ui.workspace import Workspace

        try:
            if args.workspace_command == "init":
                workspace = Workspace(args.path).initialize()
                print(workspace.root)
                return 0
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            print(f"vesiclescope: {exc}", file=sys.stderr)
            return 2

    if args.command == "ui":
        from vesiclescope.ui.app import WorkspaceApplication
        from vesiclescope.ui.server import serve_ui
        from vesiclescope.ui.workspace import Workspace

        try:
            app = WorkspaceApplication(
                workspace=Workspace(args.workspace),
                runner=args.runner,
                revision=args.revision,
            )
            serve_ui(
                app,
                port=args.port,
                open_browser=not args.no_browser,
            )
            return 0
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            print(f"vesiclescope: {exc}", file=sys.stderr)
            return 2

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
