from dataclasses import replace
import unittest

from vesiclescope.analysis import compare_run_bundles_detailed
from vesiclescope.engines import (
    BioFVMEngineMetadata,
    BioFVMGrid2D,
    BioFVMNumerics,
    BioFVMRunResult,
    SpatialFieldSnapshot2D,
    TransportSample,
)
from vesiclescope.run_bundles import SimulationRunBundle
from vesiclescope.scenarios import diffusion_uptake_factor_conditions


def bundle(
    *,
    revision: str = "a" * 40,
    sample_times: tuple[float, ...] = (0.0, 20.0),
    extracellular: tuple[float, ...] = (0.0, 1800.0),
    internalized: tuple[float, ...] = (0.0, 600.0),
    field_values: tuple[float, ...] | None = None,
    concentration_unit: str = "particle_equivalent/micron^3",
    quantity_unit: str = "particle_equivalent",
    grid_spacing: float = 10.0,
    slice_thickness: float = 25.0,
) -> SimulationRunBundle:
    experiment = diffusion_uptake_factor_conditions()[4].experiment
    nx = round(experiment.domain.width_micron / grid_spacing)
    ny = round(experiment.domain.height_micron / grid_spacing)
    grid = BioFVMGrid2D(
        nx=nx,
        ny=ny,
        grid_spacing_micron=grid_spacing,
        slice_thickness_micron=slice_thickness,
    )
    if field_values is None:
        field_values = tuple(0.001 for _ in range(grid.voxel_count))
    samples = tuple(
        TransportSample(
            time_min=time,
            mean_concentration=0.0 if extra == 0.0 else 0.001,
            min_concentration=0.0,
            max_concentration=0.001,
            integrated_field_quantity=extra,
            internalized_field_quantity=inside,
        )
        for time, extra, inside in zip(sample_times, extracellular, internalized)
    )
    result = BioFVMRunResult(
        experiment_id=experiment.experiment_id,
        concentration_unit=concentration_unit,
        integrated_quantity_unit=quantity_unit,
        internalized_quantity_unit=quantity_unit,
        engine=BioFVMEngineMetadata(
            engine="BioFVM",
            physicell_release="1.14.2",
            physicell_commit="dbd3499250141b27600e91e501c54c46f68f2763",
            biofvm_version="1.1.7",
        ),
        grid=grid,
        samples=samples,
        field_snapshots=(
            SpatialFieldSnapshot2D(
                time_min=sample_times[-1],
                values=field_values,
            ),
        ),
        recipient_uptake_series=(),
    )
    return SimulationRunBundle(
        vesiclescope_revision=revision,
        experiment=experiment,
        numerics=BioFVMNumerics(
            grid_spacing_micron=grid_spacing,
            time_step_min=0.1,
        ),
        result=result,
    )


class DetailedRunComparisonTests(unittest.TestCase):
    def test_identical_runs_have_zero_spatial_difference(self) -> None:
        left = bundle()
        summary = compare_run_bundles_detailed(left, left)

        self.assertEqual(summary.endpoint.extracellular_delta, 0.0)
        self.assertEqual(summary.endpoint.internalized_delta, 0.0)
        self.assertTrue(summary.spatial.compatible)
        self.assertIsNone(summary.spatial.reason)
        self.assertEqual(len(summary.spatial.values), left.result.grid.voxel_count)
        self.assertTrue(all(value == 0.0 for value in summary.spatial.values))
        self.assertEqual(summary.spatial.minimum_difference, 0.0)
        self.assertEqual(summary.spatial.maximum_difference, 0.0)
        self.assertEqual(summary.spatial.mean_absolute_difference, 0.0)

    def test_preserves_each_stored_time_axis_without_interpolation(self) -> None:
        left = bundle(
            sample_times=(0.0, 10.0, 20.0),
            extracellular=(0.0, 1000.0, 1800.0),
            internalized=(0.0, 200.0, 600.0),
        )
        right = bundle(
            sample_times=(0.0, 5.0, 20.0),
            extracellular=(0.0, 700.0, 1600.0),
            internalized=(0.0, 100.0, 800.0),
        )
        summary = compare_run_bundles_detailed(left, right)

        self.assertEqual(
            tuple(item.time_min for item in summary.left_series),
            (0.0, 10.0, 20.0),
        )
        self.assertEqual(
            tuple(item.time_min for item in summary.right_series),
            (0.0, 5.0, 20.0),
        )
        self.assertEqual(summary.endpoint.extracellular_delta, -200.0)
        self.assertEqual(summary.endpoint.internalized_delta, 200.0)

    def test_compatible_fields_subtract_right_minus_left_in_stored_order(self) -> None:
        count = bundle().result.grid.voxel_count
        left_values = tuple(float(index) for index in range(count))
        right_values = tuple(value + 2.0 for value in left_values)

        summary = compare_run_bundles_detailed(
            bundle(field_values=left_values),
            bundle(field_values=right_values),
        )

        self.assertTrue(summary.spatial.compatible)
        self.assertEqual(summary.spatial.values, (2.0,) * count)
        self.assertEqual(summary.spatial.minimum_difference, 2.0)
        self.assertEqual(summary.spatial.maximum_difference, 2.0)
        self.assertEqual(summary.spatial.mean_absolute_difference, 2.0)

    def test_incompatible_concentration_units_block_only_spatial_difference(self) -> None:
        left = bundle()
        right = bundle(concentration_unit="other/micron^3")
        summary = compare_run_bundles_detailed(left, right)

        self.assertFalse(summary.spatial.compatible)
        self.assertIn("concentration unit", summary.spatial.reason)
        self.assertEqual(summary.spatial.values, ())
        self.assertEqual(summary.endpoint.extracellular_delta, 0.0)

    def test_incompatible_grid_blocks_spatial_difference(self) -> None:
        summary = compare_run_bundles_detailed(
            bundle(grid_spacing=10.0),
            bundle(grid_spacing=5.0),
        )
        self.assertFalse(summary.spatial.compatible)
        self.assertIn("grid", summary.spatial.reason)

    def test_incompatible_quantity_units_still_fail_comparison(self) -> None:
        with self.assertRaisesRegex(ValueError, "incompatible"):
            compare_run_bundles_detailed(
                bundle(quantity_unit="particle_equivalent"),
                bundle(quantity_unit="other_quantity"),
            )


if __name__ == "__main__":
    unittest.main()
