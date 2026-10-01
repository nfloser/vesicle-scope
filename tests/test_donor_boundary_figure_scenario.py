import unittest

from vesiclescope.domain import CircularReleaseSource, EvidenceCategory
from vesiclescope.scenarios import finite_donor_boundary_figure_experiment


class FiniteDonorBoundaryFigureScenarioTests(unittest.TestCase):
    def test_scenario_is_finite_source_only_and_explicitly_synthetic(self) -> None:
        experiment = finite_donor_boundary_figure_experiment()

        self.assertEqual(experiment.experiment_id, "synthetic.finite-donor-boundary.figure")
        self.assertEqual(experiment.domain.width_micron, 240.0)
        self.assertEqual(experiment.domain.height_micron, 240.0)
        self.assertEqual(experiment.domain.slice_thickness_micron, 25.0)
        self.assertEqual(experiment.duration_min, 20.0)
        self.assertEqual(experiment.sample_every_min, 5.0)
        self.assertEqual(experiment.decay.value, 0.0)
        self.assertEqual(experiment.uptake_sinks, ())
        self.assertEqual(len(experiment.release_sources), 1)

        donor = experiment.release_sources[0]
        self.assertIsInstance(donor, CircularReleaseSource)
        self.assertEqual((donor.x_micron, donor.y_micron), (120.0, 120.0))
        self.assertEqual(donor.footprint_radius_micron, 15.0)

        for parameter in (
            experiment.diffusion,
            experiment.decay,
            experiment.initial_concentration,
            donor.release_rate,
        ):
            self.assertEqual(parameter.evidence, EvidenceCategory.SYNTHETIC_BENCHMARK)
            self.assertTrue(
                any("not a biological default" in item for item in parameter.limitations)
            )


if __name__ == "__main__":
    unittest.main()
