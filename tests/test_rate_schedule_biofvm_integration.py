import math
import os
import unittest
from dataclasses import replace
from pathlib import Path

from vesiclescope.engines.biofvm import BioFVMNumerics, run_transport

from test_rate_schedules import experiment, schedule


RUNNER = os.environ.get("VESICLESCOPE_BIOFVM_RUNNER")
NUMERICS = BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1)


@unittest.skipUnless(RUNNER, "native BioFVM runner is required")
class RateScheduleBioFVMTests(unittest.TestCase):
    def run_experiment(self, item):
        return run_transport(item, NUMERICS, Path(RUNNER))

    def test_release_schedule_conserves_released_mass(self) -> None:
        item = experiment(
            uptake_sinks=(),
            release_schedule=schedule((0, 10, 1.0), (10, 20, 3.0), (20, 30, 0.0)),
        )
        result = self.run_experiment(item)
        rate = item.release_sources[0].release_rate.value
        for sample in result.samples:
            expected = rate * item.release_schedule.integral(0.0, sample.time_min)
            self.assertTrue(
                math.isclose(sample.integrated_field_quantity, expected, rel_tol=1e-9, abs_tol=1e-6),
                (sample.time_min, sample.integrated_field_quantity, expected),
            )

    def test_unit_schedule_reproduces_constant_rates_exactly(self) -> None:
        base = experiment()
        unit = experiment(
            release_schedule=schedule((0, 30, 1.0)),
            uptake_schedule=schedule((0, 15, 1.0), (15, 30, 1.0)),
        )
        left = self.run_experiment(base)
        right = self.run_experiment(unit)
        self.assertEqual(left.samples, right.samples)
        self.assertEqual(left.field_snapshots, right.field_snapshots)

    def test_zero_uptake_segment_stops_internalization(self) -> None:
        item = experiment(uptake_schedule=schedule((0, 10, 0.0), (10, 30, 1.0)))
        result = self.run_experiment(item)
        by_time = {sample.time_min: sample for sample in result.samples}
        self.assertEqual(by_time[10.0].internalized_field_quantity, 0.0)
        self.assertGreater(by_time[20.0].internalized_field_quantity, 0.0)
        for sample in result.samples:
            released = 60.0 * sample.time_min
            total = sample.integrated_field_quantity + sample.internalized_field_quantity
            self.assertTrue(math.isclose(total, released, rel_tol=1e-9, abs_tol=1e-6))

    def test_doubled_uptake_matches_doubled_rate(self) -> None:
        doubled_schedule = experiment(uptake_schedule=schedule((0, 30, 2.0)))
        sink = experiment().uptake_sinks[0]
        doubled_rate = experiment(
            uptake_sinks=(
                replace(sink, uptake_rate=replace(sink.uptake_rate, value=1.0)),
            )
        )
        left = self.run_experiment(doubled_schedule)
        right = self.run_experiment(doubled_rate)
        for a, b in zip(left.samples, right.samples):
            self.assertAlmostEqual(a.internalized_field_quantity, b.internalized_field_quantity, places=9)


if __name__ == "__main__":
    unittest.main()
