import json
import unittest

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
from vesiclescope.population_run_bundles import (
    deserialize_population_run_bundle,
    serialize_population_run_bundle,
)
from vesiclescope.run_bundles import SimulationRunBundle
from vesiclescope.workflows.perturbation_transport import (
    PopulationRunRecord,
    PopulationTransportRun,
)


def p(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier,
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic persistence test.",),
    )


def experiment(identifier: str) -> TransportExperiment:
    return TransportExperiment(
        experiment_id=identifier,
        domain=RectangularDomain2D(20.0, 20.0, 10.0),
        duration_min=1.0,
        sample_every_min=1.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=p(f"{identifier}.diffusion", 10.0, "micron^2/min"),
        decay=p(f"{identifier}.decay", 0.0, "1/min"),
        initial_concentration=p(
            f"{identifier}.initial",
            1.0,
            "particle_equivalent/micron^3",
        ),
    )


def result(identifier: str, value: float) -> BioFVMRunResult:
    grid = BioFVMGrid2D(2, 2, 10.0, 10.0)
    field = (value, value, value, value)
    integrated = sum(field) * 1000.0
    samples = tuple(
        TransportSample(
            time_min=time,
            mean_concentration=value,
            min_concentration=value,
            max_concentration=value,
            integrated_field_quantity=integrated,
            internalized_field_quantity=0.0,
        )
        for time in (0.0, 1.0)
    )
    fields = tuple(
        SpatialFieldSnapshot2D(time_min=time, values=field)
        for time in (0.0, 1.0)
    )
    return BioFVMRunResult(
        experiment_id=identifier,
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
        samples=samples,
        field_snapshots=fields,
        recipient_uptake_series=(),
    )


def perturbation_study() -> PerturbationStudy:
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
                    limitations=("Synthetic marker.",),
                ),
            ),
        )
        for identifier in ("population-a", "population-b")
    )
    return PerturbationStudy(
        study_id="persistence-study",
        exposures=(
            BiologicalExposure(
                identifier="stimulus",
                compound_name="synthetic stimulus",
                concentration=p("stimulus", 1.0, "a.u."),
                target=ExposureTarget.DONOR_CELL_POPULATION,
                start_min=0.0,
                end_min=1.0,
                evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
            ),
        ),
        phenotypes=phenotypes,
        effects=(),
    )


def population_run() -> PopulationTransportRun:
    records = []
    for index, phenotype_id in enumerate(("population-a", "population-b"), start=1):
        exp = experiment(f"{phenotype_id}.baseline")
        records.append(
            PopulationRunRecord(
                phenotype_id=phenotype_id,
                baseline_experiment=exp,
                effects=(),
                run_bundle=SimulationRunBundle(
                    vesiclescope_revision="d" * 40,
                    experiment=exp,
                    numerics=BioFVMNumerics(10.0, 0.1),
                    result=result(exp.experiment_id, float(index)),
                ),
            )
        )
    return PopulationTransportRun(
        study=perturbation_study(),
        populations=tuple(records),
        unexecuted_effects=(),
    )


class PopulationRunBundleTests(unittest.TestCase):
    def test_round_trip_is_deterministic_and_preserves_each_population(self) -> None:
        run = population_run()

        first = serialize_population_run_bundle(run)
        second = serialize_population_run_bundle(run)
        restored = deserialize_population_run_bundle(first)

        self.assertEqual(first, second)
        self.assertEqual(restored, run)
        self.assertEqual(
            tuple(item.phenotype_id for item in restored.populations),
            ("population-a", "population-b"),
        )
        self.assertEqual(
            restored.populations[1].run_bundle.result.field_snapshots[-1].values,
            (2.0, 2.0, 2.0, 2.0),
        )

    def test_integrity_digest_rejects_tampering(self) -> None:
        document = json.loads(serialize_population_run_bundle(population_run()))
        document["payload"]["populations"][0]["phenotype_id"] = "tampered"

        with self.assertRaisesRegex(ValueError, "digest"):
            deserialize_population_run_bundle(json.dumps(document))


if __name__ == "__main__":
    unittest.main()
