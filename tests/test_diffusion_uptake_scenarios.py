import unittest

from vesiclescope.domain import (
    CircularReleaseSource,
    CircularUptakeSink,
    EvidenceCategory,
)
from vesiclescope.scenarios import (
    DIFFUSION_FACTORS,
    UPTAKE_FACTORS,
    diffusion_uptake_factor_conditions,
)


class DiffusionUptakeScenarioTests(unittest.TestCase):
    def test_builds_exactly_nine_conditions_in_stable_matrix_order(self) -> None:
        conditions = diffusion_uptake_factor_conditions()

        self.assertEqual(len(conditions), 9)
        self.assertEqual(
            tuple(
                (condition.diffusion_factor, condition.uptake_factor)
                for condition in conditions
            ),
            tuple(
                (diffusion, uptake)
                for uptake in UPTAKE_FACTORS
                for diffusion in DIFFUSION_FACTORS
            ),
        )
        self.assertEqual(
            len({condition.experiment.experiment_id for condition in conditions}),
            9,
        )

    def test_each_condition_uses_one_finite_donor_and_eight_fixed_recipients(self) -> None:
        conditions = diffusion_uptake_factor_conditions()
        reference = conditions[0].experiment
        reference_recipient_geometry = tuple(
            (
                sink.identifier,
                sink.x_micron,
                sink.y_micron,
                sink.footprint_radius_micron,
                sink.effective_volume_micron3,
            )
            for sink in reference.uptake_sinks
        )

        for condition in conditions:
            with self.subTest(
                diffusion=condition.diffusion_factor,
                uptake=condition.uptake_factor,
            ):
                experiment = condition.experiment
                self.assertEqual(len(experiment.release_sources), 1)
                donor = experiment.release_sources[0]
                self.assertIsInstance(donor, CircularReleaseSource)
                self.assertEqual((donor.x_micron, donor.y_micron), (105.0, 105.0))
                self.assertEqual(donor.footprint_radius_micron, 15.0)
                self.assertEqual(donor.release_rate.value, 120.0)

                self.assertEqual(len(experiment.uptake_sinks), 8)
                self.assertTrue(
                    all(
                        isinstance(sink, CircularUptakeSink)
                        for sink in experiment.uptake_sinks
                    )
                )
                self.assertEqual(
                    tuple(
                        (
                            sink.identifier,
                            sink.x_micron,
                            sink.y_micron,
                            sink.footprint_radius_micron,
                            sink.effective_volume_micron3,
                        )
                        for sink in experiment.uptake_sinks
                    ),
                    reference_recipient_geometry,
                )

    def test_only_diffusion_and_recipient_uptake_change_across_factor_conditions(self) -> None:
        conditions = diffusion_uptake_factor_conditions()

        for condition in conditions:
            experiment = condition.experiment
            self.assertEqual(
                experiment.diffusion.value,
                100.0 * condition.diffusion_factor,
            )
            self.assertTrue(
                all(
                    sink.uptake_rate.value == 0.5 * condition.uptake_factor
                    for sink in experiment.uptake_sinks
                )
            )
            self.assertEqual(experiment.decay.value, 0.0)
            self.assertEqual(experiment.initial_concentration.value, 0.0)
            self.assertEqual(experiment.duration_min, 20.0)
            self.assertEqual(experiment.sample_every_min, 5.0)
            self.assertEqual(
                experiment.release_sources[0].release_rate.value,
                120.0,
            )

            changed_parameters = (
                experiment.diffusion,
                *(sink.uptake_rate for sink in experiment.uptake_sinks),
            )
            self.assertTrue(
                all(
                    parameter.evidence is EvidenceCategory.SYNTHETIC_BENCHMARK
                    for parameter in changed_parameters
                )
            )
            self.assertTrue(
                all(
                    any(
                        "not a biological default" in limitation
                        for limitation in parameter.limitations
                    )
                    for parameter in changed_parameters
                )
            )


if __name__ == "__main__":
    unittest.main()
