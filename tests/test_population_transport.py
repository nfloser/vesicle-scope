import unittest
from pathlib import Path
from unittest.mock import patch

from vesiclescope.domain import (
    BoundaryCondition,
    CircularReleaseSource,
    EvidenceCategory,
    EvidenceSource,
    EVPopulationExperiment,
    EVPopulationTransport,
    ModelEffectMapping,
    ModelEffectTarget,
    EffectOperation,
    EffectDirection,
    EffectOutcome,
    PerturbationEffect,
    PerturbationStudy,
    BiologicalExposure,
    ExposureTarget,
    EVMarkerFeature,
    EVPhenotype,
    MarkerState,
    ParameterContext,
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
from vesiclescope.perturbation_execution import apply_model_effects
from vesiclescope.population_experiment_files import (
    deserialize_population_experiment_document,
    serialize_population_experiment_document,
)
from vesiclescope.population_run_bundles import (
    PopulationSimulationRunBundle,
    deserialize_population_run_bundle,
    serialize_population_run_bundle,
)
from vesiclescope.workflows.population_transport import (
    run_population_transport,
    sum_population_fields,
)


def synthetic(identifier, value, unit):
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier,
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic test input.",),
    )


def transport(identifier, release=100.0):
    return TransportExperiment(
        experiment_id=identifier,
        domain=RectangularDomain2D(100.0, 100.0, 20.0),
        duration_min=10.0,
        sample_every_min=5.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=synthetic(identifier+".diffusion", 10.0, "micron^2/min"),
        decay=synthetic(identifier+".decay", 0.0, "1/min"),
        initial_concentration=synthetic(
            identifier+".initial", 0.0, "particle_equivalent/micron^3"
        ),
        release_sources=(
            CircularReleaseSource(
                identifier="donor",
                x_micron=50.0,
                y_micron=50.0,
                footprint_radius_micron=10.0,
                release_rate=synthetic(
                    identifier+".release", release, "particle_equivalent/min"
                ),
            ),
        ),
    )


def population_experiment():
    return EVPopulationExperiment(
        experiment_id="two-pop",
        populations=(
            EVPopulationTransport("p.cd9", "phenotype.cd9", transport("transport.cd9", 100.0)),
            EVPopulationTransport("p.cd63", "phenotype.cd63", transport("transport.cd63", 40.0)),
        ),
    )


class PopulationContractTests(unittest.TestCase):
    def test_requires_common_space_and_time_contract(self):
        exp = population_experiment()
        self.assertEqual(tuple(p.population_id for p in exp.populations), ("p.cd9", "p.cd63"))

        bad = TransportExperiment(
            experiment_id="bad",
            domain=RectangularDomain2D(120.0, 100.0, 20.0),
            duration_min=10.0,
            sample_every_min=5.0,
            boundary=BoundaryCondition.NO_FLUX,
            diffusion=synthetic("d", 10, "micron^2/min"),
            decay=synthetic("k", 0, "1/min"),
            initial_concentration=synthetic("c", 0, "particle_equivalent/micron^3"),
        )
        with self.assertRaisesRegex(ValueError, "common domain"):
            EVPopulationExperiment(
                experiment_id="bad-pop",
                populations=(
                    EVPopulationTransport("a", "pa", transport("a")),
                    EVPopulationTransport("b", "pb", bad),
                ),
            )



    def test_population_experiment_document_round_trips(self):
        experiment = population_experiment()
        encoded = serialize_population_experiment_document(experiment)
        restored = deserialize_population_experiment_document(encoded)
        self.assertEqual(restored, experiment)

class PerturbationExecutionTests(unittest.TestCase):
    def test_explicit_release_multiplier_creates_audited_effective_parameter(self):
        base = population_experiment()
        exposure = BiologicalExposure(
            identifier="stim",
            compound_name="synthetic stimulus",
            concentration=synthetic("stim.conc", 1.0, "a.u."),
            target=ExposureTarget.DONOR_CELL_POPULATION,
            start_min=0.0,
            end_min=10.0,
            evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        )
        phenotype = EVPhenotype(
            identifier="phenotype.cd9",
            name="CD9 phenotype",
            markers=(EVMarkerFeature(
                identifier="cd9",
                marker_name="CD9",
                state=MarkerState.POSITIVE,
                evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
            ),),
        )
        effect = PerturbationEffect(
            identifier="stim.release",
            exposure_id="stim",
            outcome=EffectOutcome.EV_RELEASE,
            direction=EffectDirection.INCREASE,
            evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
            phenotype_id="phenotype.cd9",
            model_mapping=ModelEffectMapping(
                target=ModelEffectTarget.RELEASE_RATE,
                operation=EffectOperation.MULTIPLY,
                value=synthetic("release.factor", 2.0, "fold"),
                target_identifier="donor",
            ),
        )
        study = PerturbationStudy(
            study_id="study",
            exposures=(exposure,),
            phenotypes=(phenotype,),
            effects=(effect,),
        )

        resolved = apply_model_effects(base, study)

        self.assertEqual(
            resolved.experiment.populations[0].transport.release_sources[0].release_rate.value,
            200.0,
        )
        self.assertEqual(
            resolved.experiment.populations[1].transport.release_sources[0].release_rate.value,
            40.0,
        )
        self.assertEqual(resolved.applied_effects[0].base_value, 100.0)
        self.assertEqual(resolved.applied_effects[0].effective_value, 200.0)

    def test_contradictory_direction_and_multiplier_are_rejected(self):
        base = population_experiment()
        exposure = BiologicalExposure(
            identifier="stim",
            compound_name="synthetic stimulus",
            concentration=synthetic("stim.conc", 1.0, "a.u."),
            target=ExposureTarget.DONOR_CELL_POPULATION,
            start_min=0.0,
            end_min=10.0,
            evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        )
        phenotype = EVPhenotype(
            identifier="phenotype.cd9",
            name="CD9 phenotype",
            markers=(EVMarkerFeature(
                identifier="cd9",
                marker_name="CD9",
                state=MarkerState.POSITIVE,
                evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
            ),),
        )
        effect = PerturbationEffect(
            identifier="bad.release",
            exposure_id="stim",
            outcome=EffectOutcome.EV_RELEASE,
            direction=EffectDirection.INCREASE,
            evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
            phenotype_id="phenotype.cd9",
            model_mapping=ModelEffectMapping(
                target=ModelEffectTarget.RELEASE_RATE,
                operation=EffectOperation.MULTIPLY,
                value=synthetic("release.factor", 0.5, "fold"),
                target_identifier="donor",
            ),
        )
        study = PerturbationStudy("study", (exposure,), (phenotype,), (effect,))

        with self.assertRaisesRegex(ValueError, "increase effect"):
            apply_model_effects(base, study)

    def test_unmapped_observation_never_changes_the_model(self):
        base = population_experiment()
        exposure = BiologicalExposure(
            identifier="stim",
            compound_name="synthetic stimulus",
            concentration=synthetic("stim.conc", 1.0, "a.u."),
            target=ExposureTarget.DONOR_CELL_POPULATION,
            start_min=0.0,
            end_min=10.0,
            evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        )
        phenotype = EVPhenotype(
            identifier="phenotype.cd9",
            name="CD9 phenotype",
            markers=(EVMarkerFeature(
                identifier="cd9",
                marker_name="CD9",
                state=MarkerState.POSITIVE,
                evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
            ),),
        )
        effect = PerturbationEffect(
            identifier="observed.only",
            exposure_id="stim",
            outcome=EffectOutcome.EV_RELEASE,
            direction=EffectDirection.INCREASE,
            evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
            phenotype_id="phenotype.cd9",
        )
        study = PerturbationStudy("study", (exposure,), (phenotype,), (effect,))

        resolved = apply_model_effects(base, study)
        self.assertEqual(resolved.experiment, base)
        self.assertEqual(resolved.applied_effects, ())


class PopulationRunnerTests(unittest.TestCase):
    def result(self, experiment_id, values):
        grid = BioFVMGrid2D(2, 2, 50.0, 20.0)
        samples = tuple(
            TransportSample(t, v, v, v, v*200000.0, 0.0)
            for t, v in ((0.0, values[0]), (5.0, values[1]), (10.0, values[2]))
        )
        fields = tuple(
            SpatialFieldSnapshot2D(t, (v, v, v, v))
            for t, v in ((0.0, values[0]), (5.0, values[1]), (10.0, values[2]))
        )
        return BioFVMRunResult(
            experiment_id=experiment_id,
            concentration_unit="particle_equivalent/micron^3",
            integrated_quantity_unit="particle_equivalent",
            internalized_quantity_unit="particle_equivalent",
            engine=BioFVMEngineMetadata("BioFVM", "1.14.2", "a"*40, "1.1.7"),
            grid=grid,
            samples=samples,
            field_snapshots=fields,
            recipient_uptake_series=(),
        )

    @patch("vesiclescope.workflows.population_transport.run_transport")
    def test_runs_each_population_and_preserves_separate_fields(self, mocked):
        mocked.side_effect = (
            self.result("transport.cd9", (0.0, 1.0, 2.0)),
            self.result("transport.cd63", (0.0, 0.5, 1.0)),
        )
        result = run_population_transport(
            population_experiment(),
            BioFVMNumerics(50.0, 0.5),
            Path("runner"),
        )

        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(result.populations[0].phenotype_id, "phenotype.cd9")
        self.assertEqual(result.populations[1].phenotype_id, "phenotype.cd63")
        combined = sum_population_fields(result)
        self.assertEqual(combined[-1].values, (3.0, 3.0, 3.0, 3.0))


    @patch("vesiclescope.workflows.population_transport.run_transport")
    def test_population_run_bundle_round_trips_separate_population_results(self, mocked):
        mocked.side_effect = (
            self.result("transport.cd9", (0.0, 1.0, 2.0)),
            self.result("transport.cd63", (0.0, 0.5, 1.0)),
        )
        numerics = BioFVMNumerics(50.0, 0.5)
        experiment = population_experiment()
        result = run_population_transport(experiment, numerics, Path("runner"))
        bundle = PopulationSimulationRunBundle(
            vesiclescope_revision="a" * 40,
            experiment=experiment,
            numerics=numerics,
            result=result,
        )

        encoded = serialize_population_run_bundle(bundle)
        restored = deserialize_population_run_bundle(encoded)

        self.assertEqual(restored, bundle)
        self.assertEqual(
            restored.result.populations[1].result.field_snapshots[-1].values,
            (1.0, 1.0, 1.0, 1.0),
        )


if __name__ == "__main__":
    unittest.main()
