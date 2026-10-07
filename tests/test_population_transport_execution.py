import unittest
from unittest.mock import patch

from vesiclescope.domain import (
    BiologicalExposure,
    BoundaryCondition,
    EVMarkerFeature,
    EVPhenotype,
    EvidenceCategory,
    ExposureTarget,
    MarkerState,
    PerturbationStudy,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines import (
    BioFVMEngineMetadata,
    BioFVMGrid2D,
    BioFVMNumerics,
    BioFVMRunResult,
    SpatialFieldSnapshot2D,
    TransportSample,
)
from vesiclescope.workflows.perturbation_transport import (
    PopulationTransportSpec,
    aggregate_population_fields,
    aggregate_population_samples,
    resolve_perturbation_transport,
    run_population_transport,
)


def parameter(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier,
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic population execution test.",),
    )


def population_experiment(identifier: str) -> TransportExperiment:
    return TransportExperiment(
        experiment_id=identifier,
        domain=RectangularDomain2D(
            width_micron=20.0,
            height_micron=20.0,
            slice_thickness_micron=10.0,
        ),
        duration_min=2.0,
        sample_every_min=2.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=parameter(f"{identifier}.diffusion", 10.0, "micron^2/min"),
        decay=parameter(f"{identifier}.decay", 0.0, "1/min"),
        initial_concentration=parameter(
            f"{identifier}.initial",
            0.0,
            "particle_equivalent/micron^3",
        ),
    )


def study() -> PerturbationStudy:
    phenotypes = tuple(
        EVPhenotype(
            identifier=identifier,
            name=identifier,
            markers=(
                EVMarkerFeature(
                    identifier=f"{identifier}.marker",
                    marker_name="synthetic marker",
                    state=MarkerState.UNRESOLVED,
                    evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
                    limitations=("Synthetic marker only.",),
                ),
            ),
        )
        for identifier in ("population-a", "population-b")
    )
    return PerturbationStudy(
        study_id="two-population-execution",
        exposures=(
            BiologicalExposure(
                identifier="stimulus",
                compound_name="synthetic stimulus",
                concentration=parameter("stimulus", 1.0, "a.u."),
                target=ExposureTarget.DONOR_CELL_POPULATION,
                start_min=0.0,
                end_min=2.0,
                evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
            ),
        ),
        phenotypes=phenotypes,
        effects=(),
    )


def result(experiment_id: str, final_values: tuple[float, ...]) -> BioFVMRunResult:
    grid = BioFVMGrid2D(
        nx=2,
        ny=2,
        grid_spacing_micron=10.0,
        slice_thickness_micron=10.0,
    )
    initial = (0.0, 0.0, 0.0, 0.0)
    voxel_volume = 1000.0
    final_integrated = sum(final_values) * voxel_volume
    return BioFVMRunResult(
        experiment_id=experiment_id,
        concentration_unit="particle_equivalent/micron^3",
        integrated_quantity_unit="particle_equivalent",
        internalized_quantity_unit="particle_equivalent",
        engine=BioFVMEngineMetadata(
            engine="BioFVM",
            physicell_release="1.14.2",
            physicell_commit="dbd3499250141b27600e91e501c54c46f68f2763",
            biofvm_version="1.1.7",
        ),
        grid=grid,
        samples=(
            TransportSample(
                time_min=0.0,
                mean_concentration=0.0,
                min_concentration=0.0,
                max_concentration=0.0,
                integrated_field_quantity=0.0,
                internalized_field_quantity=0.0,
            ),
            TransportSample(
                time_min=2.0,
                mean_concentration=sum(final_values) / len(final_values),
                min_concentration=min(final_values),
                max_concentration=max(final_values),
                integrated_field_quantity=final_integrated,
                internalized_field_quantity=0.0,
            ),
        ),
        field_snapshots=(
            SpatialFieldSnapshot2D(time_min=0.0, values=initial),
            SpatialFieldSnapshot2D(time_min=2.0, values=final_values),
        ),
        recipient_uptake_series=(),
    )


class PopulationTransportExecutionTests(unittest.TestCase):
    def resolved(self):
        return resolve_perturbation_transport(
            study(),
            (
                PopulationTransportSpec(
                    phenotype_id="population-a",
                    experiment=population_experiment("population-a.baseline"),
                ),
                PopulationTransportSpec(
                    phenotype_id="population-b",
                    experiment=population_experiment("population-b.baseline"),
                ),
            ),
        )

    @patch("vesiclescope.workflows.perturbation_transport.run_transport")
    def test_executes_each_population_independently_and_keeps_child_run_bundles(
        self,
        run_transport_mock,
    ) -> None:
        run_transport_mock.side_effect = (
            result("population-a.baseline", (1.0, 2.0, 3.0, 4.0)),
            result("population-b.baseline", (4.0, 3.0, 2.0, 1.0)),
        )

        run = run_population_transport(
            self.resolved(),
            BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
            "runner",
            "a" * 40,
        )

        self.assertEqual(run_transport_mock.call_count, 2)
        self.assertEqual(
            tuple(item.phenotype_id for item in run.populations),
            ("population-a", "population-b"),
        )
        self.assertEqual(
            run.populations[0].run_bundle.experiment.experiment_id,
            "population-a.baseline",
        )

    @patch("vesiclescope.workflows.perturbation_transport.run_transport")
    def test_aggregate_is_pointwise_sum_without_hiding_population_results(
        self,
        run_transport_mock,
    ) -> None:
        run_transport_mock.side_effect = (
            result("population-a.baseline", (1.0, 2.0, 3.0, 4.0)),
            result("population-b.baseline", (4.0, 3.0, 2.0, 1.0)),
        )
        run = run_population_transport(
            self.resolved(),
            BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
            "runner",
            "b" * 40,
        )

        fields = aggregate_population_fields(run)
        samples = aggregate_population_samples(run)

        self.assertEqual(fields[-1].values, (5.0, 5.0, 5.0, 5.0))
        self.assertEqual(samples[-1].mean_concentration, 5.0)
        self.assertEqual(samples[-1].min_concentration, 5.0)
        self.assertEqual(samples[-1].max_concentration, 5.0)
        self.assertEqual(samples[-1].integrated_field_quantity, 20000.0)
        self.assertEqual(samples[-1].internalized_field_quantity, 0.0)
        self.assertEqual(
            run.populations[0].run_bundle.result.field_snapshots[-1].values,
            (1.0, 2.0, 3.0, 4.0),
        )

    @patch("vesiclescope.workflows.perturbation_transport.run_transport")
    def test_rejects_population_results_that_cannot_be_composed(
        self,
        run_transport_mock,
    ) -> None:
        incompatible = result("population-b.baseline", (1.0, 1.0, 1.0, 1.0))
        incompatible = BioFVMRunResult(
            experiment_id=incompatible.experiment_id,
            concentration_unit="different/unit",
            integrated_quantity_unit=incompatible.integrated_quantity_unit,
            internalized_quantity_unit=incompatible.internalized_quantity_unit,
            engine=incompatible.engine,
            grid=incompatible.grid,
            samples=incompatible.samples,
            field_snapshots=incompatible.field_snapshots,
            recipient_uptake_series=incompatible.recipient_uptake_series,
        )
        run_transport_mock.side_effect = (
            result("population-a.baseline", (1.0, 1.0, 1.0, 1.0)),
            incompatible,
        )

        with self.assertRaisesRegex(ValueError, "concentration unit"):
            run_population_transport(
                self.resolved(),
                BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
                "runner",
                "c" * 40,
            )


if __name__ == "__main__":
    unittest.main()
