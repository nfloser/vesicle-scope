import math
import unittest

from vesiclescope.analysis.reach import (
    BOLTZMANN_J_PER_K,
    ReachGeometry,
    RetentionLandmark,
    TailBound,
    bessel_k0,
    bessel_k1,
    cumulative_signal_fraction,
    implied_loss_rate_per_min,
    infer_length_scale,
    perturbed_reach,
    steady_state_profile_shape,
    stokes_einstein_diffusion_micron2_per_min,
)


COLOMBO_LANDMARKS = (
    RetentionLandmark(distance_micron=17.0, cumulative_fraction=0.5),
    RetentionLandmark(distance_micron=40.0, cumulative_fraction=0.8),
)
COLOMBO_TAIL = TailBound(distance_micron=100.0, max_fraction_beyond=0.05)


class BesselFunctionTests(unittest.TestCase):
    # Reference values: Abramowitz & Stegun, Table 9.8 / standard tables.
    def test_reference_values(self) -> None:
        self.assertAlmostEqual(bessel_k0(0.1), 2.4270690247, places=9)
        self.assertAlmostEqual(bessel_k0(1.0), 0.4210244382, places=9)
        self.assertAlmostEqual(bessel_k1(0.1), 9.8538447809, places=8)
        self.assertAlmostEqual(bessel_k1(1.0), 0.6019072302, places=9)
        self.assertAlmostEqual(bessel_k0(5.0) / 3.6910983340e-3, 1.0, places=8)

    def test_rejects_non_positive_argument(self) -> None:
        with self.assertRaises(ValueError):
            bessel_k0(0.0)


class ProfileTests(unittest.TestCase):
    def test_profiles_equal_one_at_boundary_and_decay(self) -> None:
        for geometry, radius in (
            (ReachGeometry.PLANAR_BOUNDARY, None),
            (ReachGeometry.SPHERICAL_DONOR_EQUATORIAL_SECTION, 10.0),
            (ReachGeometry.CIRCULAR_DONOR_2D_SLAB, 10.0),
        ):
            shape = lambda d: steady_state_profile_shape(  # noqa: E731
                geometry,
                length_scale_micron=20.0,
                distance_micron=d,
                donor_radius_micron=radius,
            )
            self.assertAlmostEqual(shape(0.0), 1.0, places=12)
            self.assertGreater(shape(5.0), shape(10.0))

    def test_cumulative_fraction_is_monotone_and_bounded(self) -> None:
        for geometry in ReachGeometry:
            previous = 0.0
            for distance in (0.0, 5.0, 20.0, 80.0, 400.0):
                value = cumulative_signal_fraction(
                    geometry,
                    length_scale_micron=20.0,
                    distance_micron=distance,
                    donor_radius_micron=10.0,
                )
                self.assertGreaterEqual(value, previous)
                self.assertLessEqual(value, 1.0)
                previous = value
            self.assertAlmostEqual(previous, 1.0, places=6)

    def test_slab_cumulative_matches_numerical_integral(self) -> None:
        lam, radius, distance = 20.0, 10.0, 30.0
        steps = 4000
        upper = 40.0 * lam

        def integrate(limit: float) -> float:
            h = limit / steps
            return h * sum(
                (0.5 if i in (0, steps) else 1.0)
                * (radius + i * h)
                * bessel_k0((radius + i * h) / lam)
                for i in range(steps + 1)
            )

        expected = integrate(distance) / integrate(upper)
        actual = cumulative_signal_fraction(
            ReachGeometry.CIRCULAR_DONOR_2D_SLAB,
            length_scale_micron=lam,
            distance_micron=distance,
            donor_radius_micron=radius,
        )
        self.assertAlmostEqual(actual, expected, places=5)

    def test_slab_approaches_planar_for_large_donor(self) -> None:
        planar = cumulative_signal_fraction(
            ReachGeometry.PLANAR_BOUNDARY,
            length_scale_micron=20.0,
            distance_micron=20.0,
        )
        slab = cumulative_signal_fraction(
            ReachGeometry.CIRCULAR_DONOR_2D_SLAB,
            length_scale_micron=20.0,
            distance_micron=20.0,
            donor_radius_micron=1e5,
        )
        self.assertAlmostEqual(planar, slab, places=3)

    def test_radius_required_for_finite_donor_geometries(self) -> None:
        with self.assertRaises(ValueError):
            cumulative_signal_fraction(
                ReachGeometry.CIRCULAR_DONOR_2D_SLAB,
                length_scale_micron=20.0,
                distance_micron=10.0,
            )


class InferenceTests(unittest.TestCase):
    def test_planar_single_landmark_inversion_is_exact(self) -> None:
        inference = infer_length_scale(
            ReachGeometry.PLANAR_BOUNDARY,
            COLOMBO_LANDMARKS,
            tail_bound=COLOMBO_TAIL,
        )
        expected = (-17.0 / math.log(0.5), -40.0 / math.log(0.2))
        for actual, wanted in zip(inference.per_landmark_length_scale_micron, expected):
            self.assertAlmostEqual(actual, wanted, places=9)
        self.assertAlmostEqual(inference.least_squares_length_scale_micron, 24.69, places=1)
        self.assertLess(inference.landmark_consistency_ratio, 1.02)
        self.assertTrue(inference.tail_bound_satisfied)

    def test_round_trip_recovers_known_length_scale(self) -> None:
        for geometry in ReachGeometry:
            truth = 18.0
            landmarks = tuple(
                RetentionLandmark(
                    distance_micron=d,
                    cumulative_fraction=cumulative_signal_fraction(
                        geometry,
                        length_scale_micron=truth,
                        distance_micron=d,
                        donor_radius_micron=12.0,
                    ),
                )
                for d in (10.0, 30.0, 60.0)
            )
            inference = infer_length_scale(
                geometry,
                landmarks,
                donor_radius_micron=12.0,
            )
            self.assertAlmostEqual(
                inference.least_squares_length_scale_micron, truth, places=4
            )
            for value in inference.per_landmark_length_scale_micron:
                self.assertAlmostEqual(value, truth, places=4)

    def test_slab_geometry_needs_shorter_length_than_planar(self) -> None:
        planar = infer_length_scale(ReachGeometry.PLANAR_BOUNDARY, COLOMBO_LANDMARKS)
        slab = infer_length_scale(
            ReachGeometry.CIRCULAR_DONOR_2D_SLAB,
            COLOMBO_LANDMARKS,
            donor_radius_micron=10.0,
        )
        self.assertLess(
            slab.least_squares_length_scale_micron,
            planar.least_squares_length_scale_micron,
        )

    def test_landmark_validation(self) -> None:
        with self.assertRaises(ValueError):
            RetentionLandmark(distance_micron=10.0, cumulative_fraction=1.0)
        with self.assertRaises(ValueError):
            infer_length_scale(ReachGeometry.PLANAR_BOUNDARY, ())


class PhysicalMappingTests(unittest.TestCase):
    def test_stokes_einstein_matches_formula_and_units(self) -> None:
        value = stokes_einstein_diffusion_micron2_per_min(
            hydrodynamic_diameter_nm=100.0,
            temperature_kelvin=310.15,
            viscosity_pa_s=0.6913e-3,
        )
        expected_m2_s = BOLTZMANN_J_PER_K * 310.15 / (6 * math.pi * 0.6913e-3 * 50e-9)
        self.assertAlmostEqual(value, expected_m2_s * 1e12 * 60, places=9)
        self.assertAlmostEqual(value, 394.3, delta=0.5)

    def test_implied_loss_rate(self) -> None:
        self.assertAlmostEqual(
            implied_loss_rate_per_min(
                length_scale_micron=20.0,
                diffusion_micron2_per_min=100.0,
            ),
            0.25,
        )


class PerturbationTests(unittest.TestCase):
    def test_release_changes_reach_but_not_length_scale(self) -> None:
        result = perturbed_reach(
            length_scale_micron=25.0,
            boundary_to_threshold_ratio=10.0,
            release_fold=2.0,
            loss_fold=1.0,
            diffusion_fold=1.0,
        )
        self.assertEqual(result.length_scale_fold, 1.0)
        self.assertAlmostEqual(
            result.perturbed_threshold_reach_micron
            - result.baseline_threshold_reach_micron,
            25.0 * math.log(2.0),
        )

    def test_halved_loss_extends_length_by_sqrt_two(self) -> None:
        result = perturbed_reach(
            length_scale_micron=25.0,
            boundary_to_threshold_ratio=10.0,
            release_fold=1.0,
            loss_fold=0.5,
            diffusion_fold=1.0,
        )
        self.assertAlmostEqual(result.length_scale_fold, math.sqrt(2.0))
        expected = 25.0 * math.sqrt(2.0) * math.log(10.0 * math.sqrt(2.0))
        self.assertAlmostEqual(result.perturbed_threshold_reach_micron, expected)

    def test_reach_is_zero_below_threshold(self) -> None:
        result = perturbed_reach(
            length_scale_micron=25.0,
            boundary_to_threshold_ratio=2.0,
            release_fold=0.25,
            loss_fold=1.0,
            diffusion_fold=1.0,
        )
        self.assertEqual(result.perturbed_threshold_reach_micron, 0.0)


if __name__ == "__main__":
    unittest.main()
