import os
import unittest
from pathlib import Path

from vesiclescope.engines.biofvm import BioFVMNumerics
from vesiclescope.scenarios.dose_response import (
    synthetic_dose_response_experiment,
    synthetic_dose_responses,
    synthetic_hormone_pulse,
)
from vesiclescope.workflows.dose_response import run_dose_response_comparison


RUNNER = os.environ.get("VESICLESCOPE_BIOFVM_RUNNER")


@unittest.skipUnless(RUNNER, "native BioFVM runner is required")
class DoseResponseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.comparison = run_dose_response_comparison(
            experiment=synthetic_dose_response_experiment(),
            exposure=synthetic_hormone_pulse(),
            responses=synthetic_dose_responses(),
            numerics=BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
            runner=Path(RUNNER),
            segment_min=5.0,
        )

    def test_no_change_before_exposure(self) -> None:
        for condition in self.comparison.conditions:
            for time_min, ratio in self.comparison.internalization_rate_ratio(condition):
                if time_min < 30.0:
                    self.assertEqual(ratio, 1.0)

    def test_variants_carry_only_their_own_schedule(self) -> None:
        release, uptake = self.comparison.conditions
        self.assertIsNotNone(release.experiment.release_schedule)
        self.assertIsNone(release.experiment.uptake_schedule)
        self.assertIsNotNone(uptake.experiment.uptake_schedule)
        self.assertIsNone(uptake.experiment.release_schedule)
        self.assertIsNone(self.comparison.baseline_experiment.release_schedule)

    def test_uptake_effect_is_immediate_while_release_effect_is_transport_delayed(self) -> None:
        release, uptake = self.comparison.conditions
        first_interval = lambda condition: next(  # noqa: E731
            ratio
            for time_min, ratio in self.comparison.internalization_rate_ratio(condition)
            if time_min > 30.0
        )
        self.assertGreater(abs(first_interval(uptake) - 1.0), abs(first_interval(release) - 1.0))

    def test_effects_have_expected_sign(self) -> None:
        release, uptake = self.comparison.conditions
        at = lambda condition, t: dict(  # noqa: E731
            self.comparison.internalization_rate_ratio(condition)
        )[t]
        self.assertGreater(at(release, 147.5), 1.3)
        self.assertLess(at(uptake, 147.5), 0.8)


if __name__ == "__main__":
    unittest.main()
