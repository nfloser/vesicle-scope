from dataclasses import replace
import unittest

from vesiclescope.analysis import compare_run_bundles
from vesiclescope.engines import (
    BioFVMEngineMetadata,
    BioFVMGrid2D,
    BioFVMNumerics,
    BioFVMRunResult,
    RecipientUptakeSample,
    RecipientUptakeSeries,
    SpatialFieldSnapshot2D,
    TransportSample,
)
from vesiclescope.run_bundles import SimulationRunBundle
from vesiclescope.scenarios import diffusion_uptake_factor_conditions


def bundle(*, extracellular: float, internalized: float) -> SimulationRunBundle:
    experiment = diffusion_uptake_factor_conditions()[4].experiment
    grid = BioFVMGrid2D(
        nx=21,
        ny=21,
        grid_spacing_micron=10.0,
        slice_thickness_micron=25.0,
    )
    voxel_volume = 10.0 * 10.0 * 25.0
    concentration = extracellular / (grid.voxel_count * voxel_volume)
    per_recipient = internalized / len(experiment.uptake_sinks)
    result = BioFVMRunResult(
        experiment_id=experiment.experiment_id,
        concentration_unit="particle_equivalent/micron^3",
        integrated_quantity_unit="particle_equivalent",
        internalized_quantity_unit="particle_equivalent",
        engine=BioFVMEngineMetadata(
            engine="BioFVM",
            physicell_release="1.14.2",
            physicell_commit="dbd3499250141b27600e91e501c54c46f68f2763",
            biofvm_version="1.1.7",
        ),
        grid=grid,
        samples=(
            TransportSample(
                time_min=20.0,
                mean_concentration=concentration,
                min_concentration=concentration,
                max_concentration=concentration,
                integrated_field_quantity=extracellular,
                internalized_field_quantity=internalized,
            ),
        ),
        field_snapshots=(
            SpatialFieldSnapshot2D(
                time_min=20.0,
                values=(concentration,) * grid.voxel_count,
            ),
        ),
        recipient_uptake_series=tuple(
            RecipientUptakeSeries(
                identifier=sink.identifier,
                x_micron=sink.x_micron,
                y_micron=sink.y_micron,
                effective_volume_micron3=sink.effective_volume_micron3,
                uptake_rate_per_min=sink.uptake_rate.value,
                samples=(
                    RecipientUptakeSample(
                        time_min=20.0,
                        internalized_field_quantity=per_recipient,
                    ),
                ),
            )
            for sink in experiment.uptake_sinks
        ),
    )
    return SimulationRunBundle(
        vesiclescope_revision="a" * 40,
        experiment=experiment,
        numerics=BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
        result=result,
    )


class RunComparisonTests(unittest.TestCase):
    def test_reports_endpoint_deltas_and_ratios_without_ranking(self) -> None:
        summary = compare_run_bundles(
            bundle(extracellular=1800.0, internalized=600.0),
            bundle(extracellular=1600.0, internalized=800.0),
        )
        self.assertEqual(summary.extracellular_delta, -200.0)
        self.assertEqual(summary.internalized_delta, 200.0)
        self.assertAlmostEqual(summary.extracellular_ratio_right_over_left, 1600.0 / 1800.0)
        self.assertAlmostEqual(summary.internalized_ratio_right_over_left, 800.0 / 600.0)
        self.assertEqual(summary.quantity_unit, "particle_equivalent")

    def test_zero_left_endpoint_has_undefined_ratio(self) -> None:
        summary = compare_run_bundles(
            bundle(extracellular=0.0, internalized=0.0),
            bundle(extracellular=1.0, internalized=2.0),
        )
        self.assertIsNone(summary.extracellular_ratio_right_over_left)
        self.assertIsNone(summary.internalized_ratio_right_over_left)

    def test_rejects_incompatible_quantity_units(self) -> None:
        left = bundle(extracellular=1.0, internalized=2.0)
        right = bundle(extracellular=1.0, internalized=2.0)
        altered_result = replace(
            right.result,
            integrated_quantity_unit="other_quantity",
            internalized_quantity_unit="other_quantity",
        )
        right = replace(right, result=altered_result)
        with self.assertRaisesRegex(ValueError, "incompatible"):
            compare_run_bundles(left, right)


if __name__ == "__main__":
    unittest.main()
