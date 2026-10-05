import importlib.util
from pathlib import Path
import tempfile
import unittest

from vesiclescope.analysis import DiffusionUptakeSummary
from vesiclescope.figures import (
    prepare_diffusion_uptake_figure_data,
    render_diffusion_uptake_figure,
)


def summary(diffusion: float, uptake: float, fraction: float) -> DiffusionUptakeSummary:
    return DiffusionUptakeSummary(
        diffusion_factor=diffusion,
        uptake_factor=uptake,
        diffusion_value=100.0 * diffusion,
        diffusion_unit="micron^2/min",
        uptake_value=0.5 * uptake,
        uptake_unit="1/min",
        total_released_quantity=2400.0,
        final_extracellular_quantity=2400.0 * (1.0 - fraction),
        final_internalized_quantity=2400.0 * fraction,
        extracellular_fraction=1.0 - fraction,
        internalized_fraction=fraction,
        quantity_unit="particle_equivalent",
    )


SUMMARIES = tuple(
    summary(diffusion, uptake, 0.05 + 0.1 * uptake + 0.05 * diffusion)
    for uptake in (0.5, 1.0, 2.0)
    for diffusion in (0.5, 1.0, 2.0)
)


class DiffusionUptakeFigureDataTests(unittest.TestCase):
    def test_matrix_order_is_uptake_rows_and_diffusion_columns(self) -> None:
        data = prepare_diffusion_uptake_figure_data(SUMMARIES)
        self.assertEqual(data.diffusion_factors, (0.5, 1.0, 2.0))
        self.assertEqual(data.uptake_factors, (0.5, 1.0, 2.0))
        self.assertEqual(
            data.internalized_fraction_rows[0],
            tuple(item.internalized_fraction for item in SUMMARIES[:3]),
        )

    def test_rejects_missing_factor_condition(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly nine"):
            prepare_diffusion_uptake_figure_data(SUMMARIES[:-1])


@unittest.skipUnless(
    importlib.util.find_spec("matplotlib") is not None,
    "Matplotlib is required for SVG rendering",
)
class DiffusionUptakeFigureRenderTests(unittest.TestCase):
    def test_svg_keeps_scientific_status_labels_inspectable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "diffusion-uptake.svg"
            render_diffusion_uptake_figure(SUMMARIES, output)
            svg = output.read_text(encoding="utf-8")

        for text in (
            "Synthetic diffusion × uptake factor experiment",
            "Fraction of released model quantity internalized",
            "not experimental evidence",
            "relative to synthetic baselines",
            "uptake 0.5×",
            "uptake 1×",
            "uptake 2×",
        ):
            self.assertIn(text, svg)


if __name__ == "__main__":
    unittest.main()
