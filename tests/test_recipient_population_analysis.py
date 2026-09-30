import math
import unittest

from vesiclescope.analysis import (
    analyze_recipient_population,
    bin_recipient_uptake_by_distance,
)
from vesiclescope.domain import (
    BoundaryCondition,
    EvidenceCategory,
    PointReleaseSource,
    PointUptakeSink,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines import (
    BioFVMEngineMetadata,
    BioFVMGrid2D,
    BioFVMRunResult,
    RecipientUptakeSample,
    RecipientUptakeSeries,
    SpatialFieldSnapshot2D,
    TransportSample,
)


def parameter(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier,
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic analysis fixture.",),
    )


def sink(identifier: str, x_micron: float) -> PointUptakeSink:
    return PointUptakeSink(
        identifier=identifier,
        x_micron=x_micron,
        y_micron=50.0,
        effective_volume_micron3=1000.0,
        uptake_rate=parameter(f"{identifier}.uptake", 0.5, "1/min"),
    )


def experiment() -> TransportExperiment:
    return TransportExperiment(
        experiment_id="analysis.population",
        domain=RectangularDomain2D(
            width_micron=200.0,
            height_micron=100.0,
            slice_thickness_micron=25.0,
        ),
        duration_min=10.0,
        sample_every_min=10.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=parameter("transport.diffusion", 100.0, "micron^2/min"),
        decay=parameter("transport.decay", 0.0, "1/min"),
        initial_concentration=parameter(
            "initial.concentration",
            0.0,
            "particle_equivalent/micron^3",
        ),
        release_sources=(
            PointReleaseSource(
                identifier="source.center",
                x_micron=100.0,
                y_micron=50.0,
                release_rate=parameter(
                    "source.release",
                    120.0,
                    "particle_equivalent/min",
                ),
            ),
        ),
        uptake_sinks=(
            sink("sink.left", 70.0),
            sink("sink.right", 130.0),
        ),
    )


def result(
    *,
    identifiers: tuple[str, str] = ("sink.left", "sink.right"),
) -> BioFVMRunResult:
    series = (
        RecipientUptakeSeries(
            identifier=identifiers[0],
            x_micron=70.0,
            y_micron=50.0,
            effective_volume_micron3=1000.0,
            uptake_rate_per_min=0.5,
            samples=(
                RecipientUptakeSample(0.0, 0.0),
                RecipientUptakeSample(10.0, 25.0),
            ),
        ),
        RecipientUptakeSeries(
            identifier=identifiers[1],
            x_micron=130.0,
            y_micron=50.0,
            effective_volume_micron3=1000.0,
            uptake_rate_per_min=0.5,
            samples=(
                RecipientUptakeSample(0.0, 0.0),
                RecipientUptakeSample(10.0, 35.0),
            ),
        ),
    )
    samples = (
        TransportSample(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        TransportSample(10.0, 0.00228, 0.0, 0.01, 1140.0, 60.0),
    )
    fields = (
        SpatialFieldSnapshot2D(0.0, tuple(0.0 for _ in range(50))),
        SpatialFieldSnapshot2D(10.0, tuple(0.00228 for _ in range(50))),
    )
    return BioFVMRunResult(
        experiment_id="analysis.population",
        concentration_unit="particle_equivalent/micron^3",
        integrated_quantity_unit="particle_equivalent",
        internalized_quantity_unit="particle_equivalent",
        engine=BioFVMEngineMetadata(
            engine="BioFVM",
            physicell_release="1.14.2",
            physicell_commit="dbd3499250141b27600e91e501c54c46f68f2763",
            biofvm_version="1.1.7",
        ),
        grid=BioFVMGrid2D(
            nx=10,
            ny=5,
            grid_spacing_micron=20.0,
            slice_thickness_micron=25.0,
        ),
        samples=samples,
        field_snapshots=fields,
        recipient_uptake_series=series,
    )


class RecipientPopulationAnalysisTests(unittest.TestCase):
    def test_reports_planar_density_distance_and_uptake(self) -> None:
        summary = analyze_recipient_population(
            experiment(),
            result(),
            time_min=10.0,
        )

        self.assertEqual(summary.recipient_count, 2)
        self.assertEqual(summary.planar_density_unit, "recipient/mm^2")
        self.assertAlmostEqual(summary.planar_density, 100.0)
        self.assertEqual(summary.quantity_unit, "particle_equivalent")
        self.assertAlmostEqual(summary.total_internalized_quantity, 60.0)
        self.assertAlmostEqual(summary.mean_internalized_quantity, 30.0)
        self.assertEqual(
            tuple(observation.identifier for observation in summary.recipients),
            ("sink.left", "sink.right"),
        )
        self.assertTrue(
            all(
                math.isclose(
                    observation.donor_distance_micron,
                    30.0,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
                for observation in summary.recipients
            )
        )

    def test_requires_result_recipient_identity_to_match_experiment(self) -> None:
        with self.assertRaises(ValueError):
            analyze_recipient_population(
                experiment(),
                result(identifiers=("sink.wrong", "sink.right")),
                time_min=10.0,
            )

    def test_requires_requested_sample_time(self) -> None:
        with self.assertRaises(ValueError):
            analyze_recipient_population(
                experiment(),
                result(),
                time_min=5.0,
            )

    def test_distance_bins_are_half_open_and_exhaustive(self) -> None:
        summary = analyze_recipient_population(
            experiment(),
            result(),
            time_min=10.0,
        )
        bins = bin_recipient_uptake_by_distance(
            summary.recipients,
            edges_micron=(0.0, 30.0, 40.0),
            quantity_unit=summary.quantity_unit,
        )

        self.assertEqual(len(bins), 2)
        self.assertEqual(bins[0].interval_semantics, "[lower, upper)")
        self.assertEqual(bins[0].recipient_count, 0)
        self.assertEqual(bins[1].recipient_count, 2)
        self.assertAlmostEqual(bins[1].total_internalized_quantity, 60.0)
        self.assertAlmostEqual(bins[1].mean_internalized_quantity, 30.0)

        with self.assertRaises(ValueError):
            bin_recipient_uptake_by_distance(
                summary.recipients,
                edges_micron=(0.0, 30.0),
                quantity_unit=summary.quantity_unit,
            )

    def test_requires_exactly_one_source_for_donor_distance(self) -> None:
        base = experiment()
        no_source = TransportExperiment(
            experiment_id=base.experiment_id,
            domain=base.domain,
            duration_min=base.duration_min,
            sample_every_min=base.sample_every_min,
            boundary=base.boundary,
            diffusion=base.diffusion,
            decay=base.decay,
            initial_concentration=base.initial_concentration,
            release_sources=(),
            uptake_sinks=base.uptake_sinks,
        )

        with self.assertRaises(ValueError):
            analyze_recipient_population(no_source, result(), time_min=10.0)


if __name__ == "__main__":
    unittest.main()
