import math
import unittest
from pathlib import Path

from vesiclescope.domain import (
    BoundaryCondition,
    CircularReleaseSource,
    EvidenceCategory,
    PointReleaseSource,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines.biofvm import (
    BioFVMNumerics,
    build_command,
    discretize_release_sources,
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


def circular_source(
    *,
    identifier: str = "source.circular",
    x_micron: float = 100.0,
    y_micron: float = 50.0,
    radius_micron: float = 25.0,
    release_rate: float = 120.0,
) -> CircularReleaseSource:
    return CircularReleaseSource(
        identifier=identifier,
        x_micron=x_micron,
        y_micron=y_micron,
        footprint_radius_micron=radius_micron,
        release_rate=synthetic_parameter(
            f"{identifier}.release",
            release_rate,
            "particle_equivalent/min",
        ),
    )


def experiment(
    source: PointReleaseSource | CircularReleaseSource | None = None,
) -> TransportExperiment:
    return TransportExperiment(
        experiment_id="synthetic.circular-donor",
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
        release_sources=(source or circular_source(),),
    )


class CircularReleaseSourceDomainTests(unittest.TestCase):
    def test_requires_positive_finite_radius(self) -> None:
        for radius in (0.0, -1.0, math.nan, math.inf):
            with self.subTest(radius=radius):
                with self.assertRaises(ValueError):
                    circular_source(radius_micron=radius)

    def test_requires_full_footprint_inside_domain(self) -> None:
        for source in (
            circular_source(x_micron=20.0, radius_micron=25.0),
            circular_source(x_micron=180.0, radius_micron=25.0),
            circular_source(y_micron=20.0, radius_micron=25.0),
            circular_source(y_micron=80.0, radius_micron=25.0),
        ):
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    experiment(source)

    def test_point_release_source_remains_supported_unchanged(self) -> None:
        point = PointReleaseSource(
            identifier="source.point",
            x_micron=100.0,
            y_micron=50.0,
            release_rate=synthetic_parameter(
                "source.point.release",
                120.0,
                "particle_equivalent/min",
            ),
        )

        configured = experiment(point)

        self.assertIs(configured.release_sources[0], point)


class CircularReleaseDiscretizationTests(unittest.TestCase):
    def test_selects_voxel_centers_deterministically(self) -> None:
        sources = discretize_release_sources(
            experiment(),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
        )

        self.assertEqual(len(sources), 1)
        source = sources[0]
        self.assertEqual(source.identifier, "source.circular")
        self.assertEqual(source.geometry_kind, "circle")
        self.assertEqual(source.footprint_radius_micron, 25.0)
        self.assertEqual(
            tuple((component.x_micron, component.y_micron) for component in source.components),
            (
                (90.0, 30.0),
                (110.0, 30.0),
                (90.0, 50.0),
                (110.0, 50.0),
                (90.0, 70.0),
                (110.0, 70.0),
            ),
        )

    def test_preserves_aggregate_release_rate_across_grid_refinement(self) -> None:
        configured_rate = experiment().release_sources[0].release_rate.value
        counts = []

        for grid in (20.0, 10.0, 5.0):
            sources = discretize_release_sources(
                experiment(),
                BioFVMNumerics(grid_spacing_micron=grid, time_step_min=0.1),
            )
            components = sources[0].components
            counts.append(len(components))
            self.assertAlmostEqual(
                sum(component.release_rate_per_min for component in components),
                configured_rate,
                places=12,
            )

        self.assertLess(counts[0], counts[1])
        self.assertLess(counts[1], counts[2])

    def test_point_source_maps_to_one_component_with_full_rate(self) -> None:
        point = PointReleaseSource(
            identifier="source.point",
            x_micron=93.0,
            y_micron=47.0,
            release_rate=synthetic_parameter(
                "source.point.release",
                77.0,
                "particle_equivalent/min",
            ),
        )
        sources = discretize_release_sources(
            experiment(point),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
        )

        self.assertEqual(sources[0].geometry_kind, "point")
        self.assertEqual(len(sources[0].components), 1)
        self.assertEqual(sources[0].components[0].x_micron, 93.0)
        self.assertEqual(sources[0].components[0].y_micron, 47.0)
        self.assertEqual(sources[0].components[0].release_rate_per_min, 77.0)

    def test_too_small_circular_source_fails_if_no_voxel_center_is_covered(self) -> None:
        source = circular_source(radius_micron=1.0)

        with self.assertRaises(ValueError):
            discretize_release_sources(
                experiment(source),
                BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            )

    def test_command_preserves_scientific_geometry_and_component_rates(self) -> None:
        command = build_command(
            experiment(),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            Path("runner"),
        )

        self.assertEqual(command[command.index("--source-kind") + 1], "circle")
        self.assertEqual(command[command.index("--source-radius-micron") + 1], "25")
        self.assertEqual(command[command.index("--source-component-count") + 1], "6")
        self.assertEqual(
            command[command.index("--source-rate-particle-equivalent-per-min") + 1],
            "120",
        )
        component_rates = tuple(
            float(
                command[
                    command.index(
                        f"--source-component-{index}-rate-particle-equivalent-per-min"
                    )
                    + 1
                ]
            )
            for index in range(6)
        )
        self.assertAlmostEqual(sum(component_rates), 120.0, places=12)


if __name__ == "__main__":
    unittest.main()
