import math
import unittest
from pathlib import Path

from vesiclescope.domain import (
    BoundaryCondition,
    CircularUptakeSink,
    EvidenceCategory,
    PointReleaseSource,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines.biofvm import (
    BioFVMNumerics,
    build_command,
    discretize_uptake_sinks,
)


def synthetic_parameter(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic verification input; not a biological default.",),
    )


def circular_sink(
    *,
    identifier: str = "sink.circular",
    x_micron: float = 100.0,
    y_micron: float = 50.0,
    radius_micron: float = 25.0,
    effective_volume_micron3: float = 1200.0,
) -> CircularUptakeSink:
    return CircularUptakeSink(
        identifier=identifier,
        x_micron=x_micron,
        y_micron=y_micron,
        footprint_radius_micron=radius_micron,
        effective_volume_micron3=effective_volume_micron3,
        uptake_rate=synthetic_parameter(
            f"{identifier}.uptake",
            0.5,
            "1/min",
        ),
    )


def experiment(
    sink: CircularUptakeSink | None = None,
) -> TransportExperiment:
    return TransportExperiment(
        experiment_id="synthetic.circular-recipient",
        domain=RectangularDomain2D(
            width_micron=200.0,
            height_micron=100.0,
            slice_thickness_micron=25.0,
        ),
        duration_min=10.0,
        sample_every_min=2.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=synthetic_parameter(
            "transport.diffusion",
            100.0,
            "micron^2/min",
        ),
        decay=synthetic_parameter("transport.decay", 0.0, "1/min"),
        initial_concentration=synthetic_parameter(
            "initial.concentration",
            0.0,
            "particle_equivalent/micron^3",
        ),
        release_sources=(
            PointReleaseSource(
                identifier="source.donor",
                x_micron=40.0,
                y_micron=50.0,
                release_rate=synthetic_parameter(
                    "source.release",
                    120.0,
                    "particle_equivalent/min",
                ),
            ),
        ),
        uptake_sinks=(sink or circular_sink(),),
    )


class CircularUptakeSinkDomainTests(unittest.TestCase):
    def test_requires_positive_finite_radius(self) -> None:
        for radius in (0.0, -1.0, math.nan, math.inf):
            with self.subTest(radius=radius):
                with self.assertRaises(ValueError):
                    circular_sink(radius_micron=radius)

    def test_preserves_radius_and_effective_volume_as_independent_inputs(self) -> None:
        sink = circular_sink(
            radius_micron=20.0,
            effective_volume_micron3=1750.0,
        )

        self.assertEqual(sink.footprint_radius_micron, 20.0)
        self.assertEqual(sink.effective_volume_micron3, 1750.0)

    def test_requires_full_circular_footprint_inside_domain(self) -> None:
        for sink in (
            circular_sink(x_micron=20.0, radius_micron=25.0),
            circular_sink(x_micron=180.0, radius_micron=25.0),
            circular_sink(y_micron=20.0, radius_micron=25.0),
            circular_sink(y_micron=80.0, radius_micron=25.0),
        ):
            with self.subTest(sink=sink):
                with self.assertRaises(ValueError):
                    experiment(sink)


class CircularUptakeDiscretizationTests(unittest.TestCase):
    def test_selects_voxel_centers_deterministically(self) -> None:
        components = discretize_uptake_sinks(
            experiment(),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
        )

        self.assertEqual(len(components), 1)
        recipient = components[0]
        self.assertEqual(recipient.identifier, "sink.circular")
        self.assertEqual(recipient.geometry_kind, "circle")
        self.assertEqual(recipient.footprint_radius_micron, 25.0)
        self.assertEqual(
            tuple((component.x_micron, component.y_micron) for component in recipient.components),
            (
                (90.0, 30.0),
                (110.0, 30.0),
                (90.0, 50.0),
                (110.0, 50.0),
                (90.0, 70.0),
                (110.0, 70.0),
            ),
        )

    def test_preserves_total_effective_volume_across_grid_refinement(self) -> None:
        configured_volume = experiment().uptake_sinks[0].effective_volume_micron3
        counts = []

        for grid in (20.0, 10.0, 5.0):
            recipients = discretize_uptake_sinks(
                experiment(),
                BioFVMNumerics(grid_spacing_micron=grid, time_step_min=0.1),
            )
            components = recipients[0].components
            counts.append(len(components))
            self.assertAlmostEqual(
                sum(component.effective_volume_micron3 for component in components),
                configured_volume,
                places=12,
            )

        self.assertLess(counts[0], counts[1])
        self.assertLess(counts[1], counts[2])

    def test_command_keeps_one_recipient_identity_with_many_native_components(self) -> None:
        command = build_command(
            experiment(),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            Path("runner"),
        )

        self.assertEqual(command[command.index("--uptake-count") + 1], "1")
        self.assertEqual(command[command.index("--uptake-0-kind") + 1], "circle")
        self.assertEqual(
            command[command.index("--uptake-0-radius-micron") + 1],
            "25",
        )
        self.assertEqual(
            command[command.index("--uptake-0-component-count") + 1],
            "6",
        )

        component_volumes = tuple(
            float(command[command.index(f"--uptake-0-component-{index}-volume-micron3") + 1])
            for index in range(6)
        )
        self.assertAlmostEqual(sum(component_volumes), 1200.0, places=12)


if __name__ == "__main__":
    unittest.main()
