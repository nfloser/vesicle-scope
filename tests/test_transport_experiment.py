import math
import unittest
from dataclasses import FrozenInstanceError

from vesiclescope.domain import EvidenceCategory, ScientificParameter
from vesiclescope.domain.transport import (
    BoundaryCondition,
    PointReleaseSource,
    PointUptakeSink,
    RectangularDomain2D,
    TransportExperiment,
)
from vesiclescope.validation.analytical import first_order_decay


def synthetic_parameter(
    identifier: str,
    value: float,
    unit: str,
) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic verification input; not a biological default.",),
    )


class RectangularDomain2DTests(unittest.TestCase):
    def test_requires_positive_finite_dimensions(self) -> None:
        for width, height, thickness in (
            (0.0, 100.0, 20.0),
            (-1.0, 100.0, 20.0),
            (100.0, 0.0, 20.0),
            (100.0, -1.0, 20.0),
            (math.inf, 100.0, 20.0),
            (100.0, math.nan, 20.0),
            (100.0, 100.0, 0.0),
            (100.0, 100.0, -1.0),
            (100.0, 100.0, math.inf),
            (100.0, 100.0, math.nan),
        ):
            with self.subTest(width=width, height=height, thickness=thickness):
                with self.assertRaises(ValueError):
                    RectangularDomain2D(
                        width_micron=width,
                        height_micron=height,
                        slice_thickness_micron=thickness,
                    )


class TransportExperimentTests(unittest.TestCase):
    def make_experiment(
        self,
        *,
        diffusion: ScientificParameter | None = None,
        decay: ScientificParameter | None = None,
        duration_min: float = 60.0,
        sample_every_min: float = 5.0,
        release_sources: tuple[PointReleaseSource, ...] = (),
        uptake_sinks: tuple[PointUptakeSink, ...] = (),
    ) -> TransportExperiment:
        return TransportExperiment(
            experiment_id="synthetic.decay",
            domain=RectangularDomain2D(
                width_micron=200.0,
                height_micron=100.0,
                slice_thickness_micron=20.0,
            ),
            duration_min=duration_min,
            sample_every_min=sample_every_min,
            boundary=BoundaryCondition.NO_FLUX,
            diffusion=diffusion
            or synthetic_parameter("transport.diffusion", 10.0, "micron^2/min"),
            decay=decay or synthetic_parameter("transport.decay", 0.1, "1/min"),
            initial_concentration=synthetic_parameter(
                "initial.concentration",
                2.0,
                "particle_equivalent/micron^3",
            ),
            release_sources=release_sources,
            uptake_sinks=uptake_sinks,
        )

    def test_preserves_provenance_objects(self) -> None:
        diffusion = synthetic_parameter("transport.diffusion", 10.0, "micron^2/min")
        decay = synthetic_parameter("transport.decay", 0.1, "1/min")

        experiment = self.make_experiment(diffusion=diffusion, decay=decay)

        self.assertIs(experiment.diffusion, diffusion)
        self.assertIs(experiment.decay, decay)
        self.assertEqual(experiment.boundary, BoundaryCondition.NO_FLUX)

    def test_experiment_is_immutable(self) -> None:
        experiment = self.make_experiment()

        with self.assertRaises(FrozenInstanceError):
            experiment.duration_min = 120.0

    def test_requires_positive_finite_duration_and_sampling(self) -> None:
        for duration, sampling in (
            (0.0, 1.0),
            (-1.0, 1.0),
            (math.inf, 1.0),
            (60.0, 0.0),
            (60.0, -1.0),
            (60.0, math.nan),
            (5.0, 10.0),
        ):
            with self.subTest(duration=duration, sampling=sampling):
                with self.assertRaises(ValueError):
                    self.make_experiment(
                        duration_min=duration,
                        sample_every_min=sampling,
                    )

    def test_rejects_incompatible_transport_units(self) -> None:
        cases = (
            (
                synthetic_parameter("transport.diffusion", 10.0, "mm^2/min"),
                synthetic_parameter("transport.decay", 0.1, "1/min"),
            ),
            (
                synthetic_parameter("transport.diffusion", 10.0, "micron^2/min"),
                synthetic_parameter("transport.decay", 0.1, "1/sec"),
            ),
        )

        for diffusion, decay in cases:
            with self.subTest(diffusion=diffusion.unit, decay=decay.unit):
                with self.assertRaises(ValueError):
                    self.make_experiment(diffusion=diffusion, decay=decay)

    def test_rejects_negative_diffusion_and_decay(self) -> None:
        cases = (
            (
                synthetic_parameter("transport.diffusion", -1.0, "micron^2/min"),
                synthetic_parameter("transport.decay", 0.1, "1/min"),
            ),
            (
                synthetic_parameter("transport.diffusion", 10.0, "micron^2/min"),
                synthetic_parameter("transport.decay", -0.1, "1/min"),
            ),
        )

        for diffusion, decay in cases:
            with self.subTest(diffusion=diffusion.value, decay=decay.value):
                with self.assertRaises(ValueError):
                    self.make_experiment(diffusion=diffusion, decay=decay)

    def test_preserves_valid_localized_release_source(self) -> None:
        source = PointReleaseSource(
            identifier="source.center",
            x_micron=100.0,
            y_micron=50.0,
            release_rate=synthetic_parameter(
                "source.release",
                120.0,
                "particle_equivalent/min",
            ),
        )

        experiment = self.make_experiment(release_sources=(source,))

        self.assertEqual(experiment.release_sources, (source,))
        self.assertIs(experiment.release_sources[0], source)

    def test_rejects_invalid_localized_release_source_fields(self) -> None:
        valid_rate = synthetic_parameter(
            "source.release",
            120.0,
            "particle_equivalent/min",
        )

        for identifier, x, y in (
            ("   ", 100.0, 50.0),
            ("source", -1.0, 50.0),
            ("source", math.nan, 50.0),
            ("source", 100.0, -1.0),
            ("source", 100.0, math.inf),
        ):
            with self.subTest(identifier=identifier, x=x, y=y):
                with self.assertRaises(ValueError):
                    PointReleaseSource(
                        identifier=identifier,
                        x_micron=x,
                        y_micron=y,
                        release_rate=valid_rate,
                    )

        with self.assertRaises(ValueError):
            PointReleaseSource(
                identifier="source",
                x_micron=100.0,
                y_micron=50.0,
                release_rate=synthetic_parameter(
                    "source.release",
                    120.0,
                    "particle_equivalent/sec",
                ),
            )

        with self.assertRaises(ValueError):
            PointReleaseSource(
                identifier="source",
                x_micron=100.0,
                y_micron=50.0,
                release_rate=synthetic_parameter(
                    "source.release",
                    -1.0,
                    "particle_equivalent/min",
                ),
            )

    def test_rejects_sources_outside_domain_or_invalid_collection(self) -> None:
        outside = PointReleaseSource(
            identifier="outside",
            x_micron=200.0,
            y_micron=50.0,
            release_rate=synthetic_parameter(
                "source.release",
                1.0,
                "particle_equivalent/min",
            ),
        )

        with self.assertRaises(ValueError):
            self.make_experiment(release_sources=(outside,))

        valid = PointReleaseSource(
            identifier="center",
            x_micron=100.0,
            y_micron=50.0,
            release_rate=synthetic_parameter(
                "source.release",
                1.0,
                "particle_equivalent/min",
            ),
        )
        with self.assertRaises(TypeError):
            self.make_experiment(release_sources=[valid])  # type: ignore[arg-type]

    def test_preserves_valid_explicit_volume_uptake_sink(self) -> None:
        uptake_rate = synthetic_parameter(
            "sink.uptake",
            0.5,
            "1/min",
        )
        sink = PointUptakeSink(
            identifier="sink.center",
            x_micron=100.0,
            y_micron=50.0,
            effective_volume_micron3=1000.0,
            uptake_rate=uptake_rate,
        )

        experiment = self.make_experiment(uptake_sinks=(sink,))

        self.assertEqual(experiment.uptake_sinks, (sink,))
        self.assertIs(experiment.uptake_sinks[0], sink)
        self.assertIs(experiment.uptake_sinks[0].uptake_rate, uptake_rate)

    def test_rejects_invalid_uptake_sink_fields(self) -> None:
        valid_rate = synthetic_parameter("sink.uptake", 0.5, "1/min")

        for identifier, x, y, volume in (
            ("   ", 100.0, 50.0, 1000.0),
            ("sink", -1.0, 50.0, 1000.0),
            ("sink", math.nan, 50.0, 1000.0),
            ("sink", 100.0, -1.0, 1000.0),
            ("sink", 100.0, math.inf, 1000.0),
            ("sink", 100.0, 50.0, 0.0),
            ("sink", 100.0, 50.0, -1.0),
            ("sink", 100.0, 50.0, math.nan),
            ("sink", 100.0, 50.0, math.inf),
        ):
            with self.subTest(
                identifier=identifier,
                x=x,
                y=y,
                volume=volume,
            ):
                with self.assertRaises(ValueError):
                    PointUptakeSink(
                        identifier=identifier,
                        x_micron=x,
                        y_micron=y,
                        effective_volume_micron3=volume,
                        uptake_rate=valid_rate,
                    )

        with self.assertRaises(ValueError):
            PointUptakeSink(
                identifier="sink",
                x_micron=100.0,
                y_micron=50.0,
                effective_volume_micron3=1000.0,
                uptake_rate=synthetic_parameter(
                    "sink.uptake",
                    0.5,
                    "1/sec",
                ),
            )

        with self.assertRaises(ValueError):
            PointUptakeSink(
                identifier="sink",
                x_micron=100.0,
                y_micron=50.0,
                effective_volume_micron3=1000.0,
                uptake_rate=synthetic_parameter(
                    "sink.uptake",
                    -0.5,
                    "1/min",
                ),
            )

    def test_rejects_uptake_sinks_outside_domain_or_invalid_collection(self) -> None:
        outside = PointUptakeSink(
            identifier="outside",
            x_micron=200.0,
            y_micron=50.0,
            effective_volume_micron3=1000.0,
            uptake_rate=synthetic_parameter("sink.uptake", 0.5, "1/min"),
        )

        with self.assertRaises(ValueError):
            self.make_experiment(uptake_sinks=(outside,))

        valid = PointUptakeSink(
            identifier="center",
            x_micron=100.0,
            y_micron=50.0,
            effective_volume_micron3=1000.0,
            uptake_rate=synthetic_parameter("sink.uptake", 0.5, "1/min"),
        )
        with self.assertRaises(TypeError):
            self.make_experiment(uptake_sinks=[valid])  # type: ignore[arg-type]

    def test_zero_diffusion_and_decay_are_valid_limiting_cases(self) -> None:
        experiment = self.make_experiment(
            diffusion=synthetic_parameter("transport.diffusion", 0.0, "micron^2/min"),
            decay=synthetic_parameter("transport.decay", 0.0, "1/min"),
        )

        self.assertEqual(experiment.diffusion.value, 0.0)
        self.assertEqual(experiment.decay.value, 0.0)


class FirstOrderDecayTests(unittest.TestCase):
    def test_returns_initial_value_at_time_zero(self) -> None:
        self.assertEqual(first_order_decay(2.5, 0.3, 0.0), 2.5)

    def test_matches_closed_form_solution(self) -> None:
        result = first_order_decay(initial_value=2.0, rate_per_min=0.1, time_min=10.0)

        self.assertAlmostEqual(result, 2.0 * math.exp(-1.0), places=12)

    def test_zero_decay_preserves_initial_value(self) -> None:
        self.assertEqual(first_order_decay(2.5, 0.0, 60.0), 2.5)

    def test_rejects_negative_or_non_finite_inputs(self) -> None:
        invalid_calls = (
            (-1.0, 0.1, 1.0),
            (1.0, -0.1, 1.0),
            (1.0, 0.1, -1.0),
            (math.nan, 0.1, 1.0),
            (1.0, math.inf, 1.0),
            (1.0, 0.1, math.nan),
        )

        for initial, rate, time in invalid_calls:
            with self.subTest(initial=initial, rate=rate, time=time):
                with self.assertRaises(ValueError):
                    first_order_decay(initial, rate, time)


if __name__ == "__main__":
    unittest.main()
