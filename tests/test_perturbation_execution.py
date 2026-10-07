import unittest
from dataclasses import replace

from vesiclescope.domain import (
    BiologicalExposure,
    EffectDirection,
    EffectOperation,
    EffectOutcome,
    EVMarkerFeature,
    EVPhenotype,
    EvidenceCategory,
    EvidenceSource,
    ExposureTarget,
    MarkerState,
    ModelEffectMapping,
    ModelEffectTarget,
    ParameterContext,
    PerturbationEffect,
    PerturbationStudy,
    PointReleaseSource,
    PointUptakeSink,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
    BoundaryCondition,
)
from vesiclescope.workflows.perturbation_transport import (
    EffectExecutionStatus,
    PopulationTransportSpec,
    resolve_perturbation_transport,
)


def parameter(
    identifier: str,
    value: float,
    unit: str,
    *,
    evidence: EvidenceCategory = EvidenceCategory.SYNTHETIC_BENCHMARK,
    source: EvidenceSource | None = None,
) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=evidence,
        source=source,
        limitations=("Test input; not a biological default.",),
    )


def phenotype(identifier: str) -> EVPhenotype:
    return EVPhenotype(
        identifier=identifier,
        name=identifier,
        markers=(
            EVMarkerFeature(
                identifier=f"{identifier}.marker",
                marker_name="synthetic marker",
                state=MarkerState.UNRESOLVED,
                evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
                limitations=("Synthetic phenotype identity only.",),
            ),
        ),
    )


def transport_experiment(
    experiment_id: str,
    *,
    release: float,
    uptake: float = 0.2,
    decay: float = 0.05,
) -> TransportExperiment:
    return TransportExperiment(
        experiment_id=experiment_id,
        domain=RectangularDomain2D(
            width_micron=100.0,
            height_micron=100.0,
            slice_thickness_micron=10.0,
        ),
        duration_min=10.0,
        sample_every_min=2.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=parameter(f"{experiment_id}.diffusion", 50.0, "micron^2/min"),
        decay=parameter(f"{experiment_id}.decay", decay, "1/min"),
        initial_concentration=parameter(
            f"{experiment_id}.initial",
            0.0,
            "particle_equivalent/micron^3",
        ),
        release_sources=(
            PointReleaseSource(
                identifier="donor",
                x_micron=50.0,
                y_micron=50.0,
                release_rate=parameter(
                    f"{experiment_id}.release",
                    release,
                    "particle_equivalent/min",
                ),
            ),
        ),
        uptake_sinks=(
            PointUptakeSink(
                identifier="recipient",
                x_micron=70.0,
                y_micron=50.0,
                effective_volume_micron3=1000.0,
                uptake_rate=parameter(
                    f"{experiment_id}.uptake",
                    uptake,
                    "1/min",
                ),
            ),
        ),
    )


def exposure() -> BiologicalExposure:
    return BiologicalExposure(
        identifier="stimulus",
        compound_name="declared stimulus",
        concentration=parameter("stimulus.concentration", 1.0, "a.u."),
        target=ExposureTarget.DONOR_CELL_POPULATION,
        start_min=0.0,
        end_min=10.0,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        context=ParameterContext(experimental_conditions="execution contract test"),
        limitations=("Synthetic execution test only.",),
    )


def effect(
    identifier: str,
    phenotype_id: str | None,
    *,
    target: ModelEffectTarget | None,
    operation: EffectOperation = EffectOperation.MULTIPLY,
    value: float = 2.0,
    unit: str = "fold",
    target_identifier: str | None = None,
    direction: EffectDirection = EffectDirection.INCREASE,
) -> PerturbationEffect:
    mapping = None
    if target is not None:
        mapping = ModelEffectMapping(
            target=target,
            operation=operation,
            value=parameter(f"{identifier}.mapping", value, unit),
            target_identifier=target_identifier,
        )
    outcome = {
        ModelEffectTarget.UPTAKE_RATE: EffectOutcome.EV_UPTAKE,
        ModelEffectTarget.DECAY_RATE: EffectOutcome.EV_CLEARANCE,
    }.get(target, EffectOutcome.EV_RELEASE)
    return PerturbationEffect(
        identifier=identifier,
        exposure_id="stimulus",
        outcome=outcome,
        direction=direction,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        phenotype_id=phenotype_id,
        model_mapping=mapping,
        limitations=("Synthetic execution mapping only.",),
    )


def study(*effects: PerturbationEffect) -> PerturbationStudy:
    return PerturbationStudy(
        study_id="two-population-study",
        exposures=(exposure(),),
        phenotypes=(phenotype("population-a"), phenotype("population-b")),
        effects=tuple(effects),
        limitations=("Synthetic execution contract test.",),
    )


class PerturbationExecutionTests(unittest.TestCase):
    def specs(self) -> tuple[PopulationTransportSpec, ...]:
        return (
            PopulationTransportSpec(
                phenotype_id="population-a",
                experiment=transport_experiment("population-a.control", release=100.0),
            ),
            PopulationTransportSpec(
                phenotype_id="population-b",
                experiment=transport_experiment("population-b.control", release=40.0),
            ),
        )

    def test_applies_explicit_release_mapping_only_to_named_population_and_source(self) -> None:
        resolved = resolve_perturbation_transport(
            study(
                effect(
                    "release-a",
                    "population-a",
                    target=ModelEffectTarget.RELEASE_RATE,
                    target_identifier="donor",
                    value=1.5,
                )
            ),
            self.specs(),
        )

        population_a, population_b = resolved.populations
        self.assertEqual(
            population_a.effective_experiment.release_sources[0].release_rate.value,
            150.0,
        )
        self.assertEqual(
            population_b.effective_experiment.release_sources[0].release_rate.value,
            40.0,
        )
        audit = population_a.effects[0]
        self.assertEqual(audit.status, EffectExecutionStatus.APPLIED)
        self.assertEqual(audit.baseline_value, 100.0)
        self.assertEqual(audit.effective_value, 150.0)
        self.assertEqual(audit.unit, "particle_equivalent/min")

    def test_supports_explicit_uptake_and_decay_mappings(self) -> None:
        resolved = resolve_perturbation_transport(
            study(
                effect(
                    "uptake-a",
                    "population-a",
                    target=ModelEffectTarget.UPTAKE_RATE,
                    operation=EffectOperation.ADD,
                    value=0.1,
                    unit="1/min",
                    target_identifier="recipient",
                ),
                effect(
                    "decay-b",
                    "population-b",
                    target=ModelEffectTarget.DECAY_RATE,
                    operation=EffectOperation.SET,
                    value=0.2,
                    unit="1/min",
                    direction=EffectDirection.INCREASE,
                ),
            ),
            self.specs(),
        )

        self.assertAlmostEqual(
            resolved.populations[0].effective_experiment.uptake_sinks[0].uptake_rate.value,
            0.3,
        )
        self.assertAlmostEqual(
            resolved.populations[1].effective_experiment.decay.value,
            0.2,
        )

    def test_effect_without_mapping_remains_visible_and_does_not_change_transport(self) -> None:
        no_mapping = effect(
            "qualitative-only",
            "population-a",
            target=None,
        )
        resolved = resolve_perturbation_transport(study(no_mapping), self.specs())

        population = resolved.populations[0]
        self.assertEqual(population.baseline_experiment, population.effective_experiment)
        self.assertEqual(population.effects[0].status, EffectExecutionStatus.NOT_EXECUTED)
        self.assertIn("no model mapping", population.effects[0].reason)

    def test_marker_cargo_and_fraction_mappings_are_not_silently_transport_effects(self) -> None:
        resolved = resolve_perturbation_transport(
            study(
                effect(
                    "fraction-a",
                    "population-a",
                    target=ModelEffectTarget.PHENOTYPE_FRACTION,
                    target_identifier="population-a",
                )
            ),
            self.specs(),
        )

        audit = resolved.populations[0].effects[0]
        self.assertEqual(audit.status, EffectExecutionStatus.NOT_EXECUTED)
        self.assertIn("not a transport parameter", audit.reason)
        self.assertEqual(
            resolved.populations[0].baseline_experiment,
            resolved.populations[0].effective_experiment,
        )

    def test_effect_without_phenotype_is_reported_unassigned_not_broadcast(self) -> None:
        unresolved = effect(
            "ambiguous-release",
            None,
            target=ModelEffectTarget.RELEASE_RATE,
            target_identifier="donor",
        )
        resolved = resolve_perturbation_transport(study(unresolved), self.specs())

        self.assertEqual(len(resolved.unexecuted_effects), 1)
        self.assertEqual(
            resolved.unexecuted_effects[0].status,
            EffectExecutionStatus.NOT_EXECUTED,
        )
        self.assertIn("phenotype", resolved.unexecuted_effects[0].reason)
        self.assertEqual(
            resolved.populations[0].baseline_experiment,
            resolved.populations[0].effective_experiment,
        )
        self.assertEqual(
            resolved.populations[1].baseline_experiment,
            resolved.populations[1].effective_experiment,
        )

    def test_rejects_multiply_without_fold_unit(self) -> None:
        with self.assertRaisesRegex(ValueError, "fold"):
            resolve_perturbation_transport(
                study(
                    effect(
                        "bad-multiply",
                        "population-a",
                        target=ModelEffectTarget.RELEASE_RATE,
                        target_identifier="donor",
                        unit="percent",
                    )
                ),
                self.specs(),
            )

    def test_rejects_add_or_set_with_incompatible_unit(self) -> None:
        with self.assertRaisesRegex(ValueError, "same unit"):
            resolve_perturbation_transport(
                study(
                    effect(
                        "bad-add",
                        "population-a",
                        target=ModelEffectTarget.UPTAKE_RATE,
                        operation=EffectOperation.ADD,
                        value=1.0,
                        unit="fold",
                        target_identifier="recipient",
                    )
                ),
                self.specs(),
            )

    def test_rejects_unknown_explicit_transport_target_identifier(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown release source"):
            resolve_perturbation_transport(
                study(
                    effect(
                        "missing-source",
                        "population-a",
                        target=ModelEffectTarget.RELEASE_RATE,
                        target_identifier="not-present",
                    )
                ),
                self.specs(),
            )

    def test_rejects_ambiguous_direction_for_deterministic_mapping(self) -> None:
        for direction in (EffectDirection.UNKNOWN, EffectDirection.MIXED):
            with self.subTest(direction=direction):
                with self.assertRaisesRegex(ValueError, "deterministic"):
                    resolve_perturbation_transport(
                        study(
                            effect(
                                "ambiguous-direction",
                                "population-a",
                                target=ModelEffectTarget.RELEASE_RATE,
                                target_identifier="donor",
                                direction=direction,
                            )
                        ),
                        self.specs(),
                    )

    def test_rejects_mapping_that_contradicts_reported_direction(self) -> None:
        with self.assertRaisesRegex(ValueError, "direction"):
            resolve_perturbation_transport(
                study(
                    effect(
                        "wrong-direction",
                        "population-a",
                        target=ModelEffectTarget.RELEASE_RATE,
                        target_identifier="donor",
                        value=0.5,
                        direction=EffectDirection.INCREASE,
                    )
                ),
                self.specs(),
            )

    def test_rejects_outcome_to_transport_target_mismatch(self) -> None:
        mismatched = PerturbationEffect(
            identifier="mismatched-outcome",
            exposure_id="stimulus",
            outcome=EffectOutcome.EV_UPTAKE,
            direction=EffectDirection.INCREASE,
            evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
            phenotype_id="population-a",
            model_mapping=ModelEffectMapping(
                target=ModelEffectTarget.RELEASE_RATE,
                operation=EffectOperation.MULTIPLY,
                value=parameter("mismatched.mapping", 2.0, "fold"),
                target_identifier="donor",
            ),
        )
        with self.assertRaisesRegex(ValueError, "outcome"):
            resolve_perturbation_transport(study(mismatched), self.specs())

    def test_rejects_two_effects_that_target_the_same_transport_parameter(self) -> None:
        first = effect(
            "first",
            "population-a",
            target=ModelEffectTarget.RELEASE_RATE,
            target_identifier="donor",
            value=1.2,
        )
        second = replace(
            effect(
                "second",
                "population-a",
                target=ModelEffectTarget.RELEASE_RATE,
                target_identifier="donor",
                value=1.3,
            ),
            exposure_id="stimulus",
        )
        with self.assertRaisesRegex(ValueError, "multiple effects"):
            resolve_perturbation_transport(study(first, second), self.specs())


if __name__ == "__main__":
    unittest.main()
