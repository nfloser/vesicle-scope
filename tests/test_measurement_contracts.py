import json
from pathlib import Path
import tempfile
import unittest

from vesiclescope.domain import (
    AssayObservation,
    BloodEVPreanalytics,
    CentrifugationStep,
    LongitudinalEVDataset,
    MeasurementKind,
    MeasurementTimepoint,
    SpecimenKind,
)
from vesiclescope.measurement_files import (
    deserialize_measurement_document,
    read_measurement_document,
    serialize_measurement_document,
    write_measurement_document,
)


class BloodEVPreanalyticsTests(unittest.TestCase):
    def test_records_plasma_processing_without_calling_particles_evs(self) -> None:
        protocol = BloodEVPreanalytics(
            sample_id="sample-001",
            specimen=SpecimenKind.PLASMA,
            anticoagulant="EDTA",
            collection_to_processing_min=20.0,
            centrifugation_steps=(
                CentrifugationStep(
                    relative_centrifugal_force_g=2500.0,
                    duration_min=15.0,
                    retained_fraction="supernatant",
                ),
                CentrifugationStep(
                    relative_centrifugal_force_g=2500.0,
                    duration_min=15.0,
                    retained_fraction="supernatant",
                ),
            ),
            residual_platelet_count_per_ul=120.0,
            hemolysis_assessment="no visible haemolysis",
        )

        self.assertEqual(protocol.specimen, SpecimenKind.PLASMA)
        self.assertEqual(protocol.anticoagulant, "EDTA")
        self.assertEqual(len(protocol.centrifugation_steps), 2)

    def test_plasma_requires_anticoagulant_and_non_negative_processing_delay(self) -> None:
        with self.assertRaises(ValueError):
            BloodEVPreanalytics(
                sample_id="sample-001",
                specimen=SpecimenKind.PLASMA,
                anticoagulant=None,
                collection_to_processing_min=10.0,
            )

        with self.assertRaises(ValueError):
            BloodEVPreanalytics(
                sample_id="sample-001",
                specimen=SpecimenKind.SERUM,
                anticoagulant=None,
                collection_to_processing_min=-1.0,
            )

    def test_centrifugation_step_requires_physical_values(self) -> None:
        with self.assertRaises(ValueError):
            CentrifugationStep(
                relative_centrifugal_force_g=0.0,
                duration_min=15.0,
                retained_fraction="supernatant",
            )


class MeasurementContractTests(unittest.TestCase):
    def test_keeps_particle_count_distinct_from_marker_defined_events(self) -> None:
        particle_count = AssayObservation(
            identifier="nta.particles",
            scientific_name="particle concentration",
            kind=MeasurementKind.PARTICLE_CONCENTRATION,
            value=1.5e10,
            unit="particle/mL",
            method="nanoparticle tracking analysis",
            detection_semantics="All particles detected by scatter-mode NTA in the configured size range.",
        )
        cd9_events = AssayObservation(
            identifier="ifcm.cd9",
            scientific_name="CD9-positive event concentration",
            kind=MeasurementKind.MARKER_POSITIVE_EVENT_CONCENTRATION,
            value=2.5e8,
            unit="event/mL",
            method="imaging flow cytometry",
            markers=("CD9",),
            detection_semantics="Fluorescent events meeting the declared CD9-positive gating criteria.",
        )

        self.assertNotEqual(particle_count.kind, cd9_events.kind)
        self.assertEqual(particle_count.markers, ())
        self.assertEqual(cd9_events.markers, ("CD9",))

    def test_marker_measurements_require_markers(self) -> None:
        with self.assertRaises(ValueError):
            AssayObservation(
                identifier="marker.empty",
                scientific_name="marker signal",
                kind=MeasurementKind.MARKER_SIGNAL,
                value=1.0,
                unit="a.u.",
                method="SP-IRIS",
                detection_semantics="Fluorescence intensity.",
            )

    def test_rejects_duplicate_markers_and_negative_concentrations(self) -> None:
        with self.assertRaises(ValueError):
            AssayObservation(
                identifier="marker.duplicate",
                scientific_name="co-positive events",
                kind=MeasurementKind.MARKER_POSITIVE_EVENT_CONCENTRATION,
                value=1.0,
                unit="event/mL",
                method="SP-IRIS",
                markers=("CD9", "CD9"),
                detection_semantics="Co-positive captured events.",
            )

        with self.assertRaises(ValueError):
            AssayObservation(
                identifier="nta.negative",
                scientific_name="particle concentration",
                kind=MeasurementKind.PARTICLE_CONCENTRATION,
                value=-1.0,
                unit="particle/mL",
                method="NTA",
                detection_semantics="Scatter-mode particle count.",
            )

    def test_timepoints_are_unique_per_condition(self) -> None:
        obs = AssayObservation(
            identifier="nta.particles",
            scientific_name="particle concentration",
            kind=MeasurementKind.PARTICLE_CONCENTRATION,
            value=1.0,
            unit="particle/mL",
            method="NTA",
            detection_semantics="Scatter-mode particle count.",
        )
        protocol = BloodEVPreanalytics(
            sample_id="sample-001",
            specimen=SpecimenKind.PLASMA,
            anticoagulant="EDTA",
            collection_to_processing_min=20.0,
        )

        with self.assertRaises(ValueError):
            LongitudinalEVDataset(
                dataset_id="stress-study",
                samples=(protocol,),
                timepoints=(
                    MeasurementTimepoint(
                        sample_id="sample-001",
                        condition_id="control",
                        time_min=0.0,
                        observations=(obs,),
                    ),
                    MeasurementTimepoint(
                        sample_id="sample-001",
                        condition_id="control",
                        time_min=0.0,
                        observations=(obs,),
                    ),
                ),
            )


    def test_timepoint_may_precede_reference_and_must_reference_known_sample(self) -> None:
        obs = AssayObservation(
            identifier="nta.particles",
            scientific_name="particle concentration",
            kind=MeasurementKind.PARTICLE_CONCENTRATION,
            value=1.0,
            unit="particle/mL",
            method="NTA",
            detection_semantics="Scatter-mode particle count.",
        )
        protocol = BloodEVPreanalytics(
            sample_id="sample-001",
            specimen=SpecimenKind.PLASMA,
            anticoagulant="EDTA",
            collection_to_processing_min=20.0,
        )
        dataset = LongitudinalEVDataset(
            dataset_id="pre-stimulus",
            samples=(protocol,),
            timepoints=(
                MeasurementTimepoint(
                    sample_id="sample-001",
                    condition_id="control",
                    time_min=-5.0,
                    observations=(obs,),
                ),
            ),
        )
        self.assertEqual(dataset.timepoints[0].time_min, -5.0)

        with self.assertRaisesRegex(ValueError, "unknown sample"):
            LongitudinalEVDataset(
                dataset_id="bad-reference",
                samples=(protocol,),
                timepoints=(
                    MeasurementTimepoint(
                        sample_id="missing",
                        condition_id="control",
                        time_min=0.0,
                        observations=(obs,),
                    ),
                ),
            )


class MeasurementDocumentTests(unittest.TestCase):
    def make_dataset(self) -> LongitudinalEVDataset:
        protocol = BloodEVPreanalytics(
            sample_id="sample-001",
            specimen=SpecimenKind.PLASMA,
            anticoagulant="EDTA",
            collection_to_processing_min=20.0,
            centrifugation_steps=(
                CentrifugationStep(
                    relative_centrifugal_force_g=2500.0,
                    duration_min=15.0,
                    retained_fraction="supernatant",
                ),
            ),
            limitations=("Residual platelets may influence downstream EV-associated measurements.",),
        )
        observations = (
            AssayObservation(
                identifier="nta.particles",
                scientific_name="particle concentration",
                kind=MeasurementKind.PARTICLE_CONCENTRATION,
                value=1.5e10,
                unit="particle/mL",
                method="NTA",
                detection_semantics="Scatter-mode particle count; not asserted to equal EV concentration.",
                technical_replicates=3,
                standard_deviation=1.2e9,
            ),
            AssayObservation(
                identifier="spiris.cd9_cd63",
                scientific_name="CD9/CD63 co-positive event concentration",
                kind=MeasurementKind.MARKER_POSITIVE_EVENT_CONCENTRATION,
                value=2.0e7,
                unit="event/mL",
                method="SP-IRIS",
                markers=("CD9", "CD63"),
                detection_semantics="Captured and fluorescently detected co-positive single-particle events.",
            ),
        )
        return LongitudinalEVDataset(
            dataset_id="synthetic.longitudinal-ev",
            samples=(protocol,),
            timepoints=(
                MeasurementTimepoint(
                    sample_id="sample-001",
                    condition_id="control",
                    time_min=0.0,
                    observations=observations,
                ),
                MeasurementTimepoint(
                    sample_id="sample-001",
                    condition_id="stress",
                    time_min=15.0,
                    observations=observations,
                ),
            ),
            reference_time_description="Minutes relative to the declared stimulation reference.",
            limitations=("Synthetic example; not biological evidence.",),
        )

    def test_round_trip_and_digest_are_deterministic(self) -> None:
        dataset = self.make_dataset()
        first = serialize_measurement_document(dataset)
        second = serialize_measurement_document(dataset)

        self.assertEqual(first, second)
        self.assertEqual(deserialize_measurement_document(first), dataset)

        document = json.loads(first)
        self.assertRegex(document["payload_sha256"], r"^[0-9a-f]{64}$")

    def test_tampering_is_rejected(self) -> None:
        document = json.loads(serialize_measurement_document(self.make_dataset()))
        document["payload"]["dataset"]["dataset_id"] = "tampered"

        with self.assertRaisesRegex(ValueError, "digest"):
            deserialize_measurement_document(json.dumps(document))

    def test_filesystem_round_trip_is_exact(self) -> None:
        dataset = self.make_dataset()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "measurements.json"
            returned = write_measurement_document(path, dataset)

            self.assertEqual(returned, path)
            self.assertEqual(read_measurement_document(path), dataset)
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                serialize_measurement_document(dataset),
            )


if __name__ == "__main__":
    unittest.main()
