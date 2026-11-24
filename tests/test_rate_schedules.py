import unittest

from vesiclescope.domain import (
    BoundaryCondition,
    CircularReleaseSource,
    CircularUptakeSink,
    EvidenceCategory,
    RateSchedule,
    RateScheduleSegment,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines.biofvm import BioFVMNumerics, build_command
from vesiclescope.experiment_files import (
    deserialize_experiment_document,
    serialize_experiment_document,
)
from vesiclescope.run_bundles import encode_experiment_payload


def parameter(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier,
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic verification input; not a biological default.",),
    )


def schedule(*segments: tuple[float, float, float]) -> RateSchedule:
    return RateSchedule(
        segments=tuple(RateScheduleSegment(a, b, m) for a, b, m in segments),
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        derivation="synthetic step schedule for verification",
    )


def experiment(**kwargs) -> TransportExperiment:
    values = dict(
        experiment_id="synthetic.schedule",
        domain=RectangularDomain2D(
            width_micron=200.0, height_micron=200.0, slice_thickness_micron=25.0
        ),
        duration_min=30.0,
        sample_every_min=10.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=parameter("transport.diffusion", 100.0, "micron^2/min"),
        decay=parameter("transport.decay", 0.0, "1/min"),
        initial_concentration=parameter(
            "initial.concentration", 0.0, "particle_equivalent/micron^3"
        ),
        release_sources=(
            CircularReleaseSource(
                identifier="source.donor",
                x_micron=100.0,
                y_micron=100.0,
                footprint_radius_micron=10.0,
                release_rate=parameter("source.release", 60.0, "particle_equivalent/min"),
            ),
        ),
        uptake_sinks=(
            CircularUptakeSink(
                identifier="sink.1",
                x_micron=150.0,
                y_micron=100.0,
                footprint_radius_micron=10.0,
                effective_volume_micron3=1000.0,
                uptake_rate=parameter("sink.1.uptake", 0.5, "1/min"),
            ),
        ),
    )
    values.update(kwargs)
    return TransportExperiment(**values)


class RateScheduleContractTests(unittest.TestCase):
    def test_integral_and_lookup(self) -> None:
        item = schedule((0, 10, 1.0), (10, 20, 3.0), (20, 30, 0.0))
        self.assertEqual(item.multiplier_at(15.0), 3.0)
        self.assertAlmostEqual(item.integral(0.0, 30.0), 40.0)
        self.assertAlmostEqual(item.integral(5.0, 15.0), 20.0)

    def test_segments_must_be_contiguous_and_start_at_zero(self) -> None:
        with self.assertRaises(ValueError):
            schedule((0, 10, 1.0), (12, 30, 1.0))
        with self.assertRaises(ValueError):
            schedule((5, 30, 1.0))
        with self.assertRaises(ValueError):
            RateScheduleSegment(0.0, 10.0, -1.0)

    def test_schedule_must_cover_duration(self) -> None:
        with self.assertRaises(ValueError):
            experiment(release_schedule=schedule((0, 20, 1.0)))

    def test_schedule_requires_targets(self) -> None:
        with self.assertRaises(ValueError):
            experiment(uptake_sinks=(), uptake_schedule=schedule((0, 30, 1.0)))


class RateScheduleSerializationTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        original = experiment(
            release_schedule=schedule((0, 10, 1.0), (10, 30, 2.5)),
            uptake_schedule=schedule((0, 30, 0.5)),
        )
        restored = deserialize_experiment_document(serialize_experiment_document(original))
        self.assertEqual(restored, original)

    def test_constant_rate_payload_has_no_schedule_keys(self) -> None:
        payload = encode_experiment_payload(experiment())
        self.assertNotIn("release_schedule", payload)
        self.assertNotIn("uptake_schedule", payload)
        self.assertEqual(
            deserialize_experiment_document(serialize_experiment_document(experiment())),
            experiment(),
        )


class RateScheduleCommandTests(unittest.TestCase):
    def test_command_carries_schedules(self) -> None:
        command = build_command(
            experiment(release_schedule=schedule((0, 10, 1.0), (10, 30, 2.5))),
            BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
            "runner",
        )
        text = " ".join(command)
        self.assertIn("--release-schedule-count 2", text)
        self.assertIn("--release-schedule-1-end-min 30", text)
        self.assertIn("--release-schedule-1-multiplier 2.5", text)
        self.assertNotIn("--uptake-schedule", text)

    def test_segment_boundaries_must_tile_time_step(self) -> None:
        with self.assertRaises(ValueError):
            build_command(
                experiment(release_schedule=schedule((0, 10.05, 1.0), (10.05, 30, 2.0))),
                BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
                "runner",
            )


if __name__ == "__main__":
    unittest.main()
