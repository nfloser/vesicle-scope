from dataclasses import replace
import unittest

from vesiclescope.domain import EvidenceCategory
from vesiclescope.experiment_editing import derive_synthetic_experiment
from vesiclescope.scenarios import diffusion_uptake_factor_conditions


def baseline():
    return diffusion_uptake_factor_conditions()[4].experiment


def release_rates(experiment):
    return {
        source.identifier: source.release_rate.value
        for source in experiment.release_sources
    }


def uptake_rates(experiment):
    return {
        sink.identifier: sink.uptake_rate.value
        for sink in experiment.uptake_sinks
    }


class SyntheticExperimentEditingTests(unittest.TestCase):
    def test_derives_new_values_without_mutating_source(self) -> None:
        source = baseline()
        releases = release_rates(source)
        releases[source.release_sources[0].identifier] = 150.0
        uptakes = uptake_rates(source)
        for identifier in uptakes:
            uptakes[identifier] = 0.75

        derived = derive_synthetic_experiment(
            source,
            experiment_id="synthetic.user.variant",
            duration_min=30.0,
            sample_every_min=5.0,
            diffusion_value=125.0,
            decay_value=0.02,
            initial_concentration_value=0.0,
            release_rates=releases,
            uptake_rates=uptakes,
        )

        self.assertEqual(source.experiment_id, "synthetic.diffusion-uptake.d1.u1")
        self.assertEqual(source.diffusion.value, 100.0)
        self.assertEqual(source.release_sources[0].release_rate.value, 120.0)
        self.assertEqual(source.uptake_sinks[0].uptake_rate.value, 0.5)

        self.assertEqual(derived.experiment_id, "synthetic.user.variant")
        self.assertEqual(derived.duration_min, 30.0)
        self.assertEqual(derived.diffusion.value, 125.0)
        self.assertEqual(derived.diffusion.unit, source.diffusion.unit)
        self.assertIs(
            derived.diffusion.evidence,
            EvidenceCategory.SYNTHETIC_BENCHMARK,
        )
        self.assertEqual(derived.release_sources[0].release_rate.value, 150.0)
        self.assertTrue(
            all(sink.uptake_rate.value == 0.75 for sink in derived.uptake_sinks)
        )
        self.assertEqual(derived.domain, source.domain)
        self.assertEqual(
            tuple((sink.x_micron, sink.y_micron) for sink in derived.uptake_sinks),
            tuple((sink.x_micron, sink.y_micron) for sink in source.uptake_sinks),
        )

    def test_rejects_non_synthetic_source_experiment(self) -> None:
        source = baseline()
        assumed = replace(
            source,
            diffusion=replace(
                source.diffusion,
                evidence=EvidenceCategory.ASSUMED,
            ),
        )

        with self.assertRaisesRegex(ValueError, "synthetic_benchmark"):
            derive_synthetic_experiment(
                assumed,
                experiment_id="derived",
                duration_min=20.0,
                sample_every_min=5.0,
                diffusion_value=100.0,
                decay_value=0.0,
                initial_concentration_value=0.0,
                release_rates=release_rates(assumed),
                uptake_rates=uptake_rates(assumed),
            )

    def test_requires_exact_release_and_uptake_identifier_maps(self) -> None:
        source = baseline()
        with self.assertRaisesRegex(ValueError, "release_rates"):
            derive_synthetic_experiment(
                source,
                experiment_id="derived",
                duration_min=20.0,
                sample_every_min=5.0,
                diffusion_value=100.0,
                decay_value=0.0,
                initial_concentration_value=0.0,
                release_rates={"unknown": 1.0},
                uptake_rates=uptake_rates(source),
            )

        incomplete_uptake = uptake_rates(source)
        incomplete_uptake.pop(next(iter(incomplete_uptake)))
        with self.assertRaisesRegex(ValueError, "uptake_rates"):
            derive_synthetic_experiment(
                source,
                experiment_id="derived",
                duration_min=20.0,
                sample_every_min=5.0,
                diffusion_value=100.0,
                decay_value=0.0,
                initial_concentration_value=0.0,
                release_rates=release_rates(source),
                uptake_rates=incomplete_uptake,
            )

    def test_domain_validators_reject_invalid_edited_values(self) -> None:
        source = baseline()
        with self.assertRaisesRegex(ValueError, "diffusion"):
            derive_synthetic_experiment(
                source,
                experiment_id="derived",
                duration_min=20.0,
                sample_every_min=5.0,
                diffusion_value=-1.0,
                decay_value=0.0,
                initial_concentration_value=0.0,
                release_rates=release_rates(source),
                uptake_rates=uptake_rates(source),
            )

        with self.assertRaisesRegex(ValueError, "sample_every_min"):
            derive_synthetic_experiment(
                source,
                experiment_id="derived",
                duration_min=5.0,
                sample_every_min=10.0,
                diffusion_value=100.0,
                decay_value=0.0,
                initial_concentration_value=0.0,
                release_rates=release_rates(source),
                uptake_rates=uptake_rates(source),
            )


if __name__ == "__main__":
    unittest.main()
