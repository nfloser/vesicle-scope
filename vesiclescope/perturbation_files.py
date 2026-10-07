"""Deterministic documents for evidence-aware perturbation studies."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from vesiclescope.domain import (
    BiologicalExposure,
    CargoClass,
    EffectDirection,
    EffectOperation,
    EffectOutcome,
    EVCargoFeature,
    EVMarkerFeature,
    EVPhenotype,
    EvidenceCategory,
    EvidenceSource,
    ExposureTarget,
    MarkerState,
    ModelEffectMapping,
    ModelEffectTarget,
    ParameterContext,
    PerturbationEffect,
    PerturbationStudy,
    ScientificParameter,
)


PERTURBATION_DOCUMENT_SCHEMA = "vesiclescope.perturbation-study"
PERTURBATION_DOCUMENT_VERSION = 1


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


def _encode_source(source: EvidenceSource | None) -> dict[str, Any] | None:
    if source is None:
        return None
    return {"identifier": source.identifier, "location": source.location}


def _decode_source(value: Any) -> EvidenceSource | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("evidence source must be an object or null")
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
        raise ValueError("context must be an object or null")
    return ParameterContext(
        species=value.get("species"),
        tissue=value.get("tissue"),
        cell_type=value.get("cell_type"),
        cell_line=value.get("cell_line"),
        ev_preparation=value.get("ev_preparation"),
        measurement_method=value.get("measurement_method"),
        experimental_conditions=value.get("experimental_conditions"),
    )


def _encode_parameter(value: ScientificParameter | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "identifier": value.identifier,
        "scientific_name": value.scientific_name,
        "value": value.value,
        "unit": value.unit,
        "evidence": value.evidence.value,
        "source": _encode_source(value.source),
        "context": _encode_context(value.context),
        "assumptions": list(value.assumptions),
        "limitations": list(value.limitations),
    }


def _decode_parameter(value: Any) -> ScientificParameter | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("scientific parameter must be an object or null")
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
        assumptions=tuple(value.get("assumptions", [])),
        limitations=tuple(value.get("limitations", [])),
    )


def _encode_exposure(value: BiologicalExposure) -> dict[str, Any]:
    return {
        "identifier": value.identifier,
        "compound_name": value.compound_name,
        "concentration": _encode_parameter(value.concentration),
        "target": value.target.value,
        "start_min": value.start_min,
        "end_min": value.end_min,
        "evidence": value.evidence.value,
        "source": _encode_source(value.source),
        "context": _encode_context(value.context),
        "assumptions": list(value.assumptions),
        "limitations": list(value.limitations),
    }


def _decode_exposure(value: Any) -> BiologicalExposure:
    if not isinstance(value, dict):
        raise ValueError("exposure must be an object")
    try:
        target = ExposureTarget(value["target"])
        evidence = EvidenceCategory(value["evidence"])
    except (KeyError, ValueError) as exc:
        raise ValueError("exposure has an unsupported enum value") from exc
    concentration = _decode_parameter(value["concentration"])
    if concentration is None:
        raise ValueError("exposure concentration cannot be null")
    return BiologicalExposure(
        identifier=value["identifier"],
        compound_name=value["compound_name"],
        concentration=concentration,
        target=target,
        start_min=value["start_min"],
        end_min=value["end_min"],
        evidence=evidence,
        source=_decode_source(value.get("source")),
        context=_decode_context(value.get("context")),
        assumptions=tuple(value.get("assumptions", [])),
        limitations=tuple(value.get("limitations", [])),
    )


def _encode_marker(value: EVMarkerFeature) -> dict[str, Any]:
    return {
        "identifier": value.identifier,
        "marker_name": value.marker_name,
        "state": value.state.value,
        "evidence": value.evidence.value,
        "source": _encode_source(value.source),
        "context": _encode_context(value.context),
        "limitations": list(value.limitations),
    }


def _decode_marker(value: Any) -> EVMarkerFeature:
    if not isinstance(value, dict):
        raise ValueError("marker feature must be an object")
    try:
        state = MarkerState(value["state"])
        evidence = EvidenceCategory(value["evidence"])
    except (KeyError, ValueError) as exc:
        raise ValueError("marker feature has an unsupported enum value") from exc
    return EVMarkerFeature(
        identifier=value["identifier"],
        marker_name=value["marker_name"],
        state=state,
        evidence=evidence,
        source=_decode_source(value.get("source")),
        context=_decode_context(value.get("context")),
        limitations=tuple(value.get("limitations", [])),
    )


def _encode_cargo(value: EVCargoFeature) -> dict[str, Any]:
    return {
        "identifier": value.identifier,
        "molecule_name": value.molecule_name,
        "cargo_class": value.cargo_class.value,
        "evidence": value.evidence.value,
        "source": _encode_source(value.source),
        "context": _encode_context(value.context),
        "abundance": _encode_parameter(value.abundance),
        "qualitative_state": value.qualitative_state,
        "limitations": list(value.limitations),
    }


def _decode_cargo(value: Any) -> EVCargoFeature:
    if not isinstance(value, dict):
        raise ValueError("cargo feature must be an object")
    try:
        cargo_class = CargoClass(value["cargo_class"])
        evidence = EvidenceCategory(value["evidence"])
    except (KeyError, ValueError) as exc:
        raise ValueError("cargo feature has an unsupported enum value") from exc
    return EVCargoFeature(
        identifier=value["identifier"],
        molecule_name=value["molecule_name"],
        cargo_class=cargo_class,
        evidence=evidence,
        source=_decode_source(value.get("source")),
        context=_decode_context(value.get("context")),
        abundance=_decode_parameter(value.get("abundance")),
        qualitative_state=value.get("qualitative_state"),
        limitations=tuple(value.get("limitations", [])),
    )


def _encode_phenotype(value: EVPhenotype) -> dict[str, Any]:
    return {
        "identifier": value.identifier,
        "name": value.name,
        "markers": [_encode_marker(item) for item in value.markers],
        "cargo": [_encode_cargo(item) for item in value.cargo],
        "context": _encode_context(value.context),
        "limitations": list(value.limitations),
    }


def _decode_phenotype(value: Any) -> EVPhenotype:
    if not isinstance(value, dict):
        raise ValueError("EV phenotype must be an object")
    return EVPhenotype(
        identifier=value["identifier"],
        name=value["name"],
        markers=tuple(_decode_marker(item) for item in value.get("markers", [])),
        cargo=tuple(_decode_cargo(item) for item in value.get("cargo", [])),
        context=_decode_context(value.get("context")),
        limitations=tuple(value.get("limitations", [])),
    )


def _encode_mapping(value: ModelEffectMapping | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "target": value.target.value,
        "operation": value.operation.value,
        "value": _encode_parameter(value.value),
        "target_identifier": value.target_identifier,
    }


def _decode_mapping(value: Any) -> ModelEffectMapping | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("model effect mapping must be an object or null")
    try:
        target = ModelEffectTarget(value["target"])
        operation = EffectOperation(value["operation"])
    except (KeyError, ValueError) as exc:
        raise ValueError("model effect mapping has an unsupported enum value") from exc
    parameter = _decode_parameter(value["value"])
    if parameter is None:
        raise ValueError("model effect mapping value cannot be null")
    return ModelEffectMapping(
        target=target,
        operation=operation,
        value=parameter,
        target_identifier=value.get("target_identifier"),
    )


def _encode_effect(value: PerturbationEffect) -> dict[str, Any]:
    return {
        "identifier": value.identifier,
        "exposure_id": value.exposure_id,
        "outcome": value.outcome.value,
        "direction": value.direction.value,
        "evidence": value.evidence.value,
        "source": _encode_source(value.source),
        "context": _encode_context(value.context),
        "phenotype_id": value.phenotype_id,
        "feature_id": value.feature_id,
        "magnitude": _encode_parameter(value.magnitude),
        "model_mapping": _encode_mapping(value.model_mapping),
        "limitations": list(value.limitations),
    }


def _decode_effect(value: Any) -> PerturbationEffect:
    if not isinstance(value, dict):
        raise ValueError("perturbation effect must be an object")
    try:
        outcome = EffectOutcome(value["outcome"])
        direction = EffectDirection(value["direction"])
        evidence = EvidenceCategory(value["evidence"])
    except (KeyError, ValueError) as exc:
        raise ValueError("perturbation effect has an unsupported enum value") from exc
    return PerturbationEffect(
        identifier=value["identifier"],
        exposure_id=value["exposure_id"],
        outcome=outcome,
        direction=direction,
        evidence=evidence,
        source=_decode_source(value.get("source")),
        context=_decode_context(value.get("context")),
        phenotype_id=value.get("phenotype_id"),
        feature_id=value.get("feature_id"),
        magnitude=_decode_parameter(value.get("magnitude")),
        model_mapping=_decode_mapping(value.get("model_mapping")),
        limitations=tuple(value.get("limitations", [])),
    )


def _encode_study(study: PerturbationStudy) -> dict[str, Any]:
    return {
        "study_id": study.study_id,
        "exposures": [_encode_exposure(item) for item in study.exposures],
        "phenotypes": [_encode_phenotype(item) for item in study.phenotypes],
        "effects": [_encode_effect(item) for item in study.effects],
        "measurement_dataset_ids": list(study.measurement_dataset_ids),
        "transport_experiment_ids": list(study.transport_experiment_ids),
        "limitations": list(study.limitations),
    }


def _decode_study(value: Any) -> PerturbationStudy:
    if not isinstance(value, dict):
        raise ValueError("perturbation study must be an object")
    return PerturbationStudy(
        study_id=value["study_id"],
        exposures=tuple(_decode_exposure(item) for item in value["exposures"]),
        phenotypes=tuple(_decode_phenotype(item) for item in value["phenotypes"]),
        effects=tuple(_decode_effect(item) for item in value["effects"]),
        measurement_dataset_ids=tuple(value.get("measurement_dataset_ids", [])),
        transport_experiment_ids=tuple(value.get("transport_experiment_ids", [])),
        limitations=tuple(value.get("limitations", [])),
    )


def serialize_perturbation_document(study: PerturbationStudy) -> str:
    """Serialize one integrity-protected perturbation study."""

    if not isinstance(study, PerturbationStudy):
        raise TypeError("study must be a PerturbationStudy")
    payload = {"study": _encode_study(study)}
    document = {
        "schema": PERTURBATION_DOCUMENT_SCHEMA,
        "version": PERTURBATION_DOCUMENT_VERSION,
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


def deserialize_perturbation_document(text: str) -> PerturbationStudy:
    """Parse and integrity-check one perturbation-study document."""

    if not isinstance(text, str):
        raise TypeError("perturbation document must be text")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("perturbation document is not valid JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("perturbation document must be an object")
    if set(document) != {"schema", "version", "payload_sha256", "payload"}:
        raise ValueError("perturbation document has unexpected or missing top-level fields")
    if document["schema"] != PERTURBATION_DOCUMENT_SCHEMA:
        raise ValueError("unsupported perturbation document schema")
    if document["version"] != PERTURBATION_DOCUMENT_VERSION:
        raise ValueError("unsupported perturbation document version")

    payload = document["payload"]
    if not isinstance(payload, dict) or set(payload) != {"study"}:
        raise ValueError("perturbation document payload must contain exactly one study")
    digest = document["payload_sha256"]
    if not isinstance(digest, str) or digest != _payload_digest(payload):
        raise ValueError("perturbation document payload digest mismatch")

    try:
        return _decode_study(payload["study"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid perturbation study: {exc}") from exc
