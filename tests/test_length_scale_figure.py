import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec("matplotlib"), "matplotlib required")
class LengthScaleFigureTests(unittest.TestCase):
    def test_script_writes_svg_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(
                [sys.executable, "-m", "scripts.generate_length_scale_figure", "--output-dir", directory],
                check=True,
                capture_output=True,
                cwd=Path(__file__).resolve().parents[1],
            )
            svg = (Path(directory) / "colombo-length-scale.svg").read_text()
            self.assertIn("fit-derived publication summaries, not raw data", svg)
            self.assertIn("not separately identifiable", svg)
            record = json.loads((Path(directory) / "colombo-length-scale.json").read_text())
            low, high = record["length_scale_range_micron"]
            self.assertAlmostEqual(low, 16.8, delta=0.2)
            self.assertAlmostEqual(high, 24.7, delta=0.2)
            self.assertTrue(all(item["tail_bound_satisfied"] for item in record["inferences"]))

    def test_rendering_is_deterministic(self) -> None:
        from vesiclescope.figures.length_scale import render_length_scale_figure
        from vesiclescope.validation import colombo_2025_length_scale_constraints

        summary = colombo_2025_length_scale_constraints((10.0,))
        with tempfile.TemporaryDirectory() as directory:
            first = render_length_scale_figure(summary, Path(directory) / "a.svg").read_bytes()
            second = render_length_scale_figure(summary, Path(directory) / "b.svg").read_bytes()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
