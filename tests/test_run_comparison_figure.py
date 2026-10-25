from dataclasses import replace
import importlib.util
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from urllib.parse import urlencode
from urllib.request import urlopen

from vesiclescope.engines import SpatialFieldSnapshot2D
from vesiclescope.figures import (
    prepare_run_comparison_figure_data,
    render_run_comparison_figure,
)
from vesiclescope.run_bundles import serialize_run_bundle
from vesiclescope.ui.app import WorkspaceApplication
from vesiclescope.ui.server import create_server
from vesiclescope.ui.workspace import Workspace
from test_stored_run_figure import bundle


def comparison_bundles():
    left = bundle()
    sample = left.result.samples[-1]
    right_values = tuple(
        value + 0.5 for value in left.result.field_snapshots[-1].values
    )
    voxel_volume = (
        left.result.grid.grid_spacing_micron**2
        * left.result.grid.slice_thickness_micron
    )
    right_sample = replace(
        sample,
        mean_concentration=sum(right_values) / len(right_values),
        min_concentration=min(right_values),
        max_concentration=max(right_values),
        integrated_field_quantity=sum(right_values) * voxel_volume,
    )
    right = replace(
        left,
        vesiclescope_revision="b" * 40,
        result=replace(
            left.result,
            samples=(right_sample,),
            field_snapshots=(
                SpatialFieldSnapshot2D(
                    sample.time_min,
                    right_values,
                ),
            ),
        ),
    )
    return left, right


class RunComparisonFigureDataTests(unittest.TestCase):
    def test_uses_exact_persisted_snapshots_and_stable_shared_scale(self) -> None:
        left, right = comparison_bundles()

        data = prepare_run_comparison_figure_data(
            left,
            left.experiment.duration_min,
            right,
            right.experiment.duration_min,
            left_name="baseline.run.json",
            right_name="variant.run.json",
        )

        self.assertEqual(data.left_time_min, left.experiment.duration_min)
        self.assertEqual(data.right_time_min, right.experiment.duration_min)
        self.assertAlmostEqual(
            data.right_rows[0][0] - data.left_rows[0][0],
            0.5,
        )
        self.assertAlmostEqual(data.difference_rows[0][0], 0.5)
        self.assertEqual(
            data.shared_maximum,
            max(right.result.field_snapshots[-1].values),
        )
        self.assertEqual(data.left_revision, "a" * 40)
        self.assertEqual(data.right_revision, "b" * 40)

    def test_rejects_unstored_times_without_interpolation(self) -> None:
        left, right = comparison_bundles()
        with self.assertRaisesRegex(ValueError, "not stored exactly"):
            prepare_run_comparison_figure_data(left, 1.0, right, 1.0)


@unittest.skipUnless(
    importlib.util.find_spec("matplotlib") is not None,
    "Matplotlib is required for SVG rendering",
)
class RunComparisonFigureRenderTests(unittest.TestCase):
    def test_svg_is_deterministic_and_identifies_right_minus_left(self) -> None:
        left, right = comparison_bundles()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.svg"
            second = Path(directory) / "second.svg"
            for output in (first, second):
                render_run_comparison_figure(
                    left,
                    left.experiment.duration_min,
                    right,
                    right.experiment.duration_min,
                    output,
                    left_name="baseline.run.json",
                    right_name="variant.run.json",
                )
            first_bytes = first.read_bytes()
            second_bytes = second.read_bytes()

        self.assertEqual(first_bytes, second_bytes)
        svg = first_bytes.decode("utf-8")
        for required in (
            "VesicleScope stored-run comparison",
            "baseline.run.json",
            "variant.run.json",
            "Difference: right − left",
            "Stable shared concentration scale",
            "not experimental evidence",
        ):
            self.assertIn(required, svg)

    def test_loopback_endpoint_exports_selected_exact_time_svg(self) -> None:
        left, right = comparison_bundles()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root / "workspace").initialize()
            workspace.run_path("baseline.run.json").write_bytes(
                serialize_run_bundle(left)
            )
            workspace.run_path("variant.run.json").write_bytes(
                serialize_run_bundle(right)
            )
            runner = root / "runner"
            runner.touch()
            app = WorkspaceApplication(workspace, runner, "c" * 40)
            server = create_server(app, port=0)
            _, port = server.server_address
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            query = urlencode(
                {
                    "left": "baseline.run.json",
                    "right": "variant.run.json",
                    "left_time_min": left.experiment.duration_min,
                    "right_time_min": right.experiment.duration_min,
                }
            )
            try:
                with urlopen(
                    f"http://127.0.0.1:{port}/download/comparison-figure?{query}",
                    timeout=30,
                ) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(
                        response.headers.get_content_type(),
                        "image/svg+xml",
                    )
                    self.assertIn("attachment;", response.headers["Content-Disposition"])
                    svg = response.read().decode("utf-8")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        self.assertIn("VesicleScope stored-run comparison", svg)
        self.assertIn("baseline.run.json", svg)


if __name__ == "__main__":
    unittest.main()
