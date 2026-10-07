import json
import unittest

from vesiclescope.domain import (
    BiologicalExposure,
    CargoClass,
    EffectDirection,
    EffectOutcome,
    EVMarkerFeature,
    EVPhenotype,
    EVCargoFeature,
    EvidenceCategory,
    EvidenceSource,
    ExposureTarget,
    MarkerState,
    ModelEffectMapping,
    ModelEffectTarget,
    EffectOperation,
    ParameterContext,
    PerturbationEffect,
    PerturbationStudy,
    ScientificParameter,
)
from vesiclescope.perturbation_files import (
    deserialize_perturbation_document,
    serialize_perturbation_document,
)


def literature_parameter(
    identifier: str,
    value: float,
    unit: str,
    source: str = "PMID:42059363",
) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.LITERATURE_ESTIMATE,
        source=EvidenceSource(source),
        limitations=("Context-specific literature value; not a universal default.",),
    )


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
        limitations=("Synthetic mapping test; not biological evidence.",),
    )


class ExposureContractTests(unittest.TestCase):
    def test_records_time_bounded_hormone_exposure(self) -> None:
        exposure = BiologicalExposure(
            identifier="dex-neuronal",
            compound_name="dexamethasone",
            concentration=literature_parameter("exposure.dex", 5.0, "uM"),
            target=ExposureTarget.DONOR_CELL_POPULATION,
            start_min=0.0,
            end_min=1440.0,
            evidence=EvidenceCategory.MEASURED_RELATED_CONTEXT,
            source=EvidenceSource("PMID:42059363"),
            context=ParameterContext(cell_line="Neuro2a"),
            limitations=("Neuronal cell-line context; not a human blood default.",),
        )

        self.assertEqual(exposure.target, ExposureTarget.DONOR_CELL_POPULATION)
        self.assertEqual(exposure.compound_name, "dexamethasone")

    def test_exposure_requires_forward_time_window_and_evidence_source(self) -> None:
        with self.assertRaises(ValueError):
            BiologicalExposure(
                identifier="bad-window",
                compound_name="cortisol",
                concentration=literature_parameter("exposure.cortisol", 100.0, "nM"),
                target=ExposureTarget.BLOOD_CELL_POPULATION,
                start_min=10.0,
                end_min=10.0,
                evidence=EvidenceCategory.LITERATURE_ESTIMATE,
                source=EvidenceSource("PMID:1"),
            )

        with self.assertRaises(ValueError):
            BiologicalExposure(
                identifier="missing-source",
                compound_name="cortisol",
                concentration=literature_parameter("exposure.cortisol", 100.0, "nM"),
                target=ExposureTarget.BLOOD_CELL_POPULATION,
                start_min=0.0,
                end_min=60.0,
                evidence=EvidenceCategory.LITERATURE_ESTIMATE,
            )


class EVPhenotypeTests(unittest.TestCase):
    def test_marker_panel_and_cargo_are_explicit_features(self) -> None:
        phenotype = EVPhenotype(
            identifier="stress-ev",
            name="stress-associated EV phenotype",
            markers=(
                EVMarkerFeature(
                    identifier="marker.cd9",
                    marker_name="CD9",
                    state=MarkerState.POSITIVE,
                    evidence=EvidenceCategory.MEASURED_RELATED_CONTEXT,
                    source=EvidenceSource("PMCID:PMC12511347"),
                ),
                EVMarkerFeature(
                    identifier="marker.cd41",
                    marker_name="CD41",
                    state=MarkerState.UNRESOLVED,
                    evidence=EvidenceCategory.ASSUMED,
                    limitations=("Not measured in this synthetic phenotype.",),
                ),
            ),
            cargo=(
                EVCargoFeature(
                    identifier="cargo.ace",
                    molecule_name="angiotensin-converting enzyme",
                    cargo_class=CargoClass.PROTEIN,
                    evidence=EvidenceCategory.MEASURED_RELATED_CONTEXT,
                    source=EvidenceSource("PMID:35832088"),
                    qualitative_state="reported increased under norepinephrine in the source context",
                ),
            ),
        )

        self.assertEqual(phenotype.markers[0].marker_name, "CD9")
        self.assertEqual(phenotype.cargo[0].cargo_class, CargoClass.PROTEIN)

    def test_cargo_requires_a_measured_or_qualitative_quantity(self) -> None:
        with self.assertRaises(ValueError):
            EVCargoFeature(
                identifier="cargo.empty",
                molecule_name="unknown cargo",
                cargo_class=CargoClass.OTHER,
                evidence=EvidenceCategory.ASSUMED,
            )


class PerturbationEffectTests(unittest.TestCase):
    def make_exposure(self) -> BiologicalExposure:
        return BiologicalExposure(
            identifier="ne-af",
            compound_name="norepinephrine",
            concentration=literature_parameter(
                "exposure.norepinephrine",
                10.0,
                "uM",
                "PMID:35832088",
            ),
            target=ExposureTarget.DONOR_CELL_POPULATION,
            start_min=0.0,
            end_min=1440.0,
            evidence=EvidenceCategory.MEASURED_RELATED_CONTEXT,
            source=EvidenceSource("PMID:35832088"),
            context=ParameterContext(cell_type="adventitial fibroblast"),
        )

    def make_phenotype(self) -> EVPhenotype:
        return EVPhenotype(
            identifier="af-small-ev",
            name="adventitial fibroblast small-EV phenotype",
            markers=(
                EVMarkerFeature(
                    identifier="marker.generic",
                    marker_name="EV-associated phenotype",
                    state=MarkerState.UNRESOLVED,
                    evidence=EvidenceCategory.ASSUMED,
                    limitations=("Placeholder phenotype identity only.",),
                ),
            ),
            cargo=(
                EVCargoFeature(
                    identifier="cargo.ace",
                    molecule_name="angiotensin-converting enzyme",
                    cargo_class=CargoClass.PROTEIN,
                    evidence=EvidenceCategory.MEASURED_RELATED_CONTEXT,
                    source=EvidenceSource("PMID:35832088"),
                    qualitative_state="increased",
                ),
            ),
        )

    def test_effect_is_separate_from_exposure_and_mapping_is_explicit(self) -> None:
        effect = PerturbationEffect(
            identifier="ne-release-effect",
            exposure_id="ne-af",
            outcome=EffectOutcome.EV_RELEASE,
            direction=EffectDirection.INCREASE,
            evidence=EvidenceCategory.MEASURED_RELATED_CONTEXT,
            source=EvidenceSource("PMID:35832088"),
            phenotype_id="af-small-ev",
            magnitude=synthetic_parameter(
                "effect.release.fold",
                1.5,
                "fold",
            ),
            model_mapping=ModelEffectMapping(
                target=ModelEffectTarget.RELEASE_RATE,
                operation=EffectOperation.MULTIPLY,
                value=synthetic_parameter(
                    "mapping.release.multiplier",
                    1.5,
                    "fold",
                ),
            ),
            limitations=("Illustrative mapping; source-specific context must be preserved.",),
        )

        study = PerturbationStudy(
            study_id="norepinephrine-af",
            exposures=(self.make_exposure(),),
            phenotypes=(self.make_phenotype(),),
            effects=(effect,),
        )

        self.assertEqual(study.effects[0].exposure_id, "ne-af")
        self.assertEqual(
            study.effects[0].model_mapping.target,
            ModelEffectTarget.RELEASE_RATE,
        )

    def test_study_rejects_unknown_references(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown exposure"):
            PerturbationStudy(
                study_id="bad-study",
                exposures=(self.make_exposure(),),
                phenotypes=(self.make_phenotype(),),
                effects=(
                    PerturbationEffect(
                        identifier="bad-effect",
                        exposure_id="missing",
                        outcome=EffectOutcome.EV_RELEASE,
                        direction=EffectDirection.INCREASE,
                        evidence=EvidenceCategory.ASSUMED,
                    ),
                ),
            )


class PerturbationDocumentTests(unittest.TestCase):
    def make_study(self) -> PerturbationStudy:
        exposure = BiologicalExposure(
            identifier="gc-neuronal",
            compound_name="glucocorticoid",
            concentration=literature_parameter("exposure.gc", 5.0, "uM"),
            target=ExposureTarget.DONOR_CELL_POPULATION,
            start_min=0.0,
            end_min=1440.0,
            evidence=EvidenceCategory.MEASURED_RELATED_CONTEXT,
            source=EvidenceSource("PMID:42059363"),
            context=ParameterContext(cell_line="Neuro2a"),
        )
        phenotype = EVPhenotype(
            identifier="cd63-associated",
            name="CD63-associated sEV phenotype",
            markers=(
                EVMarkerFeature(
                    identifier="marker.cd63",
                    marker_name="CD63",
                    state=MarkerState.POSITIVE,
                    evidence=EvidenceCategory.MEASURED_RELATED_CONTEXT,
                    source=EvidenceSource("PMID:42059363"),
                ),
            ),
        )
        effect = PerturbationEffect(
            identifier="gc-release",
            exposure_id=exposure.identifier,
            outcome=EffectOutcome.EV_RELEASE,
            direction=EffectDirection.INCREASE,
            evidence=EvidenceCategory.MEASURED_RELATED_CONTEXT,
            source=EvidenceSource("PMID:42059363"),
            phenotype_id=phenotype.identifier,
            limitations=("No universal human-blood release multiplier is implied.",),
        )
        return PerturbationStudy(
            study_id="gc-neuronal-study",
            exposures=(exposure,),
            phenotypes=(phenotype,),
            effects=(effect,),
            measurement_dataset_ids=("future-measurement-dataset",),
            limitations=("Literature-context contract example.",),
        )

    def test_round_trip_is_deterministic_and_integrity_protected(self) -> None:
        study = self.make_study()
        first = serialize_perturbation_document(study)
        second = serialize_perturbation_document(study)

        self.assertEqual(first, second)
        self.assertEqual(deserialize_perturbation_document(first), study)
        self.assertRegex(json.loads(first)["payload_sha256"], r"^[0-9a-f]{64}$")

    def test_tampering_is_rejected(self) -> None:
        document = json.loads(serialize_perturbation_document(self.make_study()))
        document["payload"]["study"]["study_id"] = "tampered"

        with self.assertRaisesRegex(ValueError, "digest"):
            deserialize_perturbation_document(json.dumps(document))


if __name__ == "__main__":
    unittest.main()
