import json
from pathlib import Path
import tempfile
import unittest

from vesiclescope.batch_manifests import (
    BATCH_SCIENTIFIC_STATUS,
    ExperimentBatchManifest,
    ExperimentBatchManifestMember,
    deserialize_batch_manifest,
    read_batch_manifest,
    serialize_batch_manifest,
    write_batch_manifest,
)
from vesiclescope.engines import BioFVMNumerics


def manifest() -> ExperimentBatchManifest:
    return ExperimentBatchManifest(
        vesiclescope_revision="a" * 40,
        numerics=BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
        members=(
            ExperimentBatchManifestMember(
                index=1,
                input_filename="left.json",
                experiment_id="experiment.left",
                run_filename="001-left.run.json",
                run_bundle_payload_sha256="1" * 64,
            ),
            ExperimentBatchManifestMember(
                index=2,
                input_filename="right.json",
                experiment_id="experiment.right",
                run_filename="002-right.run.json",
                run_bundle_payload_sha256="2" * 64,
            ),
        ),
    )


class BatchManifestTests(unittest.TestCase):
    def test_round_trip_is_deterministic_and_preserves_order(self) -> None:
        source = manifest()
        first = serialize_batch_manifest(source)
        second = serialize_batch_manifest(source)
        self.assertEqual(first, second)
        self.assertEqual(deserialize_batch_manifest(first), source)
        payload = json.loads(first)
        self.assertEqual(payload["scientific_status"], BATCH_SCIENTIFIC_STATUS)
        self.assertEqual(
            [item["experiment_id"] for item in payload["members"]],
            ["experiment.left", "experiment.right"],
        )

    def test_rejects_non_contiguous_indices(self) -> None:
        source = manifest()
        with self.assertRaisesRegex(ValueError, "contiguous"):
            ExperimentBatchManifest(
                vesiclescope_revision=source.vesiclescope_revision,
                numerics=source.numerics,
                members=(
                    source.members[0],
                    ExperimentBatchManifestMember(
                        index=3,
                        input_filename="right.json",
                        experiment_id="experiment.right",
                        run_filename="002-right.run.json",
                        run_bundle_payload_sha256="2" * 64,
                    ),
                ),
            )

    def test_rejects_duplicate_experiment_ids_and_run_names(self) -> None:
        first = manifest().members[0]
        with self.assertRaisesRegex(ValueError, "duplicate experiment_id"):
            ExperimentBatchManifest(
                vesiclescope_revision="a" * 40,
                numerics=BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
                members=(
                    first,
                    ExperimentBatchManifestMember(
                        index=2,
                        input_filename="other.json",
                        experiment_id=first.experiment_id,
                        run_filename="other.run.json",
                        run_bundle_payload_sha256="2" * 64,
                    ),
                ),
            )
        with self.assertRaisesRegex(ValueError, "duplicate run filenames"):
            ExperimentBatchManifest(
                vesiclescope_revision="a" * 40,
                numerics=BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
                members=(
                    first,
                    ExperimentBatchManifestMember(
                        index=2,
                        input_filename="other.json",
                        experiment_id="experiment.other",
                        run_filename=first.run_filename,
                        run_bundle_payload_sha256="2" * 64,
                    ),
                ),
            )

    def test_rejects_invalid_digest_and_path_like_filename(self) -> None:
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            ExperimentBatchManifestMember(
                index=1,
                input_filename="left.json",
                experiment_id="experiment.left",
                run_filename="left.run.json",
                run_bundle_payload_sha256="BAD",
            )
        with self.assertRaisesRegex(ValueError, "plain filename"):
            ExperimentBatchManifestMember(
                index=1,
                input_filename="../left.json",
                experiment_id="experiment.left",
                run_filename="left.run.json",
                run_bundle_payload_sha256="1" * 64,
            )

    def test_rejects_tampered_status_and_version(self) -> None:
        payload = json.loads(serialize_batch_manifest(manifest()))
        payload["scientific_status"] = "random sample"
        with self.assertRaisesRegex(ValueError, "scientific_status"):
            deserialize_batch_manifest(json.dumps(payload))
        payload = json.loads(serialize_batch_manifest(manifest()))
        payload["version"] = 99
        with self.assertRaisesRegex(ValueError, "version"):
            deserialize_batch_manifest(json.dumps(payload))

    def test_file_round_trip_uses_same_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "batch-manifest.json"
            write_batch_manifest(path, manifest())
            self.assertEqual(read_batch_manifest(path), manifest())


if __name__ == "__main__":
    unittest.main()
