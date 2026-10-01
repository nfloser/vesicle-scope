from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from vesiclescope.domain import (
    EvidenceCategory,
    EvidenceSource,
    ParameterContext,
    ScientificParameter,
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
from vesiclescope.run_bundles import (
    RUN_BUNDLE_SCHEMA,
    RUN_BUNDLE_VERSION,
    SimulationRunBundle,
    deserialize_run_bundle,
    read_run_bundle,
    serialize_run_bundle,
    write_run_bundle,
)
from vesiclescope.scenarios import (
    finite_donor_boundary_figure_experiment,
    finite_recipient_count_sweep_experiment,
)


REVISION = "a" * 40


def result_for(experiment, *, grid_spacing_micron: float) -> BioFVMRunResult:
    nx = round(experiment.domain.width_micron / grid_spacing_micron)
    ny = round(experiment.domain.height_micron / grid_spacing_micron)
    values = tuple(
        0.001 + index / 1_000_000.0
        for index in range(nx * ny)
    )
    voxel_volume = (
        grid_spacing_micron
        * grid_spacing_micron
        * experiment.domain.slice_thickness_micron
    )
    integrated = sum(values) * voxel_volume
    uptake_total = float(len(experiment.uptake_sinks))
    series = tuple(
        RecipientUptakeSeries(
            identifier=sink.identifier,
            x_micron=sink.x_micron,
            y_micron=sink.y_micron,
            effective_volume_micron3=sink.effective_volume_micron3,
            uptake_rate_per_min=sink.uptake_rate.value,
            samples=(
                RecipientUptakeSample(
                    time_min=experiment.duration_min,
                    internalized_field_quantity=1.0,
                ),
            ),
        )
        for sink in experiment.uptake_sinks
    )
    return BioFVMRunResult(
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
        grid=BioFVMGrid2D(
            nx=nx,
            ny=ny,
            grid_spacing_micron=grid_spacing_micron,
            slice_thickness_micron=experiment.domain.slice_thickness_micron,
        ),
        samples=(
            TransportSample(
                time_min=experiment.duration_min,
                mean_concentration=sum(values) / len(values),
                min_concentration=min(values),
                max_concentration=max(values),
                integrated_field_quantity=integrated,
                internalized_field_quantity=uptake_total,
            ),
        ),
        field_snapshots=(
            SpatialFieldSnapshot2D(
                time_min=experiment.duration_min,
                values=values,
            ),
        ),
        recipient_uptake_series=series,
    )


def donor_bundle() -> SimulationRunBundle:
    experiment = finite_donor_boundary_figure_experiment()
    numerics = BioFVMNumerics(
        grid_spacing_micron=20.0,
        time_step_min=0.1,
    )
    return SimulationRunBundle(
        vesiclescope_revision=REVISION,
        experiment=experiment,
        numerics=numerics,
        result=result_for(experiment, grid_spacing_micron=20.0),
    )


def canonical_payload_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class SimulationRunBundleTests(unittest.TestCase):
    def test_serialization_is_deterministic_for_identical_inputs(self) -> None:
        bundle = donor_bundle()

        first = serialize_run_bundle(bundle)
        second = serialize_run_bundle(bundle)

        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))
        document = json.loads(first)
        self.assertEqual(document["schema"], RUN_BUNDLE_SCHEMA)
        self.assertEqual(document["version"], RUN_BUNDLE_VERSION)
        self.assertEqual(
            document["payload_sha256"],
            canonical_payload_digest(document["payload"]),
        )

    def test_round_trips_finite_donor_experiment_numerics_and_result_exactly(self) -> None:
        expected = donor_bundle()

        observed = deserialize_run_bundle(serialize_run_bundle(expected))

        self.assertEqual(observed, expected)
        self.assertEqual(
            observed.result.grid.ordering,
            "x_fastest_then_y",
        )
        self.assertEqual(
            observed.result.field_snapshots,
            expected.result.field_snapshots,
        )

    def test_round_trips_finite_recipient_uptake_series_exactly(self) -> None:
        experiment = finite_recipient_count_sweep_experiment(2)
        numerics = BioFVMNumerics(
            grid_spacing_micron=10.0,
            time_step_min=0.1,
        )
        expected = SimulationRunBundle(
            vesiclescope_revision=REVISION,
            experiment=experiment,
            numerics=numerics,
            result=result_for(experiment, grid_spacing_micron=10.0),
        )

        observed = deserialize_run_bundle(serialize_run_bundle(expected))

        self.assertEqual(observed, expected)
        self.assertEqual(
            tuple(item.identifier for item in observed.result.recipient_uptake_series),
            tuple(sink.identifier for sink in experiment.uptake_sinks),
        )

    def test_parameter_source_context_assumptions_and_limitations_survive(self) -> None:
        experiment = finite_donor_boundary_figure_experiment()
        evidence_parameter = ScientificParameter(
            identifier="transport.diffusion.evidence-test",
            scientific_name="Evidence round-trip diffusion",
            value=42.0,
            unit="micron^2/min",
            evidence=EvidenceCategory.LITERATURE_ESTIMATE,
            source=EvidenceSource(
                identifier="doi:10.0000/example",
                location="Table 2",
            ),
            context=ParameterContext(
                species="human",
                tissue="synthetic documentation context",
                cell_line="example line",
                ev_preparation="operational EV fraction",
                measurement_method="example method",
                experimental_conditions="example conditions",
            ),
            assumptions=("round-trip assumption",),
            limitations=("not a VesicleScope biological default",),
        )
        experiment = replace(experiment, diffusion=evidence_parameter)
        bundle = SimulationRunBundle(
            vesiclescope_revision=REVISION,
            experiment=experiment,
            numerics=BioFVMNumerics(20.0, 0.1),
            result=result_for(experiment, grid_spacing_micron=20.0),
        )

        observed = deserialize_run_bundle(serialize_run_bundle(bundle))

        self.assertEqual(observed.experiment.diffusion, evidence_parameter)

    def test_detects_payload_tampering_before_reconstruction(self) -> None:
        document = json.loads(serialize_run_bundle(donor_bundle()))
        document["payload"]["experiment"]["experiment_id"] = "tampered"
        tampered = (
            json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        ).encode("utf-8")

        with self.assertRaisesRegex(ValueError, "digest"):
            deserialize_run_bundle(tampered)

    def test_rejects_unknown_schema_version(self) -> None:
        document = json.loads(serialize_run_bundle(donor_bundle()))
        document["version"] = RUN_BUNDLE_VERSION + 1
        encoded = (
            json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        ).encode("utf-8")

        with self.assertRaisesRegex(ValueError, "version"):
            deserialize_run_bundle(encoded)

    def test_rejects_unsupported_source_geometry_even_with_valid_digest(self) -> None:
        document = json.loads(serialize_run_bundle(donor_bundle()))
        document["payload"]["experiment"]["release_sources"][0]["kind"] = "triangle"
        document["payload_sha256"] = canonical_payload_digest(document["payload"])
        encoded = (
            json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        ).encode("utf-8")

        with self.assertRaisesRegex(ValueError, "release source"):
            deserialize_run_bundle(encoded)

    def test_rejects_missing_required_result_collection(self) -> None:
        document = json.loads(serialize_run_bundle(donor_bundle()))
        del document["payload"]["result"]["field_snapshots"]
        document["payload_sha256"] = canonical_payload_digest(document["payload"])
        encoded = (
            json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        ).encode("utf-8")

        with self.assertRaisesRegex(ValueError, "missing required field"):
            deserialize_run_bundle(encoded)

    def test_rejects_blank_or_non_commit_revision(self) -> None:
        with self.assertRaisesRegex(ValueError, "commit SHA"):
            replace(donor_bundle(), vesiclescope_revision="main")

    def test_write_is_round_trippable_without_timestamp_or_absolute_path(self) -> None:
        bundle = donor_bundle()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            write_run_bundle(path, bundle)
            data = path.read_bytes()

            self.assertEqual(read_run_bundle(path), bundle)
            self.assertNotIn(str(Path(directory)).encode("utf-8"), data)
            self.assertNotIn(b"created_at", data)
            self.assertNotIn(b"timestamp", data)


if __name__ == "__main__":
    unittest.main()
