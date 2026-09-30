import math
import unittest

from vesiclescope.scenarios import recipient_count_sweep_experiment


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


if __name__ == "__main__":
    unittest.main()
