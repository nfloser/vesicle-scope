from io import BytesIO
import json
import unittest
import zipfile

from vesiclescope.batch_manifests import (
    ExperimentBatchManifest,
    ExperimentBatchManifestMember,
)
from vesiclescope.combine_archive import (
    BATCH_MANIFEST_NAME,
    MANIFEST_NAME,
    combine_archive_project_type,
    deserialize_batch_combine_archive,
    serialize_batch_combine_archive,
)
from vesiclescope.engines import (
    BioFVMEngineMetadata,
    BioFVMGrid2D,
    BioFVMNumerics,
    BioFVMRunResult,
    RecipientUptakeSample,
    RecipientUptakeSeries,
    SpatialFieldSnapshot2D,
    TransportSample,
)
from vesiclescope.run_bundles import SimulationRunBundle, run_bundle_payload_sha256
from vesiclescope.scenarios import diffusion_uptake_factor_conditions


REVISION = "a" * 40
NUMERICS = BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1)


def bundle_for(
    experiment,
    numerics: BioFVMNumerics = NUMERICS,
) -> SimulationRunBundle:
    grid = BioFVMGrid2D(
        nx=round(experiment.domain.width_micron / numerics.grid_spacing_micron),
        ny=round(experiment.domain.height_micron / numerics.grid_spacing_micron),
        grid_spacing_micron=numerics.grid_spacing_micron,
        slice_thickness_micron=experiment.domain.slice_thickness_micron,
    )
    concentration = 0.001
    voxel_volume = (
        grid.grid_spacing_micron
        * grid.grid_spacing_micron
        * grid.slice_thickness_micron
    )
    integrated = concentration * grid.voxel_count * voxel_volume
    result = BioFVMRunResult(
        experiment_id=experiment.experiment_id,
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
                time_min=experiment.duration_min,
                mean_concentration=concentration,
                min_concentration=concentration,
                max_concentration=concentration,
                integrated_field_quantity=integrated,
                internalized_field_quantity=0.0,
            ),
        ),
        field_snapshots=(
            SpatialFieldSnapshot2D(
                time_min=experiment.duration_min,
                values=(concentration,) * grid.voxel_count,
            ),
        ),
        recipient_uptake_series=tuple(
            RecipientUptakeSeries(
                identifier=sink.identifier,
                x_micron=sink.x_micron,
                y_micron=sink.y_micron,
                effective_volume_micron3=sink.effective_volume_micron3,
                uptake_rate_per_min=sink.uptake_rate.value,
                samples=(
                    RecipientUptakeSample(
                        time_min=experiment.duration_min,
                        internalized_field_quantity=0.0,
                    ),
                ),
            )
            for sink in experiment.uptake_sinks
        ),
    )
    return SimulationRunBundle(
        vesiclescope_revision=REVISION,
        experiment=experiment,
        numerics=numerics,
        result=result,
    )


def batch_fixture():
    conditions = diffusion_uptake_factor_conditions()
    runs = (
        bundle_for(conditions[0].experiment),
        bundle_for(conditions[1].experiment),
    )
    manifest = ExperimentBatchManifest(
        vesiclescope_revision=REVISION,
        numerics=NUMERICS,
        members=tuple(
            ExperimentBatchManifestMember(
                index=index,
                input_filename=f"input-{index:03d}.json",
                experiment_id=bundle.experiment.experiment_id,
                run_filename=f"member-{index:03d}.run.json",
                run_bundle_payload_sha256=run_bundle_payload_sha256(bundle),
            )
            for index, bundle in enumerate(runs, start=1)
        ),
    )
    return manifest, runs


def rewrite_archive(data: bytes, transform) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(BytesIO(data), "r") as source, zipfile.ZipFile(
        output, "w"
    ) as target:
        for info in source.infolist():
            changed = transform(info.filename, source.read(info.filename))
            if changed is None:
                continue
            name, payload = changed
            target.writestr(name, payload)
    return output.getvalue()


class CombineBatchArchiveTests(unittest.TestCase):
    def test_batch_archive_is_deterministic_and_preserves_member_order(self) -> None:
        manifest, runs = batch_fixture()
        first = serialize_batch_combine_archive(manifest, runs)
        second = serialize_batch_combine_archive(manifest, runs)
        self.assertEqual(first, second)
        self.assertEqual(combine_archive_project_type(first), "batch")

        project = deserialize_batch_combine_archive(first)
        self.assertEqual(project.manifest, manifest)
        self.assertEqual(project.runs, runs)
        self.assertEqual(
            tuple(experiment.experiment_id for experiment in project.experiments),
            tuple(member.experiment_id for member in manifest.members),
        )

    def test_manifest_uses_batch_manifest_as_master_resource(self) -> None:
        manifest, runs = batch_fixture()
        data = serialize_batch_combine_archive(manifest, runs)
        with zipfile.ZipFile(BytesIO(data), "r") as archive:
            text = archive.read(MANIFEST_NAME).decode("utf-8")
            self.assertIn(
                'location="./batch-manifest.json" '
                'format="http://purl.org/NET/mediatypes/application/json" '
                'master="true"',
                text,
            )
            self.assertIn('location="./experiments/member-001.json"', text)
            self.assertIn('location="./runs/member-002.run.json"', text)

    def test_rejects_manifest_digest_mismatch(self) -> None:
        manifest, runs = batch_fixture()
        data = serialize_batch_combine_archive(manifest, runs)

        def tamper(name: str, payload: bytes):
            if name == BATCH_MANIFEST_NAME:
                document = json.loads(payload)
                document["members"][0]["run_bundle_payload_sha256"] = "0" * 64
                payload = (
                    json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
                    + "\n"
                ).encode("utf-8")
            return name, payload

        with self.assertRaisesRegex(ValueError, "payload digest"):
            deserialize_batch_combine_archive(rewrite_archive(data, tamper))

    def test_rejects_missing_experiment_member(self) -> None:
        manifest, runs = batch_fixture()
        data = serialize_batch_combine_archive(manifest, runs)

        def remove(name: str, payload: bytes):
            if name == "experiments/member-002.json":
                return None
            return name, payload

        with self.assertRaisesRegex(ValueError, "missing member"):
            deserialize_batch_combine_archive(rewrite_archive(data, remove))

    def test_rejects_run_with_wrong_experiment_before_serialization(self) -> None:
        manifest, runs = batch_fixture()
        with self.assertRaisesRegex(ValueError, "experiment_id"):
            serialize_batch_combine_archive(manifest, (runs[1], runs[0]))

    def test_rejects_run_revision_or_numerics_mismatch(self) -> None:
        from dataclasses import replace

        manifest, runs = batch_fixture()
        with self.assertRaisesRegex(ValueError, "revision"):
            serialize_batch_combine_archive(
                manifest,
                (replace(runs[0], vesiclescope_revision="b" * 40), runs[1]),
            )
        altered_numerics = BioFVMNumerics(
            grid_spacing_micron=5.0,
            time_step_min=0.1,
        )
        altered_run = bundle_for(runs[0].experiment, altered_numerics)
        with self.assertRaisesRegex(ValueError, "numerics"):
            serialize_batch_combine_archive(
                manifest,
                (altered_run, runs[1]),
            )


if __name__ == "__main__":
    unittest.main()
