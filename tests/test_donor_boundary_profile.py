import unittest

from vesiclescope.analysis import (
    analyze_donor_boundary_profile,
    distance_from_circular_donor_boundary,
    fixed_width_distance_edges,
)
from vesiclescope.domain import (
    BoundaryCondition,
    CircularReleaseSource,
    EvidenceCategory,
    PointReleaseSource,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines import (
    BioFVMGrid2D,
    BioFVMRunResult,
    SpatialFieldSnapshot2D,
    TransportSample,
    pinned_engine_metadata,
)


def synthetic_parameter(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic verification input; not a biological default.",),
    )


def circular_experiment(*, experiment_id: str = "synthetic.boundary-profile") -> TransportExperiment:
    return TransportExperiment(
        experiment_id=experiment_id,
        domain=RectangularDomain2D(
            width_micron=40.0,
            height_micron=40.0,
            slice_thickness_micron=2.0,
        ),
        duration_min=1.0,
        sample_every_min=1.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=synthetic_parameter("transport.diffusion", 0.0, "micron^2/min"),
        decay=synthetic_parameter("transport.decay", 0.0, "1/min"),
        initial_concentration=synthetic_parameter(
            "initial.concentration",
            0.0,
            "particle_equivalent/micron^3",
        ),
        release_sources=(
            CircularReleaseSource(
                identifier="source.circular",
                x_micron=20.0,
                y_micron=20.0,
                footprint_radius_micron=10.0,
                release_rate=synthetic_parameter(
                    "source.release",
                    0.0,
                    "particle_equivalent/min",
                ),
            ),
        ),
    )


def point_experiment() -> TransportExperiment:
    base = circular_experiment(experiment_id="synthetic.point-profile")
    return TransportExperiment(
        experiment_id=base.experiment_id,
        domain=base.domain,
        duration_min=base.duration_min,
        sample_every_min=base.sample_every_min,
        boundary=base.boundary,
        diffusion=base.diffusion,
        decay=base.decay,
        initial_concentration=base.initial_concentration,
        release_sources=(
            PointReleaseSource(
                identifier="source.point",
                x_micron=20.0,
                y_micron=20.0,
                release_rate=synthetic_parameter(
                    "source.release.point",
                    0.0,
                    "particle_equivalent/min",
                ),
            ),
        ),
    )


def result(
    *,
    experiment_id: str = "synthetic.boundary-profile",
    values: tuple[float, ...] = tuple(float(value) for value in range(1, 17)),
    nx: int = 4,
    ny: int = 4,
) -> BioFVMRunResult:
    voxel_volume = 10.0 * 10.0 * 2.0
    total = sum(values) * voxel_volume
    mean = sum(values) / len(values)
    return BioFVMRunResult(
        experiment_id=experiment_id,
        concentration_unit="particle_equivalent/micron^3",
        integrated_quantity_unit="particle_equivalent",
        internalized_quantity_unit="particle_equivalent",
        engine=pinned_engine_metadata(),
        grid=BioFVMGrid2D(
            nx=nx,
            ny=ny,
            grid_spacing_micron=10.0,
            slice_thickness_micron=2.0,
        ),
        samples=(
            TransportSample(
                time_min=1.0,
                mean_concentration=mean,
                min_concentration=min(values),
                max_concentration=max(values),
                integrated_field_quantity=total,
                internalized_field_quantity=0.0,
            ),
        ),
        field_snapshots=(
            SpatialFieldSnapshot2D(
                time_min=1.0,
                values=values,
            ),
        ),
        recipient_uptake_series=(),
    )


class DonorBoundaryGeometryTests(unittest.TestCase):
    def test_boundary_distance_is_signed_and_zero_at_declared_circle(self) -> None:
        source = circular_experiment().release_sources[0]
        self.assertEqual(
            distance_from_circular_donor_boundary(
                source,
                x_micron=30.0,
                y_micron=20.0,
            ),
            0.0,
        )
        self.assertLess(
            distance_from_circular_donor_boundary(
                source,
                x_micron=20.0,
                y_micron=20.0,
            ),
            0.0,
        )
        self.assertGreater(
            distance_from_circular_donor_boundary(
                source,
                x_micron=35.0,
                y_micron=20.0,
            ),
            0.0,
        )

    def test_fixed_width_edges_keep_five_and_ten_micron_definitions_distinct(self) -> None:
        self.assertEqual(
            fixed_width_distance_edges(
                max_distance_micron=20.0,
                bin_width_micron=5.0,
            ),
            (0.0, 5.0, 10.0, 15.0, 20.0),
        )
        self.assertEqual(
            fixed_width_distance_edges(
                max_distance_micron=20.0,
                bin_width_micron=10.0,
            ),
            (0.0, 10.0, 20.0),
        )


class DonorBoundaryProfileTests(unittest.TestCase):
    def test_excludes_donor_interior_and_preserves_x_fastest_grid_ordering(self) -> None:
        profile = analyze_donor_boundary_profile(
            circular_experiment(),
            result(),
            time_min=1.0,
            edges_micron=(0.0, 10.0, 20.0),
        )

        self.assertEqual(profile.excluded_donor_voxel_count, 4)
        self.assertEqual(profile.outside_extent_voxel_count, 0)
        self.assertEqual(tuple(item.voxel_count for item in profile.bins), (8, 4))

        # x-fastest/y-row values 1..16 place donor-interior values 6, 7, 10, 11.
        self.assertAlmostEqual(
            profile.excluded_donor_integrated_quantity,
            (6.0 + 7.0 + 10.0 + 11.0) * 200.0,
        )

    def test_bin_means_and_integrated_quantity_use_only_extracellular_voxels(self) -> None:
        profile = analyze_donor_boundary_profile(
            circular_experiment(),
            result(),
            time_min=1.0,
            edges_micron=(0.0, 10.0, 20.0),
        )

        near_values = (2.0, 3.0, 5.0, 8.0, 9.0, 12.0, 14.0, 15.0)
        far_values = (1.0, 4.0, 13.0, 16.0)

        self.assertAlmostEqual(
            profile.bins[0].mean_concentration,
            sum(near_values) / len(near_values),
        )
        self.assertAlmostEqual(
            profile.bins[0].integrated_field_quantity,
            sum(near_values) * 200.0,
        )
        self.assertAlmostEqual(
            profile.bins[1].mean_concentration,
            sum(far_values) / len(far_values),
        )
        self.assertAlmostEqual(
            profile.bins[1].integrated_field_quantity,
            sum(far_values) * 200.0,
        )

    def test_exhaustive_bins_preserve_total_analyzed_extracellular_quantity(self) -> None:
        run = result()
        profile = analyze_donor_boundary_profile(
            circular_experiment(),
            run,
            time_min=1.0,
            edges_micron=(0.0, 10.0, 20.0),
        )

        binned = sum(item.integrated_field_quantity for item in profile.bins)
        self.assertAlmostEqual(
            binned,
            profile.analyzed_extracellular_integrated_quantity,
        )
        self.assertAlmostEqual(
            binned + profile.excluded_donor_integrated_quantity,
            run.samples[0].integrated_field_quantity,
        )
        self.assertEqual(profile.concentration_unit, "particle_equivalent/micron^3")
        self.assertEqual(profile.quantity_unit, "particle_equivalent")

    def test_outside_extent_voxels_remain_explicitly_accounted_for(self) -> None:
        run = result()
        profile = analyze_donor_boundary_profile(
            circular_experiment(),
            run,
            time_min=1.0,
            edges_micron=(0.0, 10.0),
        )

        far_values = (1.0, 4.0, 13.0, 16.0)
        self.assertEqual(profile.outside_extent_voxel_count, 4)
        self.assertAlmostEqual(
            profile.outside_extent_integrated_quantity,
            sum(far_values) * 200.0,
        )
        self.assertAlmostEqual(
            profile.analyzed_extracellular_integrated_quantity
            + profile.excluded_donor_integrated_quantity
            + profile.outside_extent_integrated_quantity,
            run.samples[0].integrated_field_quantity,
        )

    def test_five_and_ten_micron_bins_produce_different_deterministic_groupings(self) -> None:
        five = analyze_donor_boundary_profile(
            circular_experiment(),
            result(),
            time_min=1.0,
            edges_micron=fixed_width_distance_edges(
                max_distance_micron=20.0,
                bin_width_micron=5.0,
            ),
        )
        ten = analyze_donor_boundary_profile(
            circular_experiment(),
            result(),
            time_min=1.0,
            edges_micron=fixed_width_distance_edges(
                max_distance_micron=20.0,
                bin_width_micron=10.0,
            ),
        )

        self.assertEqual(tuple(item.voxel_count for item in five.bins), (0, 8, 4, 0))
        self.assertEqual(tuple(item.voxel_count for item in ten.bins), (8, 4))

    def test_profile_rejects_point_donor(self) -> None:
        with self.assertRaises(ValueError):
            analyze_donor_boundary_profile(
                point_experiment(),
                result(experiment_id="synthetic.point-profile"),
                time_min=1.0,
                edges_micron=(0.0, 10.0, 20.0),
            )

    def test_profile_rejects_result_for_different_experiment(self) -> None:
        with self.assertRaises(ValueError):
            analyze_donor_boundary_profile(
                circular_experiment(),
                result(experiment_id="other"),
                time_min=1.0,
                edges_micron=(0.0, 10.0, 20.0),
            )

    def test_profile_rejects_field_length_that_does_not_match_grid(self) -> None:
        with self.assertRaises(ValueError):
            analyze_donor_boundary_profile(
                circular_experiment(),
                result(values=tuple(float(value) for value in range(1, 16))),
                time_min=1.0,
                edges_micron=(0.0, 10.0, 20.0),
            )

    def test_profile_rejects_grid_that_does_not_match_experiment_dimensions(self) -> None:
        with self.assertRaises(ValueError):
            analyze_donor_boundary_profile(
                circular_experiment(),
                result(nx=5, ny=4),
                time_min=1.0,
                edges_micron=(0.0, 10.0, 20.0),
            )


if __name__ == "__main__":
    unittest.main()
