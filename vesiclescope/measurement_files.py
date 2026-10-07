"""Deterministic documents for longitudinal EV measurement datasets."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from vesiclescope.domain import (
    AssayObservation,
    BloodEVPreanalytics,
    CentrifugationStep,
    LongitudinalEVDataset,
    MeasurementKind,
    MeasurementTimepoint,
    SpecimenKind,
)


MEASUREMENT_DOCUMENT_SCHEMA = "vesiclescope.ev-measurements"
MEASUREMENT_DOCUMENT_VERSION = 1


def _canonical_payload_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _payload_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_payload_bytes(payload)).hexdigest()


def _encode_centrifugation_step(step: CentrifugationStep) -> dict[str, Any]:
    return {
        "relative_centrifugal_force_g": step.relative_centrifugal_force_g,
        "duration_min": step.duration_min,
        "retained_fraction": step.retained_fraction,
        "temperature_c": step.temperature_c,
    }


def _decode_centrifugation_step(value: Any) -> CentrifugationStep:
    if not isinstance(value, dict):
        raise ValueError("centrifugation step must be an object")
    return CentrifugationStep(
        relative_centrifugal_force_g=value["relative_centrifugal_force_g"],
        duration_min=value["duration_min"],
        retained_fraction=value["retained_fraction"],
        temperature_c=value.get("temperature_c"),
    )


def _encode_preanalytics(value: BloodEVPreanalytics) -> dict[str, Any]:
    return {
        "sample_id": value.sample_id,
        "specimen": value.specimen.value,
        "anticoagulant": value.anticoagulant,
        "collection_to_processing_min": value.collection_to_processing_min,
        "centrifugation_steps": [
            _encode_centrifugation_step(step)
            for step in value.centrifugation_steps
        ],
        "residual_platelet_count_per_ul": value.residual_platelet_count_per_ul,
        "hemolysis_assessment": value.hemolysis_assessment,
        "limitations": list(value.limitations),
    }


def _decode_preanalytics(value: Any) -> BloodEVPreanalytics:
    if not isinstance(value, dict):
        raise ValueError("preanalytics must be an object")
    try:
        specimen = SpecimenKind(value["specimen"])
    except (KeyError, ValueError) as exc:
        raise ValueError("preanalytics has an unsupported specimen kind") from exc
    return BloodEVPreanalytics(
        sample_id=value["sample_id"],
        specimen=specimen,
        anticoagulant=value.get("anticoagulant"),
        collection_to_processing_min=value["collection_to_processing_min"],
        centrifugation_steps=tuple(
            _decode_centrifugation_step(item)
            for item in value.get("centrifugation_steps", [])
        ),
        residual_platelet_count_per_ul=value.get("residual_platelet_count_per_ul"),
        hemolysis_assessment=value.get("hemolysis_assessment"),
        limitations=tuple(value.get("limitations", [])),
    )


def _encode_observation(value: AssayObservation) -> dict[str, Any]:
    return {
        "identifier": value.identifier,
        "scientific_name": value.scientific_name,
        "kind": value.kind.value,
        "value": value.value,
        "unit": value.unit,
        "method": value.method,
        "detection_semantics": value.detection_semantics,
        "markers": list(value.markers),
        "technical_replicates": value.technical_replicates,
        "standard_deviation": value.standard_deviation,
        "notes": list(value.notes),
    }


def _decode_observation(value: Any) -> AssayObservation:
    if not isinstance(value, dict):
        raise ValueError("assay observation must be an object")
    try:
        kind = MeasurementKind(value["kind"])
    except (KeyError, ValueError) as exc:
        raise ValueError("assay observation has an unsupported measurement kind") from exc
    return AssayObservation(
        identifier=value["identifier"],
        scientific_name=value["scientific_name"],
        kind=kind,
        value=value["value"],
        unit=value["unit"],
        method=value["method"],
        detection_semantics=value["detection_semantics"],
        markers=tuple(value.get("markers", [])),
        technical_replicates=value.get("technical_replicates"),
        standard_deviation=value.get("standard_deviation"),
        notes=tuple(value.get("notes", [])),
    )


def _encode_timepoint(value: MeasurementTimepoint) -> dict[str, Any]:
    return {
        "condition_id": value.condition_id,
        "time_min": value.time_min,
        "biological_replicate_id": value.biological_replicate_id,
        "observations": [
            _encode_observation(item)
            for item in value.observations
        ],
    }


def _decode_timepoint(value: Any) -> MeasurementTimepoint:
    if not isinstance(value, dict):
        raise ValueError("measurement timepoint must be an object")
    return MeasurementTimepoint(
        condition_id=value["condition_id"],
        time_min=value["time_min"],
        biological_replicate_id=value.get("biological_replicate_id"),
        observations=tuple(
            _decode_observation(item)
            for item in value["observations"]
        ),
    )


def _encode_dataset(dataset: LongitudinalEVDataset) -> dict[str, Any]:
    return {
        "dataset_id": dataset.dataset_id,
        "preanalytics": _encode_preanalytics(dataset.preanalytics),
        "timepoints": [
            _encode_timepoint(item)
            for item in dataset.timepoints
        ],
        "reference_time_description": dataset.reference_time_description,
        "limitations": list(dataset.limitations),
    }


def _decode_dataset(value: Any) -> LongitudinalEVDataset:
    if not isinstance(value, dict):
        raise ValueError("measurement dataset must be an object")
    return LongitudinalEVDataset(
        dataset_id=value["dataset_id"],
        preanalytics=_decode_preanalytics(value["preanalytics"]),
        timepoints=tuple(
            _decode_timepoint(item)
            for item in value["timepoints"]
        ),
        reference_time_description=value["reference_time_description"],
        limitations=tuple(value.get("limitations", [])),
    )


def serialize_measurement_document(dataset: LongitudinalEVDataset) -> str:
    """Serialize one integrity-protected longitudinal EV measurement dataset."""

    if not isinstance(dataset, LongitudinalEVDataset):
        raise TypeError("dataset must be a LongitudinalEVDataset")
    payload = {"dataset": _encode_dataset(dataset)}
    document = {
        "schema": MEASUREMENT_DOCUMENT_SCHEMA,
        "version": MEASUREMENT_DOCUMENT_VERSION,
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
    )


def deserialize_measurement_document(text: str) -> LongitudinalEVDataset:
    """Parse and integrity-check one longitudinal EV measurement document."""

    if not isinstance(text, str):
        raise TypeError("measurement document must be text")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("measurement document is not valid JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("measurement document must be an object")
    if set(document) != {"schema", "version", "payload_sha256", "payload"}:
        raise ValueError("measurement document has unexpected or missing top-level fields")
    if document["schema"] != MEASUREMENT_DOCUMENT_SCHEMA:
        raise ValueError("unsupported measurement document schema")
    if document["version"] != MEASUREMENT_DOCUMENT_VERSION:
        raise ValueError("unsupported measurement document version")

    payload = document["payload"]
    if not isinstance(payload, dict) or set(payload) != {"dataset"}:
        raise ValueError("measurement document payload must contain exactly one dataset")
    digest = document["payload_sha256"]
    if not isinstance(digest, str) or digest != _payload_digest(payload):
        raise ValueError("measurement document payload digest mismatch")

    try:
        return _decode_dataset(payload["dataset"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid measurement dataset: {exc}") from exc
