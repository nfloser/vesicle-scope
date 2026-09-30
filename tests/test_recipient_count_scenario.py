import math
import unittest

from vesiclescope.domain import CircularUptakeSink
from vesiclescope.scenarios import (
    FINITE_RECIPIENT_RING_POSITIONS,
    RECIPIENT_RING_POSITIONS,
    finite_recipient_count_sweep_experiment,
    recipient_count_sweep_experiment,
)


class RecipientCountScenarioTests(unittest.TestCase):
    def test_supports_only_reviewed_recipient_counts(self) -> None:
        for count in (2, 4, 8):
            self.assertEqual(
                len(recipient_count_sweep_experiment(count).uptake_sinks),
                count,
            )

        for invalid in (0, 1, 3, 16):
            with self.subTest(recipient_count=invalid):
                with self.assertRaises(ValueError):
                    recipient_count_sweep_experiment(invalid)

    def test_non_count_inputs_are_identical_across_sweep(self) -> None:
        scenarios = tuple(
            recipient_count_sweep_experiment(count)
            for count in (2, 4, 8)
        )
        reference = scenarios[0]

        for scenario in scenarios[1:]:
            self.assertEqual(scenario.domain, reference.domain)
            self.assertEqual(scenario.duration_min, reference.duration_min)
            self.assertEqual(scenario.sample_every_min, reference.sample_every_min)
            self.assertEqual(scenario.boundary, reference.boundary)
            self.assertEqual(scenario.diffusion, reference.diffusion)
            self.assertEqual(scenario.decay, reference.decay)
            self.assertEqual(
                scenario.initial_concentration,
                reference.initial_concentration,
            )
            self.assertEqual(scenario.release_sources, reference.release_sources)

        for scenario in scenarios:
            self.assertTrue(
                all(
                    sink.effective_volume_micron3 == 1000.0
                    and sink.uptake_rate.value == 0.5
                    for sink in scenario.uptake_sinks
                )
            )

    def test_all_recipients_are_exactly_50_micron_from_donor(self) -> None:
        for count in (2, 4, 8):
            scenario = recipient_count_sweep_experiment(count)
            donor = scenario.release_sources[0]

            for sink in scenario.uptake_sinks:
                self.assertTrue(
                    math.isclose(
                        math.hypot(
                            sink.x_micron - donor.x_micron,
                            sink.y_micron - donor.y_micron,
                        ),
                        50.0,
                        rel_tol=0.0,
                        abs_tol=1e-12,
                    )
                )

    def test_historical_point_geometry_remains_unchanged(self) -> None:
        self.assertEqual(
            RECIPIENT_RING_POSITIONS,
            (
                (65.0, 75.0),
                (145.0, 135.0),
                (65.0, 135.0),
                (145.0, 75.0),
                (75.0, 65.0),
                (135.0, 145.0),
                (75.0, 145.0),
                (135.0, 65.0),
            ),
        )

    def test_finite_ring_is_nested_grid_reproducible_and_non_overlapping(self) -> None:
        self.assertEqual(len(FINITE_RECIPIENT_RING_POSITIONS), 8)
        donor = (105.0, 105.0)

        for x_micron, y_micron in FINITE_RECIPIENT_RING_POSITIONS:
            self.assertEqual(x_micron % 5.0, 0.0)
            self.assertEqual(y_micron % 5.0, 0.0)
            self.assertTrue(
                math.isclose(
                    math.hypot(
                        x_micron - donor[0],
                        y_micron - donor[1],
                    ),
                    50.0,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            )

        for index, left in enumerate(FINITE_RECIPIENT_RING_POSITIONS):
            for right in FINITE_RECIPIENT_RING_POSITIONS[index + 1 :]:
                self.assertGreaterEqual(
                    math.hypot(
                        left[0] - right[0],
                        left[1] - right[1],
                    ),
                    30.0,
                )

    def test_finite_sweep_preserves_controlled_geometry_and_inputs(self) -> None:
        for count in (2, 4, 8):
            scenario = finite_recipient_count_sweep_experiment(count)
            donor = scenario.release_sources[0]
            self.assertEqual(
                scenario.experiment_id,
                f"synthetic.finite-recipient-count.{count}",
            )
            self.assertEqual(len(scenario.uptake_sinks), count)
            for sink in scenario.uptake_sinks:
                self.assertIsInstance(sink, CircularUptakeSink)
                self.assertEqual(sink.footprint_radius_micron, 15.0)
                self.assertEqual(sink.effective_volume_micron3, 1000.0)
                self.assertEqual(sink.uptake_rate.value, 0.5)
                self.assertTrue(
                    math.isclose(
                        math.hypot(
                            sink.x_micron - donor.x_micron,
                            sink.y_micron - donor.y_micron,
                        ),
                        50.0,
                        rel_tol=0.0,
                        abs_tol=1e-12,
                    )
                )

    def test_finite_sweep_supports_only_reviewed_counts(self) -> None:
        for invalid in (0, 1, 3, 16):
            with self.subTest(recipient_count=invalid):
                with self.assertRaises(ValueError):
                    finite_recipient_count_sweep_experiment(invalid)


if __name__ == "__main__":
    unittest.main()
