from dataclasses import replace
import unittest

from vesiclescope.engines import (
    BioFVMEngineMetadata,
    BioFVMGrid2D,
    BioFVMRunResult,
    SpatialFieldSnapshot2D,
    TransportSample,
)
from vesiclescope.figures import prepare_donor_boundary_figure_data
from vesiclescope.scenarios import finite_donor_boundary_figure_experiment


def normalized_result(experiment) -> BioFVMRunResult:
    grid = BioFVMGrid2D(
        nx=12,
        ny=12,
        grid_spacing_micron=20.0,
        slice_thickness_micron=25.0,
    )
    values = tuple(
        0.001 + index / 100_000.0
        for index in range(grid.voxel_count)
    )
    voxel_volume = (
        grid.grid_spacing_micron
        * grid.grid_spacing_micron
        * grid.slice_thickness_micron
    )
    integrated = sum(values) * voxel_volume
    return BioFVMRunResult(
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
                time_min=experiment.duration_min,
                mean_concentration=sum(values) / len(values),
                min_concentration=min(values),
                max_concentration=max(values),
                integrated_field_quantity=integrated,
                internalized_field_quantity=0.0,
            ),
        ),
        field_snapshots=(
            SpatialFieldSnapshot2D(
                time_min=experiment.duration_min,
                values=values,
            ),
        ),
        recipient_uptake_series=(),
    )


class DonorBoundaryFigureDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.experiment = finite_donor_boundary_figure_experiment()
        self.result = normalized_result(self.experiment)

    def test_uses_one_normalized_field_for_spatial_and_binned_views(self) -> None:
        data = prepare_donor_boundary_figure_data(
            self.experiment,
            self.result,
            time_min=self.experiment.duration_min,
            max_distance_micron=80.0,
        )

        self.assertEqual(data.heatmap_time_min, self.experiment.duration_min)
        self.assertEqual(len(data.heatmap_rows), self.result.grid.ny)
        self.assertTrue(
            all(len(row) == self.result.grid.nx for row in data.heatmap_rows)
        )
        self.assertEqual(
            data.heatmap_rows[0],
            self.result.field_snapshots[0].values[: self.result.grid.nx],
        )
        self.assertEqual(data.donor_position_micron, (120.0, 120.0))
        self.assertEqual(data.donor_radius_micron, 15.0)
        self.assertEqual(data.max_distance_micron, 80.0)
        self.assertEqual(data.concentration_unit, "particle_equivalent/micron^3")
        self.assertEqual(data.quantity_unit, "particle_equivalent")

        self.assertEqual(data.five_micron_bin_width, 5.0)
        self.assertEqual(data.ten_micron_bin_width, 10.0)
        self.assertEqual(len(data.five_micron_bin_centers), 16)
        self.assertEqual(len(data.ten_micron_bin_centers), 8)
        self.assertEqual(
            data.five_micron_bin_centers,
            tuple(2.5 + 5.0 * index for index in range(16)),
        )
        self.assertEqual(
            data.ten_micron_bin_centers,
            tuple(5.0 + 10.0 * index for index in range(8)),
        )
        self.assertEqual(len(data.five_micron_mean_concentrations), 16)
        self.assertEqual(len(data.ten_micron_mean_concentrations), 8)

    def test_ring_distances_are_physical_boundary_offsets_not_plotting_constants(self) -> None:
        data = prepare_donor_boundary_figure_data(
            self.experiment,
            self.result,
            time_min=self.experiment.duration_min,
            max_distance_micron=80.0,
        )

        self.assertEqual(data.ring_boundary_distances_micron, (20.0, 40.0, 60.0, 80.0))
        self.assertEqual(
            tuple(
                data.donor_radius_micron + distance
                for distance in data.ring_boundary_distances_micron
            ),
            (35.0, 55.0, 75.0, 95.0),
        )

    def test_rejects_result_identity_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            prepare_donor_boundary_figure_data(
                self.experiment,
                replace(self.result, experiment_id="different"),
                time_min=self.experiment.duration_min,
                max_distance_micron=80.0,
            )

    def test_rejects_radial_extent_not_shared_by_five_and_ten_micron_bins(self) -> None:
        with self.assertRaises(ValueError):
            prepare_donor_boundary_figure_data(
                self.experiment,
                self.result,
                time_min=self.experiment.duration_min,
                max_distance_micron=77.0,
            )


if __name__ == "__main__":
    unittest.main()
