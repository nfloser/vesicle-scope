from pathlib import Path
from threading import Thread
import json
import os
import tempfile
import unittest
from urllib.request import Request, urlopen

from vesiclescope.domain import (
    AssayObservation,
    BiologicalExposure,
    BloodEVPreanalytics,
    EffectDirection,
    EffectOperation,
    EffectOutcome,
    EVMarkerFeature,
    EVPhenotype,
    EvidenceCategory,
    ExposureTarget,
    LongitudinalEVDataset,
    MarkerState,
    MeasurementKind,
    MeasurementTimepoint,
    ModelEffectMapping,
    ModelEffectTarget,
    PerturbationEffect,
    PerturbationStudy,
    ScientificParameter,
    SpecimenKind,
)
from vesiclescope.measurement_files import serialize_measurement_document
from vesiclescope.perturbation_files import serialize_perturbation_document
from vesiclescope.population_run_bundles import deserialize_population_run_bundle
from vesiclescope.ui.app import WorkspaceApplication
from vesiclescope.ui.server import create_server
from vesiclescope.ui.workspace import Workspace


RUNNER = os.environ.get("VESICLESCOPE_BIOFVM_RUNNER")
REVISION = os.environ.get("VESICLESCOPE_REVISION")


def request_json(url: str, *, method: str = "GET", payload: dict | None = None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, method=method, data=data, headers=headers)
    with urlopen(request, timeout=60) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def synthetic_parameter(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic end-to-end workspace fixture.",),
    )


def phenotype(identifier: str, marker: str) -> EVPhenotype:
    return EVPhenotype(
        identifier=identifier,
        name=identifier.replace("-", " "),
        markers=(
            EVMarkerFeature(
                identifier=f"{identifier}.{marker.lower()}",
                marker_name=marker,
                state=MarkerState.POSITIVE,
                evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
                limitations=("Synthetic marker identity only.",),
            ),
        ),
        limitations=("Synthetic phenotype; no biological fraction is implied.",),
    )


def study(release_source_id: str) -> PerturbationStudy:
    exposure = BiologicalExposure(
        identifier="synthetic-cortisol",
        compound_name="cortisol",
        concentration=synthetic_parameter("synthetic.cortisol", 100.0, "nM"),
        target=ExposureTarget.DONOR_CELL_POPULATION,
        start_min=0.0,
        end_min=10.0,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic stimulation used only to exercise the workflow.",),
    )
    stimulated = phenotype("stimulated-ev", "CD9")
    control = phenotype("control-ev", "CD63")
    effect = PerturbationEffect(
        identifier="synthetic-release-effect",
        exposure_id=exposure.identifier,
        outcome=EffectOutcome.EV_RELEASE,
        direction=EffectDirection.INCREASE,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        phenotype_id=stimulated.identifier,
        model_mapping=ModelEffectMapping(
            target=ModelEffectTarget.RELEASE_RATE,
            operation=EffectOperation.MULTIPLY,
            value=synthetic_parameter("synthetic.release.fold", 1.5, "fold"),
            target_identifier=release_source_id,
        ),
        limitations=("Synthetic effect magnitude; not a cortisol response claim.",),
    )
    return PerturbationStudy(
        study_id="synthetic-cortisol-workspace",
        exposures=(exposure,),
        phenotypes=(stimulated, control),
        effects=(effect,),
        measurement_dataset_ids=("synthetic-cortisol-measurements",),
        limitations=("End-to-end software verification only.",),
    )


def measurements() -> LongitudinalEVDataset:
    sample = BloodEVPreanalytics(
        sample_id="plasma-e2e",
        specimen=SpecimenKind.PLASMA,
        anticoagulant="EDTA",
        collection_to_processing_min=15.0,
        limitations=("Synthetic pre-analytics fixture.",),
    )
    observation = AssayObservation(
        identifier="model.mean",
        scientific_name="synthetic model-aligned concentration",
        kind=MeasurementKind.EV_ASSOCIATED_EVENT_CONCENTRATION,
        value=0.0,
        unit="particle_equivalent/micron^3",
        method="synthetic exact-time adapter fixture",
        detection_semantics=(
            "Synthetic quantity intentionally expressed in the model unit for "
            "software verification; not an assay calibration claim."
        ),
    )
    return LongitudinalEVDataset(
        dataset_id="synthetic-cortisol-measurements",
        samples=(sample,),
        timepoints=(
            MeasurementTimepoint(
                sample_id=sample.sample_id,
                condition_id="stimulated",
                time_min=0.0,
                observations=(observation,),
            ),
        ),
        limitations=("Synthetic end-to-end fixture.",),
    )


@unittest.skipUnless(
    RUNNER and REVISION,
    "native runner and exact VesicleScope revision are required",
)
class InteractiveEVWorkspaceEndToEndTests(unittest.TestCase):
    def test_import_execute_inspect_and_compare_population_study(self) -> None:
        assert RUNNER is not None
        assert REVISION is not None

        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace").initialize()
            app = WorkspaceApplication(workspace, Path(RUNNER), REVISION)
            server = create_server(app, port=0)
            _, port = server.server_address
            base = f"http://127.0.0.1:{port}"
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, _ = request_json(
                    f"{base}/api/example",
                    method="POST",
                    payload={"name": "baseline.json"},
                )
                self.assertEqual(status, 201)
                status, baseline = request_json(
                    f"{base}/api/experiment?name=baseline.json"
                )
                self.assertEqual(status, 200)
                release_source_id = baseline["release_sources"][0]["identifier"]
                baseline_release = baseline["release_sources"][0]["rate"]

                status, imported_measurement = request_json(
                    f"{base}/api/measurement/import",
                    method="POST",
                    payload={
                        "name": "cortisol.measurements.json",
                        "document": serialize_measurement_document(measurements()),
                    },
                )
                self.assertEqual(status, 201)
                self.assertEqual(
                    imported_measurement["name"],
                    "cortisol.measurements.json",
                )

                status, imported_study = request_json(
                    f"{base}/api/perturbation/import",
                    method="POST",
                    payload={
                        "name": "cortisol.study.json",
                        "document": serialize_perturbation_document(
                            study(release_source_id)
                        ),
                    },
                )
                self.assertEqual(status, 201)
                self.assertEqual(imported_study["name"], "cortisol.study.json")

                status, created = request_json(
                    f"{base}/api/population-run",
                    method="POST",
                    payload={
                        "perturbation": "cortisol.study.json",
                        "population_experiments": {
                            "stimulated-ev": "baseline.json",
                            "control-ev": "baseline.json",
                        },
                        "run_name": "cortisol.population-run.json",
                        "grid_spacing_micron": 20.0,
                        "time_step_min": 0.1,
                    },
                )
                self.assertEqual(status, 201)
                self.assertEqual(
                    created["name"],
                    "cortisol.population-run.json",
                )

                status, inspected = request_json(
                    f"{base}/api/population-run?name=cortisol.population-run.json"
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    inspected["study"]["study_id"],
                    "synthetic-cortisol-workspace",
                )
                by_population = {
                    item["phenotype_id"]: item
                    for item in inspected["populations"]
                }
                self.assertEqual(set(by_population), {"stimulated-ev", "control-ev"})
                stimulated = by_population["stimulated-ev"]
                control = by_population["control-ev"]
                self.assertEqual(stimulated["effects"][0]["status"], "applied")
                self.assertEqual(
                    stimulated["effective_experiment"]["release_sources"][0]["rate"],
                    baseline_release * 1.5,
                )
                self.assertEqual(control["effects"], [])
                self.assertEqual(
                    len(inspected["aggregate"]["fields"]),
                    len(stimulated["fields"]),
                )
                self.assertGreater(
                    inspected["aggregate"]["samples"][-1]["extracellular_quantity"],
                    stimulated["samples"][-1]["extracellular_quantity"],
                )

                status, comparison = request_json(
                    f"{base}/api/measurement-comparison",
                    method="POST",
                    payload={
                        "measurement": "cortisol.measurements.json",
                        "population_run": "cortisol.population-run.json",
                        "condition_id": "stimulated",
                        "population": "total",
                        "targets": [
                            {
                                "observation_identifier": "model.mean",
                                "observable": "mean_concentration",
                            }
                        ],
                    },
                )
                self.assertEqual(status, 200)
                self.assertEqual(len(comparison["matches"]), 1)
                match = comparison["matches"][0]
                self.assertTrue(match["exact_time_match"])
                self.assertTrue(match["unit_compatible"])
                self.assertEqual(match["time_min"], 0.0)
                self.assertEqual(
                    match["residual_prediction_minus_measurement"],
                    0.0,
                )

                with urlopen(
                    f"{base}/download/population-run?name=cortisol.population-run.json",
                    timeout=30,
                ) as response:
                    stored = deserialize_population_run_bundle(response.read())
                self.assertEqual(stored.study.study_id, "synthetic-cortisol-workspace")
                self.assertEqual(len(stored.populations), 2)

                status, state = request_json(f"{base}/api/state")
                self.assertEqual(status, 200)
                self.assertEqual(
                    state["population_runs"][0]["name"],
                    "cortisol.population-run.json",
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
