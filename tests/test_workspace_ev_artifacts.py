import json
import tempfile
import unittest
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen

from vesiclescope.domain import (
    AssayObservation,
    BiologicalExposure,
    BloodEVPreanalytics,
    EVMarkerFeature,
    EVPhenotype,
    EvidenceCategory,
    EvidenceSource,
    ExposureTarget,
    LongitudinalEVDataset,
    MarkerState,
    MeasurementKind,
    MeasurementTimepoint,
    PerturbationStudy,
    ScientificParameter,
    SpecimenKind,
)
from vesiclescope.measurement_files import serialize_measurement_document
from vesiclescope.perturbation_files import serialize_perturbation_document
from vesiclescope.ui.app import WorkspaceApplication
from vesiclescope.ui.server import create_server
from vesiclescope.ui.workspace import Workspace


def parameter(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.LITERATURE_ESTIMATE,
        source=EvidenceSource("PMID:123456"),
        limitations=("Context-specific test value.",),
    )


def measurement_dataset() -> LongitudinalEVDataset:
    sample = BloodEVPreanalytics(
        sample_id="plasma-001",
        specimen=SpecimenKind.PLASMA,
        anticoagulant="EDTA",
        collection_to_processing_min=20.0,
        hemolysis_assessment="no visible haemolysis",
        limitations=("Synthetic workspace fixture.",),
    )
    total = AssayObservation(
        identifier="nta.total",
        scientific_name="particle concentration",
        kind=MeasurementKind.PARTICLE_CONCENTRATION,
        value=1.2e10,
        unit="particle/mL",
        method="NTA",
        detection_semantics="Scatter-detected particles; not asserted to equal EV concentration.",
    )
    marker = AssayObservation(
        identifier="spiris.cd9",
        scientific_name="CD9-positive event concentration",
        kind=MeasurementKind.MARKER_POSITIVE_EVENT_CONCENTRATION,
        value=2.5e8,
        unit="event/mL",
        method="SP-IRIS",
        detection_semantics="Events meeting the declared CD9-positive assay criteria.",
        markers=("CD9",),
    )
    return LongitudinalEVDataset(
        dataset_id="stress-panel",
        samples=(sample,),
        timepoints=(
            MeasurementTimepoint(
                sample_id="plasma-001",
                condition_id="control",
                time_min=0.0,
                observations=(total, marker),
            ),
            MeasurementTimepoint(
                sample_id="plasma-001",
                condition_id="cortisol",
                time_min=30.0,
                observations=(total, marker),
            ),
        ),
        reference_time_description="minutes from declared stimulation start",
        limitations=("Synthetic UI fixture; not experimental evidence.",),
    )


def perturbation_study() -> PerturbationStudy:
    phenotype = EVPhenotype(
        identifier="cd9-positive",
        name="CD9-positive EV-associated population",
        markers=(
            EVMarkerFeature(
                identifier="marker.cd9",
                marker_name="CD9",
                state=MarkerState.POSITIVE,
                evidence=EvidenceCategory.MEASURED_RELATED_CONTEXT,
                source=EvidenceSource("PMCID:PMC000001"),
                limitations=("Source-context marker identity only.",),
            ),
        ),
        limitations=("No phenotype fraction is inferred.",),
    )
    exposure = BiologicalExposure(
        identifier="cortisol-exposure",
        compound_name="cortisol",
        concentration=parameter("exposure.cortisol", 100.0, "nM"),
        target=ExposureTarget.BLOOD_CELL_POPULATION,
        start_min=0.0,
        end_min=30.0,
        evidence=EvidenceCategory.LITERATURE_ESTIMATE,
        source=EvidenceSource("PMID:123456"),
        limitations=("Illustrative context-specific exposure.",),
    )
    return PerturbationStudy(
        study_id="stress-panel-stimulation",
        exposures=(exposure,),
        phenotypes=(phenotype,),
        effects=(),
        measurement_dataset_ids=("stress-panel",),
        limitations=("No cortisol response magnitude is inferred.",),
    )


class WorkspaceEVArtifactTests(unittest.TestCase):
    def test_keeps_measurements_perturbations_and_population_runs_in_separate_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory)).initialize()

            self.assertTrue(workspace.measurements_dir.is_dir())
            self.assertTrue(workspace.perturbations_dir.is_dir())
            self.assertTrue(workspace.population_runs_dir.is_dir())
            self.assertNotEqual(workspace.measurements_dir, workspace.experiments_dir)
            self.assertNotEqual(workspace.perturbations_dir, workspace.experiments_dir)
            self.assertNotEqual(workspace.population_runs_dir, workspace.runs_dir)

    def test_imports_and_reads_integrity_checked_measurement_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory)).initialize()
            document = serialize_measurement_document(measurement_dataset())

            path = workspace.import_measurement("stress.measurements.json", document)
            restored = workspace.read_measurement(path.name)

            self.assertEqual(restored, measurement_dataset())
            self.assertEqual(workspace.list_measurement_names(), ("stress.measurements.json",))

    def test_imports_and_reads_integrity_checked_perturbation_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory)).initialize()
            document = serialize_perturbation_document(perturbation_study())

            path = workspace.import_perturbation("stress.study.json", document)
            restored = workspace.read_perturbation(path.name)

            self.assertEqual(restored, perturbation_study())
            self.assertEqual(workspace.list_perturbation_names(), ("stress.study.json",))

    def test_rejects_invalid_documents_without_creating_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory)).initialize()

            with self.assertRaises(ValueError):
                workspace.import_measurement("bad.json", "{")
            with self.assertRaises(ValueError):
                workspace.import_perturbation("bad.json", "{}")

            self.assertEqual(workspace.list_measurement_names(), ())
            self.assertEqual(workspace.list_perturbation_names(), ())

    def test_existing_workspace_name_confinement_applies_to_new_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory)).initialize()

            with self.assertRaises(ValueError):
                workspace.measurement_path("../escape.json")
            with self.assertRaises(ValueError):
                workspace.perturbation_path("/tmp/escape.json")
            with self.assertRaises(ValueError):
                workspace.population_run_path("no-extension")

    def test_loopback_api_imports_and_inspects_measurement_and_perturbation_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root / "workspace").initialize()
            runner = root / "runner"
            runner.write_text("", encoding="utf-8")
            app = WorkspaceApplication(workspace, runner, "b" * 40)
            server = create_server(app, port=0)
            _, port = server.server_address
            base = f"http://127.0.0.1:{port}"
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for path, name, document in (
                    (
                        "/api/measurement/import",
                        "stress.measurements.json",
                        serialize_measurement_document(measurement_dataset()),
                    ),
                    (
                        "/api/perturbation/import",
                        "stress.study.json",
                        serialize_perturbation_document(perturbation_study()),
                    ),
                ):
                    request = Request(
                        base + path,
                        method="POST",
                        data=json.dumps(
                            {"name": name, "document": document}
                        ).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                    )
                    with urlopen(request, timeout=30) as response:
                        self.assertEqual(response.status, 201)

                with urlopen(
                    f"{base}/api/measurement?name=stress.measurements.json",
                    timeout=30,
                ) as response:
                    measured = json.loads(response.read().decode("utf-8"))
                self.assertEqual(measured["dataset_id"], "stress-panel")
                self.assertEqual(measured["samples"][0]["specimen"], "plasma")
                observations = measured["timepoints"][0]["observations"]
                self.assertFalse(observations[0]["marker_defined"])
                self.assertTrue(observations[1]["marker_defined"])
                self.assertEqual(observations[1]["markers"], ["CD9"])

                with urlopen(
                    f"{base}/api/perturbation?name=stress.study.json",
                    timeout=30,
                ) as response:
                    study = json.loads(response.read().decode("utf-8"))
                self.assertEqual(study["study_id"], "stress-panel-stimulation")
                self.assertEqual(study["exposures"][0]["compound_name"], "cortisol")
                self.assertEqual(
                    study["exposures"][0]["source"]["identifier"],
                    "PMID:123456",
                )
                self.assertEqual(study["phenotypes"][0]["markers"][0]["state"], "positive")
                self.assertIn(
                    "No phenotype fraction",
                    study["phenotypes"][0]["limitations"][0],
                )

                with urlopen(f"{base}/api/state", timeout=30) as response:
                    state = json.loads(response.read().decode("utf-8"))
                self.assertEqual(
                    [item["name"] for item in state["measurements"]],
                    ["stress.measurements.json"],
                )
                self.assertEqual(
                    [item["name"] for item in state["perturbations"]],
                    ["stress.study.json"],
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_application_state_surfaces_scientific_artifacts_without_relabelling_them_as_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root / "workspace").initialize()
            workspace.import_measurement(
                "stress.measurements.json",
                serialize_measurement_document(measurement_dataset()),
            )
            workspace.import_perturbation(
                "stress.study.json",
                serialize_perturbation_document(perturbation_study()),
            )
            runner = root / "runner"
            runner.write_text("", encoding="utf-8")

            state = WorkspaceApplication(workspace, runner, "a" * 40).state()

            self.assertEqual(state["experiments"], [])
            self.assertEqual(state["runs"], [])
            self.assertEqual(
                state["measurements"][0]["dataset_id"],
                "stress-panel",
            )
            self.assertEqual(
                state["perturbations"][0]["study_id"],
                "stress-panel-stimulation",
            )
            self.assertEqual(state["population_runs"], [])


if __name__ == "__main__":
    unittest.main()
