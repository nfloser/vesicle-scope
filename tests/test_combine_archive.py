from io import BytesIO
import json
import unittest
import zipfile

from vesiclescope.combine_archive import (
    EXPERIMENT_NAME,
    MANIFEST_NAME,
    OMEX_MANIFEST_NAMESPACE,
    OMEX_NAMESPACE,
    deserialize_combine_archive,
    serialize_combine_archive,
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
from vesiclescope.run_bundles import SimulationRunBundle
from vesiclescope.scenarios import diffusion_uptake_factor_conditions


REVISION = "a" * 40


def baseline_experiment():
    return diffusion_uptake_factor_conditions()[4].experiment


def bundle_for(experiment=None) -> SimulationRunBundle:
    experiment = experiment or baseline_experiment()
    grid_spacing = 10.0
    nx = round(experiment.domain.width_micron / grid_spacing)
    ny = round(experiment.domain.height_micron / grid_spacing)
    grid = BioFVMGrid2D(
        nx=nx,
        ny=ny,
        grid_spacing_micron=grid_spacing,
        slice_thickness_micron=experiment.domain.slice_thickness_micron,
    )
    concentration = 0.001
    voxel_volume = (
        grid_spacing * grid_spacing * experiment.domain.slice_thickness_micron
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
        numerics=BioFVMNumerics(grid_spacing_micron=grid_spacing, time_step_min=0.1),
        result=result,
    )


def rewrite_archive(data: bytes, transform) -> bytes:
    source = zipfile.ZipFile(BytesIO(data), "r")
    output = BytesIO()
    with source, zipfile.ZipFile(output, "w") as target:
        for info in source.infolist():
            name, payload = transform(info.filename, source.read(info.filename))
            target.writestr(name, payload)
    return output.getvalue()


class CombineArchiveTests(unittest.TestCase):
    def test_serialization_is_byte_deterministic(self) -> None:
        experiment = baseline_experiment()
        bundle = bundle_for(experiment)
        self.assertEqual(
            serialize_combine_archive(experiment, (bundle, bundle)),
            serialize_combine_archive(experiment, (bundle, bundle)),
        )

    def test_manifest_declares_archive_manifest_experiment_readme_and_runs(self) -> None:
        data = serialize_combine_archive(
            baseline_experiment(),
            (bundle_for(),),
        )
        with zipfile.ZipFile(BytesIO(data), "r") as archive:
            manifest = archive.read(MANIFEST_NAME).decode("utf-8")
            self.assertIn(f'location="." format="{OMEX_NAMESPACE}"', manifest)
            self.assertIn(
                f'location="./manifest.xml" format="{OMEX_MANIFEST_NAMESPACE}"',
                manifest,
            )
            self.assertIn(
                'location="./experiment.json" '
                'format="http://purl.org/NET/mediatypes/application/json" '
                'master="true"',
                manifest,
            )
            self.assertIn('location="./runs/run-001.json"', manifest)

    def test_round_trip_preserves_experiment_and_multiple_runs(self) -> None:
        experiment = baseline_experiment()
        bundle = bundle_for(experiment)
        project = deserialize_combine_archive(
            serialize_combine_archive(experiment, (bundle, bundle))
        )
        self.assertEqual(project.experiment, experiment)
        self.assertEqual(project.runs, (bundle, bundle))

    def test_archive_without_runs_is_valid(self) -> None:
        experiment = baseline_experiment()
        project = deserialize_combine_archive(serialize_combine_archive(experiment))
        self.assertEqual(project.experiment, experiment)
        self.assertEqual(project.runs, ())

    def test_rejects_run_from_a_different_experiment_on_write(self) -> None:
        experiment = baseline_experiment()
        other = diffusion_uptake_factor_conditions()[0].experiment
        with self.assertRaisesRegex(ValueError, "exact archived experiment"):
            serialize_combine_archive(experiment, (bundle_for(other),))

    def test_tampered_run_bundle_is_rejected_on_read(self) -> None:
        original = serialize_combine_archive(
            baseline_experiment(),
            (bundle_for(),),
        )

        def tamper(name: str, payload: bytes):
            if name == "runs/run-001.json":
                document = json.loads(payload)
                document["payload"]["vesiclescope_revision"] = "b" * 40
                payload = (json.dumps(document, sort_keys=True, indent=2) + "\n").encode()
            return name, payload

        with self.assertRaisesRegex(ValueError, "digest"):
            deserialize_combine_archive(rewrite_archive(original, tamper))

    def test_rejects_path_traversal_member(self) -> None:
        data = serialize_combine_archive(baseline_experiment())
        output = BytesIO()
        with zipfile.ZipFile(BytesIO(data), "r") as source, zipfile.ZipFile(
            output, "w"
        ) as target:
            for info in source.infolist():
                target.writestr(info.filename, source.read(info.filename))
            target.writestr("../escape.txt", b"no")

        with self.assertRaisesRegex(ValueError, "unsafe member path"):
            deserialize_combine_archive(output.getvalue())

    def test_rejects_duplicate_member_names(self) -> None:
        data = serialize_combine_archive(baseline_experiment())
        output = BytesIO()
        with zipfile.ZipFile(BytesIO(data), "r") as source, zipfile.ZipFile(
            output, "w"
        ) as target:
            for info in source.infolist():
                target.writestr(info.filename, source.read(info.filename))
            target.writestr(EXPERIMENT_NAME, source.read(EXPERIMENT_NAME))

        with self.assertRaisesRegex(ValueError, "duplicate member"):
            deserialize_combine_archive(output.getvalue())


if __name__ == "__main__":
    unittest.main()
