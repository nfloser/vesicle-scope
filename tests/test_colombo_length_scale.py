import unittest

from vesiclescope.analysis import ReachGeometry
from vesiclescope.validation import (
    colombo_2025_landmarks,
    colombo_2025_length_scale_constraints,
    colombo_2025_tumour_distance_target,
)


class ColomboLengthScaleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.summary = colombo_2025_length_scale_constraints((5.0, 10.0, 20.0))

    def test_landmarks_come_from_recorded_target(self) -> None:
        recorded = colombo_2025_tumour_distance_target().fit_derived_retention_landmarks
        self.assertEqual(
            tuple((x.distance_micron, x.cumulative_fraction) for x in colombo_2025_landmarks()),
            tuple((x.distance_micron, x.cumulative_fraction) for x in recorded),
        )

    def test_planar_and_slab_geometries_are_reported(self) -> None:
        geometries = [item.geometry for item in self.summary.inferences]
        self.assertEqual(geometries[0], ReachGeometry.PLANAR_BOUNDARY)
        self.assertEqual(geometries.count(ReachGeometry.CIRCULAR_DONOR_2D_SLAB), 3)

    def test_length_scale_range(self) -> None:
        low, high = self.summary.length_scale_range_micron
        self.assertAlmostEqual(low, 16.8, delta=0.2)
        self.assertAlmostEqual(high, 24.7, delta=0.2)

    def test_every_inference_respects_published_tail_bound(self) -> None:
        for item in self.summary.inferences:
            self.assertTrue(item.tail_bound_satisfied)

    def test_slab_landmarks_are_less_mutually_consistent_than_planar(self) -> None:
        planar = self.summary.inferences[0].landmark_consistency_ratio
        for item in self.summary.inferences[1:]:
            self.assertGreater(item.landmark_consistency_ratio, planar)

    def test_free_diffusion_implies_minute_scale_loss(self) -> None:
        low, high = self.summary.loss_timescale_range_min(394.3)
        self.assertLess(high, 2.0)
        self.assertGreater(low, 0.5)

    def test_rejects_empty_radii(self) -> None:
        with self.assertRaises(ValueError):
            colombo_2025_length_scale_constraints(())


if __name__ == "__main__":
    unittest.main()
