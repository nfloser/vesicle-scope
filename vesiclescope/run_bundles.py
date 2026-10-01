"""Deterministic durable bundles for normalized VesicleScope simulation runs.

The v0.1 format is intentionally VesicleScope-native. It follows MIASE-style
reproducibility requirements without claiming SED-ML, OMEX or MultiCellDS
compatibility that the current spatial BioFVM model cannot yet provide.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from vesiclescope.domain import (
    BoundaryCondition,
    CircularReleaseSource,
    CircularUptakeSink,
    EvidenceCategory,
    EvidenceSource,
    ParameterContext,
    PointReleaseSource,
    PointUptakeSink,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
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


RUN_BUNDLE_SCHEMA = "vesiclescope.simulation-run"
RUN_BUNDLE_VERSION = 1
_SHA_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


def _revision(value: str) -> str:
    revision = _required_text(value, "vesiclescope_revision")
    if _SHA_RE.fullmatch(revision) is None:
        raise ValueError(
            "vesiclescope_revision must be a 40- or 64-character hexadecimal commit SHA"
        )
    return revision.lower()


def _same_float(left: float, right: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-9)


@dataclass(frozen=True, slots=True)
class SimulationRunBundle:
    """One immutable reproducible transport run."""

    vesiclescope_revision: str
    experiment: TransportExperiment
    numerics: BioFVMNumerics
    result: BioFVMRunResult

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "vesiclescope_revision",
            _revision(self.vesiclescope_revision),
        )
        if not isinstance(self.experiment, TransportExperiment):
            raise TypeError("experiment must be a TransportExperiment")
        if not isinstance(self.numerics, BioFVMNumerics):
            raise TypeError("numerics must be BioFVMNumerics")
        if not isinstance(self.result, BioFVMRunResult):
            raise TypeError("result must be a BioFVMRunResult")

        _validate_run_contracts(self.experiment, self.numerics, self.result)


def _validate_run_contracts(
    experiment: TransportExperiment,
    numerics: BioFVMNumerics,
    result: BioFVMRunResult,
) -> None:
    if result.experiment_id != experiment.experiment_id:
        raise ValueError("result experiment_id does not match experiment")

    for value, field_name in (
        (result.concentration_unit, "concentration_unit"),
        (result.integrated_quantity_unit, "integrated_quantity_unit"),
        (result.internalized_quantity_unit, "internalized_quantity_unit"),
    ):
        _required_text(value, field_name)

    engine = result.engine
    if not isinstance(engine, BioFVMEngineMetadata):
        raise TypeError("result engine must be BioFVMEngineMetadata")
    for value, field_name in (
        (engine.engine, "engine"),
        (engine.physicell_release, "physicell_release"),
        (engine.physicell_commit, "physicell_commit"),
        (engine.biofvm_version, "biofvm_version"),
    ):
        _required_text(value, field_name)

    grid = result.grid
    if not isinstance(grid, BioFVMGrid2D):
        raise TypeError("result grid must be BioFVMGrid2D")
    if not _same_float(grid.grid_spacing_micron, numerics.grid_spacing_micron):
        raise ValueError("result grid spacing does not match BioFVM numerics")
    if not _same_float(
        grid.slice_thickness_micron,
        experiment.domain.slice_thickness_micron,
    ):
        raise ValueError("result slice thickness does not match experiment domain")
    if not _same_float(
        grid.nx * grid.grid_spacing_micron,
        experiment.domain.width_micron,
    ):
        raise ValueError("result grid width does not match experiment domain")
    if not _same_float(
        grid.ny * grid.grid_spacing_micron,
        experiment.domain.height_micron,
    ):
        raise ValueError("result grid height does not match experiment domain")

    if not isinstance(result.samples, tuple) or not all(
        isinstance(item, TransportSample) for item in result.samples
    ):
        raise TypeError("result samples must contain TransportSample objects")
    if not isinstance(result.field_snapshots, tuple) or not all(
        isinstance(item, SpatialFieldSnapshot2D)
        for item in result.field_snapshots
    ):
        raise TypeError(
            "result field_snapshots must contain SpatialFieldSnapshot2D objects"
        )
    if not result.samples:
        raise ValueError("result must contain at least one transport sample")
    if not result.field_snapshots:
        raise ValueError("result must contain at least one field snapshot")

    sample_times = tuple(item.time_min for item in result.samples)
    if len(set(sample_times)) != len(sample_times):
        raise ValueError("result sample times must be unique")
    for snapshot in result.field_snapshots:
        if len(snapshot.values) != grid.voxel_count:
            raise ValueError(
                "result field snapshot length does not match normalized grid"
            )
        if not any(_same_float(snapshot.time_min, time) for time in sample_times):
            raise ValueError(
                "every field snapshot must correspond to a normalized sample time"
            )

    if not isinstance(result.recipient_uptake_series, tuple) or not all(
        isinstance(item, RecipientUptakeSeries)
        for item in result.recipient_uptake_series
    ):
        raise TypeError(
            "result recipient_uptake_series must contain RecipientUptakeSeries objects"
        )
    expected_recipient_ids = tuple(sink.identifier for sink in experiment.uptake_sinks)
    observed_recipient_ids = tuple(
        item.identifier for item in result.recipient_uptake_series
    )
    if observed_recipient_ids != expected_recipient_ids:
        raise ValueError(
            "result recipient uptake series must match configured uptake sinks"
        )


def _encode_source(source: EvidenceSource | None) -> dict[str, Any] | None:
    if source is None:
        return None
    return {
        "identifier": source.identifier,
        "location": source.location,
    }


def _decode_source(value: Any) -> EvidenceSource | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("parameter evidence source must be an object or null")
    return EvidenceSource(
        identifier=value["identifier"],
        location=value.get("location"),
    )


def _encode_context(context: ParameterContext | None) -> dict[str, Any] | None:
    if context is None:
        return None
    return {
        "species": context.species,
        "tissue": context.tissue,
        "cell_type": context.cell_type,
        "cell_line": context.cell_line,
        "ev_preparation": context.ev_preparation,
        "measurement_method": context.measurement_method,
        "experimental_conditions": context.experimental_conditions,
    }


def _decode_context(value: Any) -> ParameterContext | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("parameter context must be an object or null")
    return ParameterContext(
        species=value.get("species"),
        tissue=value.get("tissue"),
        cell_type=value.get("cell_type"),
        cell_line=value.get("cell_line"),
        ev_preparation=value.get("ev_preparation"),
        measurement_method=value.get("measurement_method"),
        experimental_conditions=value.get("experimental_conditions"),
    )


def _encode_parameter(parameter: ScientificParameter) -> dict[str, Any]:
    if not isinstance(parameter, ScientificParameter):
        raise TypeError("scientific parameter must be a ScientificParameter")
    return {
        "identifier": parameter.identifier,
        "scientific_name": parameter.scientific_name,
        "value": parameter.value,
        "unit": parameter.unit,
        "evidence": parameter.evidence.value,
        "source": _encode_source(parameter.source),
        "context": _encode_context(parameter.context),
        "assumptions": list(parameter.assumptions),
        "limitations": list(parameter.limitations),
    }


def _decode_parameter(value: Any) -> ScientificParameter:
    if not isinstance(value, dict):
        raise ValueError("scientific parameter must be an object")
    try:
        evidence = EvidenceCategory(value["evidence"])
    except (KeyError, ValueError) as exc:
        raise ValueError("scientific parameter has an invalid evidence category") from exc
    return ScientificParameter(
        identifier=value["identifier"],
        scientific_name=value["scientific_name"],
        value=value["value"],
        unit=value["unit"],
        evidence=evidence,
        source=_decode_source(value.get("source")),
        context=_decode_context(value.get("context")),
        assumptions=tuple(value["assumptions"]),
        limitations=tuple(value["limitations"]),
    )


def _encode_release_source(source: Any) -> dict[str, Any]:
    common = {
        "identifier": source.identifier,
        "x_micron": source.x_micron,
        "y_micron": source.y_micron,
        "release_rate": _encode_parameter(source.release_rate),
    }
    if isinstance(source, PointReleaseSource):
        return {"kind": "point", **common}
    if isinstance(source, CircularReleaseSource):
        return {
            "kind": "circle",
            **common,
            "footprint_radius_micron": source.footprint_radius_micron,
        }
    raise TypeError("unsupported release source object")


def _decode_release_source(value: Any):
    if not isinstance(value, dict):
        raise ValueError("release source must be an object")
    kind = value.get("kind")
    common = {
        "identifier": value["identifier"],
        "x_micron": value["x_micron"],
        "y_micron": value["y_micron"],
        "release_rate": _decode_parameter(value["release_rate"]),
    }
    if kind == "point":
        return PointReleaseSource(**common)
    if kind == "circle":
        return CircularReleaseSource(
            **common,
            footprint_radius_micron=value["footprint_radius_micron"],
        )
    raise ValueError(f"unsupported release source geometry: {kind!r}")


def _encode_uptake_sink(sink: Any) -> dict[str, Any]:
    common = {
        "identifier": sink.identifier,
        "x_micron": sink.x_micron,
        "y_micron": sink.y_micron,
        "effective_volume_micron3": sink.effective_volume_micron3,
        "uptake_rate": _encode_parameter(sink.uptake_rate),
    }
    if isinstance(sink, PointUptakeSink):
        return {"kind": "point", **common}
    if isinstance(sink, CircularUptakeSink):
        return {
            "kind": "circle",
            **common,
            "footprint_radius_micron": sink.footprint_radius_micron,
        }
    raise TypeError("unsupported uptake sink object")


def _decode_uptake_sink(value: Any):
    if not isinstance(value, dict):
        raise ValueError("uptake sink must be an object")
    kind = value.get("kind")
    common = {
        "identifier": value["identifier"],
        "x_micron": value["x_micron"],
        "y_micron": value["y_micron"],
        "effective_volume_micron3": value["effective_volume_micron3"],
        "uptake_rate": _decode_parameter(value["uptake_rate"]),
    }
    if kind == "point":
        return PointUptakeSink(**common)
    if kind == "circle":
        return CircularUptakeSink(
            **common,
            footprint_radius_micron=value["footprint_radius_micron"],
        )
    raise ValueError(f"unsupported uptake sink geometry: {kind!r}")


def _encode_experiment(experiment: TransportExperiment) -> dict[str, Any]:
    return {
        "experiment_id": experiment.experiment_id,
        "domain": {
            "width_micron": experiment.domain.width_micron,
            "height_micron": experiment.domain.height_micron,
            "slice_thickness_micron": experiment.domain.slice_thickness_micron,
        },
        "duration_min": experiment.duration_min,
        "sample_every_min": experiment.sample_every_min,
        "boundary": experiment.boundary.value,
        "diffusion": _encode_parameter(experiment.diffusion),
        "decay": _encode_parameter(experiment.decay),
        "initial_concentration": _encode_parameter(
            experiment.initial_concentration
        ),
        "release_sources": [
            _encode_release_source(source)
            for source in experiment.release_sources
        ],
        "uptake_sinks": [
            _encode_uptake_sink(sink)
            for sink in experiment.uptake_sinks
        ],
    }


def _decode_experiment(value: Any) -> TransportExperiment:
    if not isinstance(value, dict):
        raise ValueError("experiment must be an object")
    domain = value["domain"]
    if not isinstance(domain, dict):
        raise ValueError("experiment domain must be an object")
    try:
        boundary = BoundaryCondition(value["boundary"])
    except ValueError as exc:
        raise ValueError("experiment has an unsupported boundary condition") from exc
    return TransportExperiment(
        experiment_id=value["experiment_id"],
        domain=RectangularDomain2D(
            width_micron=domain["width_micron"],
            height_micron=domain["height_micron"],
            slice_thickness_micron=domain["slice_thickness_micron"],
        ),
        duration_min=value["duration_min"],
        sample_every_min=value["sample_every_min"],
        boundary=boundary,
        diffusion=_decode_parameter(value["diffusion"]),
        decay=_decode_parameter(value["decay"]),
        initial_concentration=_decode_parameter(value["initial_concentration"]),
        release_sources=tuple(
            _decode_release_source(item)
            for item in value["release_sources"]
        ),
        uptake_sinks=tuple(
            _decode_uptake_sink(item)
            for item in value["uptake_sinks"]
        ),
    )


def _encode_numerics(numerics: BioFVMNumerics) -> dict[str, Any]:
    return {
        "grid_spacing_micron": numerics.grid_spacing_micron,
        "time_step_min": numerics.time_step_min,
    }


def _decode_numerics(value: Any) -> BioFVMNumerics:
    if not isinstance(value, dict):
        raise ValueError("numerics must be an object")
    return BioFVMNumerics(
        grid_spacing_micron=value["grid_spacing_micron"],
        time_step_min=value["time_step_min"],
    )


def _encode_result(result: BioFVMRunResult) -> dict[str, Any]:
    return {
        "experiment_id": result.experiment_id,
        "units": {
            "concentration": result.concentration_unit,
            "integrated_quantity": result.integrated_quantity_unit,
            "internalized_quantity": result.internalized_quantity_unit,
        },
        "engine": {
            "engine": result.engine.engine,
            "physicell_release": result.engine.physicell_release,
            "physicell_commit": result.engine.physicell_commit,
            "biofvm_version": result.engine.biofvm_version,
        },
        "grid": {
            "nx": result.grid.nx,
            "ny": result.grid.ny,
            "grid_spacing_micron": result.grid.grid_spacing_micron,
            "slice_thickness_micron": result.grid.slice_thickness_micron,
            "ordering": result.grid.ordering,
        },
        "samples": [
            {
                "time_min": item.time_min,
                "mean_concentration": item.mean_concentration,
                "min_concentration": item.min_concentration,
                "max_concentration": item.max_concentration,
                "integrated_field_quantity": item.integrated_field_quantity,
                "internalized_field_quantity": item.internalized_field_quantity,
            }
            for item in result.samples
        ],
        "field_snapshots": [
            {
                "time_min": item.time_min,
                "values": list(item.values),
            }
            for item in result.field_snapshots
        ],
        "recipient_uptake_series": [
            {
                "identifier": item.identifier,
                "x_micron": item.x_micron,
                "y_micron": item.y_micron,
                "effective_volume_micron3": item.effective_volume_micron3,
                "uptake_rate_per_min": item.uptake_rate_per_min,
                "samples": [
                    {
                        "time_min": sample.time_min,
                        "internalized_field_quantity": (
                            sample.internalized_field_quantity
                        ),
                    }
                    for sample in item.samples
                ],
            }
            for item in result.recipient_uptake_series
        ],
    }


def _decode_result(value: Any) -> BioFVMRunResult:
    if not isinstance(value, dict):
        raise ValueError("result must be an object")
    units = value["units"]
    engine = value["engine"]
    grid = value["grid"]
    if not all(isinstance(item, dict) for item in (units, engine, grid)):
        raise ValueError("result units, engine and grid must be objects")

    return BioFVMRunResult(
        experiment_id=value["experiment_id"],
        concentration_unit=units["concentration"],
        integrated_quantity_unit=units["integrated_quantity"],
        internalized_quantity_unit=units["internalized_quantity"],
        engine=BioFVMEngineMetadata(
            engine=engine["engine"],
            physicell_release=engine["physicell_release"],
            physicell_commit=engine["physicell_commit"],
            biofvm_version=engine["biofvm_version"],
        ),
        grid=BioFVMGrid2D(
            nx=grid["nx"],
            ny=grid["ny"],
            grid_spacing_micron=grid["grid_spacing_micron"],
            slice_thickness_micron=grid["slice_thickness_micron"],
            ordering=grid["ordering"],
        ),
        samples=tuple(
            TransportSample(
                time_min=item["time_min"],
                mean_concentration=item["mean_concentration"],
                min_concentration=item["min_concentration"],
                max_concentration=item["max_concentration"],
                integrated_field_quantity=item["integrated_field_quantity"],
                internalized_field_quantity=item["internalized_field_quantity"],
            )
            for item in value["samples"]
        ),
        field_snapshots=tuple(
            SpatialFieldSnapshot2D(
                time_min=item["time_min"],
                values=tuple(item["values"]),
            )
            for item in value["field_snapshots"]
        ),
        recipient_uptake_series=tuple(
            RecipientUptakeSeries(
                identifier=item["identifier"],
                x_micron=item["x_micron"],
                y_micron=item["y_micron"],
                effective_volume_micron3=item["effective_volume_micron3"],
                uptake_rate_per_min=item["uptake_rate_per_min"],
                samples=tuple(
                    RecipientUptakeSample(
                        time_min=sample["time_min"],
                        internalized_field_quantity=(
                            sample["internalized_field_quantity"]
                        ),
                    )
                    for sample in item["samples"]
                ),
            )
            for item in value["recipient_uptake_series"]
        ),
    )


def _payload(bundle: SimulationRunBundle) -> dict[str, Any]:
    return {
        "vesiclescope_revision": bundle.vesiclescope_revision,
        "experiment": _encode_experiment(bundle.experiment),
        "numerics": _encode_numerics(bundle.numerics),
        "result": _encode_result(bundle.result),
    }


def _canonical_payload_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _payload_digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_payload_bytes(payload)).hexdigest()


def run_bundle_payload_sha256(bundle: SimulationRunBundle) -> str:
    """Return the canonical SHA-256 of one run bundle's scientific payload."""

    if not isinstance(bundle, SimulationRunBundle):
        raise TypeError("bundle must be a SimulationRunBundle")
    return _payload_digest(_payload(bundle))


def serialize_run_bundle(bundle: SimulationRunBundle) -> bytes:
    """Serialize a deterministic, integrity-protected v0.1 run bundle."""

    if not isinstance(bundle, SimulationRunBundle):
        raise TypeError("bundle must be a SimulationRunBundle")
    payload = _payload(bundle)
    document = {
        "schema": RUN_BUNDLE_SCHEMA,
        "version": RUN_BUNDLE_VERSION,
        "payload_sha256": _payload_digest(payload),
        "payload": payload,
    }
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def deserialize_run_bundle(data: bytes | str) -> SimulationRunBundle:
    """Parse, integrity-check and reconstruct a v0.1 simulation run bundle."""

    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("run bundle must be valid UTF-8") from exc
    elif isinstance(data, str):
        text = data
    else:
        raise TypeError("run bundle data must be bytes or text")

    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("run bundle contains malformed JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("run bundle document must be a JSON object")
    if document.get("schema") != RUN_BUNDLE_SCHEMA:
        raise ValueError("unsupported run bundle schema")
    if document.get("version") != RUN_BUNDLE_VERSION:
        raise ValueError("unsupported run bundle version")

    payload = document.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("run bundle payload must be an object")
    digest = document.get("payload_sha256")
    if not isinstance(digest, str) or digest != _payload_digest(payload):
        raise ValueError("run bundle payload digest mismatch")

    try:
        return SimulationRunBundle(
            vesiclescope_revision=payload["vesiclescope_revision"],
            experiment=_decode_experiment(payload["experiment"]),
            numerics=_decode_numerics(payload["numerics"]),
            result=_decode_result(payload["result"]),
        )
    except KeyError as exc:
        raise ValueError(f"run bundle payload is missing required field {exc.args[0]!r}") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid run bundle payload: {exc}") from exc


def write_run_bundle(path: Path, bundle: SimulationRunBundle) -> Path:
    """Atomically write one deterministic bundle to a requested filesystem path."""

    output = Path(path)
    if output.exists() and output.is_dir():
        raise ValueError("run bundle output path must be a file")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = serialize_run_bundle(bundle)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, output)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return output


def read_run_bundle(path: Path) -> SimulationRunBundle:
    """Read and validate one durable run bundle."""

    source = Path(path)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read run bundle: {source}") from exc
    return deserialize_run_bundle(data)
