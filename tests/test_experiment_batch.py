from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from vesiclescope.experiment_files import write_experiment_document
from vesiclescope.scenarios import diffusion_uptake_factor_conditions
from vesiclescope.workflows import run_experiment_batch


REVISION = "a" * 40


def write_members(directory: Path, *, duplicate: bool = False) -> tuple[Path, Path]:
    conditions = diffusion_uptake_factor_conditions()
    first = conditions[0].experiment
    second = first if duplicate else conditions[1].experiment
    left = write_experiment_document(directory / "left.json", first)
    right = write_experiment_document(directory / "right.json", second)
    return left, right


def fake_completed_result(output_path: Path):
    Path(output_path).write_text("{}\n", encoding="utf-8")
    return SimpleNamespace(
        bundle_path=Path(output_path),
        bundle=SimpleNamespace(
            vesiclescope_revision=REVISION,
            numerics=SimpleNamespace(
                grid_spacing_micron=10.0,
                time_step_min=0.1,
            ),
        ),
    )


class ExperimentBatchTests(unittest.TestCase):
    def test_rejects_duplicate_experiment_ids_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_members(root, duplicate=True)
            runner = root / "runner"
            runner.write_text("", encoding="utf-8")

            with patch(
                "vesiclescope.workflows.experiment_batch.run_external_experiment"
            ) as execute:
                with self.assertRaisesRegex(ValueError, "duplicate experiment_id"):
                    run_experiment_batch(
                        experiment_paths=paths,
                        runner=runner,
                        revision=REVISION,
                        output_dir=root / "out",
                        grid_spacing_micron=10.0,
                        time_step_min=0.1,
                    )

            execute.assert_not_called()

    def test_rejects_existing_member_output_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_members(root)
            runner = root / "runner"
            runner.write_text("", encoding="utf-8")
            output = root / "out"
            output.mkdir()
            collision = output / "001-synthetic.diffusion-uptake.d0.5.u0.5.run.json"
            collision.write_text("occupied", encoding="utf-8")

            with patch(
                "vesiclescope.workflows.experiment_batch.run_external_experiment"
            ) as execute:
                with self.assertRaisesRegex(ValueError, "already exists"):
                    run_experiment_batch(
                        experiment_paths=paths,
                        runner=runner,
                        revision=REVISION,
                        output_dir=output,
                        grid_spacing_micron=10.0,
                        time_step_min=0.1,
                    )

            execute.assert_not_called()

    def test_failed_member_never_writes_completed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_members(root)
            runner = root / "runner"
            runner.write_text("", encoding="utf-8")
            output = root / "out"

            first = SimpleNamespace(
                bundle_path=output / "001.run.json",
                bundle=SimpleNamespace(
                    vesiclescope_revision=REVISION,
                    numerics=SimpleNamespace(
                        grid_spacing_micron=10.0,
                        time_step_min=0.1,
                    ),
                ),
            )
            with patch(
                "vesiclescope.workflows.experiment_batch.run_external_experiment",
                side_effect=(first, RuntimeError("member failed")),
            ):
                with self.assertRaisesRegex(RuntimeError, "member failed"):
                    run_experiment_batch(
                        experiment_paths=paths,
                        runner=runner,
                        revision=REVISION,
                        output_dir=output,
                        grid_spacing_micron=10.0,
                        time_step_min=0.1,
                    )

            self.assertFalse((output / "batch-manifest.json").exists())

    def test_completed_manifest_preserves_order_and_bundle_digests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_members(root)
            runner = root / "runner"
            runner.write_text("", encoding="utf-8")
            output = root / "out"

            def execute(**kwargs):
                return fake_completed_result(kwargs["output_path"])

            with patch(
                "vesiclescope.workflows.experiment_batch.run_external_experiment",
                side_effect=execute,
            ), patch(
                "vesiclescope.workflows.experiment_batch.run_bundle_payload_sha256",
                side_effect=("1" * 64, "2" * 64),
            ):
                result = run_experiment_batch(
                    experiment_paths=paths,
                    runner=runner,
                    revision=REVISION,
                    output_dir=output,
                    grid_spacing_micron=10.0,
                    time_step_min=0.1,
                )

            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [member["input_filename"] for member in manifest["members"]],
                ["left.json", "right.json"],
            )
            self.assertEqual(
                [member["experiment_id"] for member in manifest["members"]],
                [
                    "synthetic.diffusion-uptake.d0.5.u0.5",
                    "synthetic.diffusion-uptake.d1.u0.5",
                ],
            )
            self.assertEqual(
                [member["run_bundle_payload_sha256"] for member in manifest["members"]],
                ["1" * 64, "2" * 64],
            )
            self.assertEqual(
                [path.name for path in result.run_paths],
                [
                    "001-synthetic.diffusion-uptake.d0.5.u0.5.run.json",
                    "002-synthetic.diffusion-uptake.d1.u0.5.run.json",
                ],
            )
            self.assertEqual(
                manifest["scientific_status"],
                "explicit input batch; no sampling or biological distribution implied",
            )

    def test_long_experiment_id_produces_bounded_deterministic_filename(self) -> None:
        from vesiclescope.workflows.experiment_batch import _safe_output_filename

        experiment_id = "experiment." + ("very-long-component-" * 20)
        first = _safe_output_filename(1, experiment_id)
        second = _safe_output_filename(1, experiment_id)

        self.assertEqual(first, second)
        self.assertLess(len(first), 120)
        self.assertTrue(first.startswith("001-experiment."))
        self.assertTrue(first.endswith(".run.json"))


if __name__ == "__main__":
    unittest.main()
