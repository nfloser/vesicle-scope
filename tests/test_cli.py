from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from vesiclescope import __version__
from vesiclescope.cli import main


class CliTests(unittest.TestCase):
    def test_default_command_prints_help(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = main([])
        self.assertEqual(status, 0)
        self.assertIn("usage: vesiclescope", output.getvalue())
        self.assertIn("examples", output.getvalue())
        self.assertIn("run", output.getvalue())

    def test_examples_are_discoverable_without_running_simulation(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = main(["examples"])
        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertIn("diffusion-uptake-factor", text)
        self.assertIn("synthetic benchmark", text)
        self.assertIn("not experimental evidence", text)

    def test_version_matches_package_version(self) -> None:
        parser_output = StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stdout(parser_output):
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn(__version__, parser_output.getvalue())

    def test_run_reports_missing_native_runner_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            error = StringIO()
            with redirect_stderr(error):
                status = main(
                    [
                        "run",
                        "diffusion-uptake-factor",
                        "--runner",
                        str(Path(directory) / "missing-runner"),
                        "--revision",
                        "a" * 40,
                        "--output-dir",
                        str(Path(directory) / "output"),
                    ]
                )
        self.assertEqual(status, 2)
        self.assertIn("native runner does not exist", error.getvalue())


    def test_experiment_export_validate_and_inspect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiment.json"

            export_output = StringIO()
            with redirect_stdout(export_output):
                export_status = main(
                    [
                        "experiment",
                        "export-example",
                        "diffusion-uptake-baseline",
                        "--output",
                        str(path),
                    ]
                )
            self.assertEqual(export_status, 0)
            self.assertTrue(path.is_file())

            validate_output = StringIO()
            with redirect_stdout(validate_output):
                validate_status = main(["experiment", "validate", str(path)])
            self.assertEqual(validate_status, 0)
            self.assertIn("valid: synthetic.diffusion-uptake.d1.u1", validate_output.getvalue())

            inspect_output = StringIO()
            with redirect_stdout(inspect_output):
                inspect_status = main(["experiment", "inspect", str(path)])
            self.assertEqual(inspect_status, 0)
            summary = inspect_output.getvalue()
            self.assertIn("experiment_id: synthetic.diffusion-uptake.d1.u1", summary)
            self.assertIn("release_sources: 1", summary)
            self.assertIn("uptake_sinks: 8", summary)
            self.assertIn("synthetic_benchmark", summary)




    def test_run_bundle_compare_can_write_deterministic_detailed_json(self) -> None:
        endpoint = SimpleNamespace(
            left_experiment_id="left.exp",
            right_experiment_id="right.exp",
            quantity_unit="particle_equivalent",
            left_grid_spacing_micron=10.0,
            right_grid_spacing_micron=10.0,
            left_time_step_min=0.1,
            right_time_step_min=0.1,
            extracellular_delta=-2.0,
            internalized_delta=2.0,
            extracellular_ratio_right_over_left=0.9,
            internalized_ratio_right_over_left=1.1,
        )
        sample_left = SimpleNamespace(
            time_min=0.0,
            extracellular_quantity=0.0,
            internalized_quantity=0.0,
        )
        sample_right = SimpleNamespace(
            time_min=0.0,
            extracellular_quantity=0.0,
            internalized_quantity=0.0,
        )
        spatial = SimpleNamespace(
            compatible=True,
            reason=None,
            nx=2,
            ny=1,
            concentration_unit="particle_equivalent/micron^3",
            time_min=20.0,
            values=(1.0, -1.0),
            minimum_difference=-1.0,
            maximum_difference=1.0,
            mean_absolute_difference=1.0,
        )
        detailed = SimpleNamespace(
            endpoint=endpoint,
            left_revision="a" * 40,
            right_revision="b" * 40,
            left_series=(sample_left,),
            right_series=(sample_right,),
            spatial=spatial,
        )

        with tempfile.TemporaryDirectory() as directory, patch(
            "vesiclescope.run_bundles.read_run_bundle",
            side_effect=("left-bundle", "right-bundle"),
        ), patch(
            "vesiclescope.run_bundles.run_bundle_payload_sha256",
            side_effect=("1" * 64, "2" * 64),
        ), patch(
            "vesiclescope.analysis.compare_run_bundles_detailed",
            return_value=detailed,
        ):
            output_path = Path(directory) / "comparison.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = main(
                    [
                        "run-bundle",
                        "compare",
                        "left.json",
                        "right.json",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(status, 0)
            self.assertTrue(output_path.is_file())
            document = output_path.read_text(encoding="utf-8")
            self.assertIn('"schema": "vesiclescope.stored-run-comparison"', document)
            self.assertIn('"left_run_payload_sha256": "' + "1" * 64 + '"', document)
            self.assertIn('"right_run_payload_sha256": "' + "2" * 64 + '"', document)
            self.assertIn("spatial_difference: compatible", stdout.getvalue())


    def test_archive_create_and_inspect_round_trip_without_solver(self) -> None:
        from vesiclescope.experiment_files import write_experiment_document
        from vesiclescope.scenarios import diffusion_uptake_factor_conditions

        experiment = diffusion_uptake_factor_conditions()[4].experiment
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            experiment_path = root / "experiment.json"
            archive_path = root / "project.omex"
            write_experiment_document(experiment_path, experiment)

            create_output = StringIO()
            with redirect_stdout(create_output):
                create_status = main(
                    [
                        "archive",
                        "create",
                        str(experiment_path),
                        "--output",
                        str(archive_path),
                    ]
                )
            self.assertEqual(create_status, 0)
            self.assertTrue(archive_path.is_file())

            inspect_output = StringIO()
            with redirect_stdout(inspect_output):
                inspect_status = main(
                    ["archive", "inspect", str(archive_path)]
                )
            self.assertEqual(inspect_status, 0)
            text = inspect_output.getvalue()
            self.assertIn(f"experiment_id: {experiment.experiment_id}", text)
            self.assertIn("stored_runs: 0", text)
            self.assertIn("container: COMBINE Archive / OMEX", text)
            self.assertIn("sedml_compatibility: not claimed", text)
            self.assertIn("not experimental evidence", text)

    def test_run_bundle_ensemble_reports_empirical_interpretation(self) -> None:
        quantity = SimpleNamespace(
            member_count=2,
            minimum=1.0,
            maximum=3.0,
            mean=2.0,
            median=2.0,
            empirical_percentile_interval_95=None,
        )
        summary = SimpleNamespace(
            member_experiment_ids=("member.a", "member.b"),
            quantity_unit="particle_equivalent",
            final_extracellular=quantity,
            final_internalized=quantity,
        )
        with patch(
            "vesiclescope.run_bundles.read_run_bundle",
            side_effect=(object(), object()),
        ), patch(
            "vesiclescope.analysis.summarize_run_ensemble",
            return_value=summary,
        ):
            output = StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        "run-bundle",
                        "ensemble",
                        "a.json",
                        "b.json",
                    ]
                )

        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertIn(
            "interpretation: empirical stored-run ensemble; not a confidence interval",
            text,
        )
        self.assertIn("member_experiment_ids: member.a, member.b", text)
        self.assertIn(
            "final_extracellular_empirical_percentile_interval_95: unavailable",
            text,
        )

    def test_engine_status_is_available_without_network(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = main(["engine", "status"])
        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertIn("physicell_release:", text)
        self.assertIn("physicell_commit:", text)
        self.assertIn("biofvm_version:", text)
        self.assertIn("default_runner_path:", text)


    def test_workspace_init_creates_product_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            output = StringIO()
            with redirect_stdout(output):
                status = main(["workspace", "init", str(workspace)])
            self.assertEqual(status, 0)
            self.assertTrue((workspace / "experiments").is_dir())
            self.assertTrue((workspace / "runs").is_dir())
            self.assertIn(str(workspace.resolve()), output.getvalue())

    def test_ui_reports_missing_runner_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            error = StringIO()
            with redirect_stderr(error):
                status = main(
                    [
                        "ui",
                        "--workspace",
                        str(Path(directory) / "workspace"),
                        "--runner",
                        str(Path(directory) / "missing-runner"),
                        "--revision",
                        "a" * 40,
                        "--no-browser",
                    ]
                )
            self.assertEqual(status, 2)
            self.assertIn("native runner does not exist", error.getvalue())



if __name__ == "__main__":
    unittest.main()
