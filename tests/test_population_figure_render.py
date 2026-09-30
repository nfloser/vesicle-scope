import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

from vesiclescope.analysis import analyze_recipient_population
from vesiclescope.engines.biofvm import BioFVMNumerics, run_transport
from vesiclescope.figures import render_recipient_count_figure
from vesiclescope.scenarios import recipient_count_sweep_experiment


RUNNER = os.environ.get("VESICLESCOPE_BIOFVM_RUNNER")
MATPLOTLIB_AVAILABLE = importlib.util.find_spec("matplotlib") is not None


@unittest.skipUnless(
    RUNNER and MATPLOTLIB_AVAILABLE,
    "native runner and Matplotlib are required for figure rendering",
)
class RecipientCountFigureRenderTests(unittest.TestCase):
    @property
    def runner(self) -> Path:
        assert RUNNER is not None
        return Path(RUNNER)

    def test_generates_inspectable_headless_svg_from_normalized_results(self) -> None:
        experiments = tuple(
            recipient_count_sweep_experiment(count)
            for count in (2, 4, 8)
        )
        numerics = BioFVMNumerics(
            grid_spacing_micron=10.0,
            time_step_min=0.1,
        )
        results = tuple(
            run_transport(experiment, numerics, self.runner)
            for experiment in experiments
        )
        summaries = tuple(
            analyze_recipient_population(
                experiment,
                result,
                time_min=experiment.duration_min,
            )
            for experiment, result in zip(experiments, results)
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "recipient-count.svg"
            returned = render_recipient_count_figure(
                experiments,
                results,
                summaries,
                output,
            )

            self.assertEqual(returned, output)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1000)
            svg = output.read_text(encoding="utf-8")

        for required_text in (
            "Synthetic fixed-grid verification",
            "particle_equivalent/micron^3",
            "recipient/mm^2",
            "particle_equivalent",
            "n=2",
            "n=4",
            "n=8",
            "not experimental evidence",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, svg)

        import matplotlib

        self.assertIn("agg", matplotlib.get_backend().lower())


if __name__ == "__main__":
    unittest.main()
