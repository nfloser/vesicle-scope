import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from vesiclescope.engines import BioFVMNumerics, run_transport
from vesiclescope.figures import render_donor_boundary_figure
from vesiclescope.scenarios import finite_donor_boundary_figure_experiment


RUNNER = os.environ.get("VESICLESCOPE_BIOFVM_RUNNER")
MATPLOTLIB_AVAILABLE = importlib.util.find_spec("matplotlib") is not None


@unittest.skipUnless(
    RUNNER and MATPLOTLIB_AVAILABLE,
    "native runner and Matplotlib are required for figure rendering",
)
class DonorBoundaryFigureRenderTests(unittest.TestCase):
    @property
    def runner(self) -> Path:
        assert RUNNER is not None
        return Path(RUNNER)

    def test_generates_inspectable_boundary_profile_svg(self) -> None:
        experiment = finite_donor_boundary_figure_experiment()
        result = run_transport(
            experiment,
            BioFVMNumerics(
                grid_spacing_micron=5.0,
                time_step_min=0.1,
            ),
            self.runner,
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "donor-boundary-profile.svg"
            returned = render_donor_boundary_figure(
                experiment,
                result,
                output,
                time_min=experiment.duration_min,
                max_distance_micron=80.0,
            )

            self.assertEqual(returned, output)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1000)
            svg = output.read_text(encoding="utf-8")

        for required_text in (
            "Synthetic donor-boundary transport verification",
            "simulated concentration",
            "5 micron public-code bins",
            "10 micron paper-described zones",
            "not experimental evidence",
            "particle_equivalent/micron^3",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, svg)

        root = ET.fromstring(svg)
        groups = {
            element.attrib.get("id"): element
            for element in root.iter()
            if element.tag.endswith("g") and element.attrib.get("id")
        }
        self.assertIn("donor-boundary", groups)
        for distance in (20, 40, 60, 80):
            self.assertIn(f"boundary-ring-{distance}", groups)

        import matplotlib

        self.assertIn("agg", matplotlib.get_backend().lower())


if __name__ == "__main__":
    unittest.main()
