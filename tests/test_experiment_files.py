import json
from pathlib import Path
import tempfile
import unittest

from vesiclescope.experiment_files import (
    EXPERIMENT_DOCUMENT_SCHEMA,
    EXPERIMENT_DOCUMENT_VERSION,
    deserialize_experiment_document,
    read_experiment_document,
    serialize_experiment_document,
    write_experiment_document,
)
from vesiclescope.scenarios import diffusion_uptake_factor_conditions


class ExperimentDocumentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.experiment = diffusion_uptake_factor_conditions()[4].experiment

    def test_round_trip_preserves_the_complete_experiment(self) -> None:
        serialized = serialize_experiment_document(self.experiment)
        restored = deserialize_experiment_document(serialized)
        self.assertEqual(restored, self.experiment)

    def test_serialization_is_deterministic(self) -> None:
        self.assertEqual(
            serialize_experiment_document(self.experiment),
            serialize_experiment_document(self.experiment),
        )

    def test_document_records_schema_version_and_digest(self) -> None:
        document = json.loads(serialize_experiment_document(self.experiment))
        self.assertEqual(document["schema"], EXPERIMENT_DOCUMENT_SCHEMA)
        self.assertEqual(document["version"], EXPERIMENT_DOCUMENT_VERSION)
        self.assertRegex(document["payload_sha256"], r"^[0-9a-f]{64}$")

    def test_tampered_payload_is_rejected(self) -> None:
        document = json.loads(serialize_experiment_document(self.experiment))
        document["payload"]["experiment"]["duration_min"] = 999.0
        with self.assertRaisesRegex(ValueError, "digest"):
            deserialize_experiment_document(json.dumps(document))

    def test_unknown_version_is_rejected(self) -> None:
        document = json.loads(serialize_experiment_document(self.experiment))
        document["version"] = 999
        with self.assertRaisesRegex(ValueError, "version"):
            deserialize_experiment_document(json.dumps(document))

    def test_unexpected_top_level_field_is_rejected(self) -> None:
        document = json.loads(serialize_experiment_document(self.experiment))
        document["future"] = True
        with self.assertRaisesRegex(ValueError, "top-level"):
            deserialize_experiment_document(json.dumps(document))

    def test_filesystem_round_trip_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiment.json"
            returned = write_experiment_document(path, self.experiment)
            self.assertEqual(returned, path)
            self.assertEqual(read_experiment_document(path), self.experiment)
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                serialize_experiment_document(self.experiment),
            )


if __name__ == "__main__":
    unittest.main()
