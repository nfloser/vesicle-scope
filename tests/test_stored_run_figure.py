from dataclasses import replace
import importlib.util
from pathlib import Path
import tempfile
import unittest

from vesiclescope.engines import BioFVMNumerics, SpatialFieldSnapshot2D, TransportSample
from vesiclescope.figures import (
    prepare_stored_run_figure_data,
    render_stored_run_figure,
)
from vesiclescope.run_bundles import SimulationRunBundle
from vesiclescope.scenarios import finite_donor_boundary_figure_experiment
from test_run_bundles import result_for


def bundle() -> SimulationRunBundle:
    experiment = finite_donor_boundary_figure_experiment()
    numerics = BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1)
    return SimulationRunBundle(
        vesiclescope_revision="a" * 40,
        experiment=experiment,
        numerics=numerics,
        result=result_for(experiment, grid_spacing_micron=20.0),
    )


class StoredRunFigureDataTests(unittest.TestCase):
    def test_uses_only_persisted_normalized_contracts(self) -> None:
        data = prepare_stored_run_figure_data(bundle())
        self.assertEqual(data.experiment_id, bundle().experiment.experiment_id)
        self.assertEqual(data.scientific_status, "synthetic benchmark; not experimental evidence")
        self.assertEqual(data.evidence_categories, ("synthetic_benchmark",))
        self.assertEqual(len(data.field_rows), bundle().result.grid.ny)
        self.assertEqual(len(data.field_rows[0]), bundle().result.grid.nx)
        self.assertEqual(data.sample_times_min, (bundle().experiment.duration_min,))
        self.assertIn("BioFVM", data.engine_label)
        self.assertEqual(data.vesiclescope_revision, "a" * 40)

    def test_requires_a_final_field_snapshot(self) -> None:
        original = bundle()
        final_sample = original.result.samples[-1]
        early_sample = TransportSample(
            time_min=0.0,
            mean_concentration=final_sample.mean_concentration,
            min_concentration=final_sample.min_concentration,
            max_concentration=final_sample.max_concentration,
            integrated_field_quantity=final_sample.integrated_field_quantity,
            internalized_field_quantity=0.0,
        )
        early_snapshot = SpatialFieldSnapshot2D(
            time_min=0.0,
            values=original.result.field_snapshots[-1].values,
        )
        altered_result = replace(
            original.result,
            samples=(early_sample, final_sample),
            field_snapshots=(early_snapshot,),
        )
        altered_bundle = SimulationRunBundle(
            vesiclescope_revision=original.vesiclescope_revision,
            experiment=original.experiment,
            numerics=original.numerics,
            result=altered_result,
        )
        with self.assertRaisesRegex(ValueError, "final field snapshot"):
            prepare_stored_run_figure_data(altered_bundle)


@unittest.skipUnless(
    importlib.util.find_spec("matplotlib") is not None,
    "Matplotlib is required for SVG rendering",
)
class StoredRunFigureRenderTests(unittest.TestCase):
    def test_svg_is_deterministic_and_keeps_provenance_inspectable(self) -> None:
        run = bundle()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.svg"
            second = Path(directory) / "second.svg"
            render_stored_run_figure(run, first)
            render_stored_run_figure(run, second)
            first_bytes = first.read_bytes()
            second_bytes = second.read_bytes()

        self.assertEqual(first_bytes, second_bytes)
        svg = first_bytes.decode("utf-8")
        for required in (
            "VesicleScope stored-run overview",
            "synthetic benchmark; not experimental evidence",
            "Stored normalized time series",
            "BioFVM",
            "revision " + "a" * 40,
        ):
            self.assertIn(required, svg)


if __name__ == "__main__":
    unittest.main()
