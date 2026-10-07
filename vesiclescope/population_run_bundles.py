"""Deterministic persistence for phenotype-specific perturbation transport runs."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from vesiclescope.domain import (
    EffectDirection,
    EffectOperation,
    ModelEffectTarget,
)
from vesiclescope.experiment_files import (
    decode_experiment_payload,
    encode_experiment_payload,
)
from vesiclescope.perturbation_files import (
    deserialize_perturbation_document,
    serialize_perturbation_document,
)
from vesiclescope.run_bundles import (
    deserialize_run_bundle,
    serialize_run_bundle,
)
from vesiclescope.workflows.perturbation_transport import (
    EffectExecutionAudit,
    EffectExecutionStatus,
    PopulationRunRecord,
    PopulationTransportRun,
)


POPULATION_RUN_BUNDLE_SCHEMA = "vesiclescope.population-simulation-run"
POPULATION_RUN_BUNDLE_VERSION = 1


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


def _encode_audit(value: EffectExecutionAudit) -> dict[str, Any]:
    return {
        "effect_id": value.effect_id,
        "exposure_id": value.exposure_id,
        "phenotype_id": value.phenotype_id,
        "direction": value.direction.value,
        "status": value.status.value,
        "reason": value.reason,
        "model_target": value.model_target.value if value.model_target else None,
        "target_identifier": value.target_identifier,
        "operation": value.operation.value if value.operation else None,
        "mapping_parameter_id": value.mapping_parameter_id,
        "mapping_evidence": value.mapping_evidence,
        "mapping_source_id": value.mapping_source_id,
        "baseline_value": value.baseline_value,
        "effective_value": value.effective_value,
        "unit": value.unit,
    }


def _decode_audit(value: Any) -> EffectExecutionAudit:
    if not isinstance(value, dict):
        raise ValueError("effect execution audit must be an object")
    try:
        direction = EffectDirection(value["direction"])
        status = EffectExecutionStatus(value["status"])
        model_target = (
            ModelEffectTarget(value["model_target"])
            if value.get("model_target") is not None
            else None
        )
        operation = (
            EffectOperation(value["operation"])
            if value.get("operation") is not None
            else None
        )
    except (KeyError, ValueError) as exc:
        raise ValueError("effect execution audit has an unsupported enum value") from exc
    return EffectExecutionAudit(
        effect_id=value["effect_id"],
        exposure_id=value["exposure_id"],
        phenotype_id=value.get("phenotype_id"),
        direction=direction,
        status=status,
        reason=value["reason"],
        model_target=model_target,
        target_identifier=value.get("target_identifier"),
        operation=operation,
        mapping_parameter_id=value.get("mapping_parameter_id"),
        mapping_evidence=value.get("mapping_evidence"),
        mapping_source_id=value.get("mapping_source_id"),
        baseline_value=value.get("baseline_value"),
        effective_value=value.get("effective_value"),
        unit=value.get("unit"),
    )


def _encode_run(run: PopulationTransportRun) -> dict[str, Any]:
    return {
        "study_document": json.loads(serialize_perturbation_document(run.study)),
        "unexecuted_effects": [
            _encode_audit(item) for item in run.unexecuted_effects
        ],
        "populations": [
            {
                "phenotype_id": item.phenotype_id,
                "baseline_experiment": encode_experiment_payload(
                    item.baseline_experiment
                ),
                "effects": [_encode_audit(effect) for effect in item.effects],
                "run_bundle": json.loads(serialize_run_bundle(item.run_bundle)),
            }
            for item in run.populations
        ],
    }


def serialize_population_run_bundle(run: PopulationTransportRun) -> bytes:
    """Serialize one integrity-protected multi-population run."""

    if not isinstance(run, PopulationTransportRun):
        raise TypeError("run must be a PopulationTransportRun")
    payload = _encode_run(run)
    document = {
        "schema": POPULATION_RUN_BUNDLE_SCHEMA,
        "version": POPULATION_RUN_BUNDLE_VERSION,
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


def deserialize_population_run_bundle(data: bytes | str) -> PopulationTransportRun:
    """Parse and integrity-check one multi-population run bundle."""

    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("population run bundle must be valid UTF-8") from exc
    elif isinstance(data, str):
        text = data
    else:
        raise TypeError("population run bundle data must be bytes or text")

    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("population run bundle contains malformed JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("population run bundle document must be an object")
    if document.get("schema") != POPULATION_RUN_BUNDLE_SCHEMA:
        raise ValueError("unsupported population run bundle schema")
    if document.get("version") != POPULATION_RUN_BUNDLE_VERSION:
        raise ValueError("unsupported population run bundle version")

    payload = document.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("population run bundle payload must be an object")
    digest = document.get("payload_sha256")
    if not isinstance(digest, str) or digest != _payload_digest(payload):
        raise ValueError("population run bundle payload digest mismatch")

    try:
        study = deserialize_perturbation_document(
            json.dumps(
                payload["study_document"],
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
        )
        populations = tuple(
            PopulationRunRecord(
                phenotype_id=item["phenotype_id"],
                baseline_experiment=decode_experiment_payload(
                    item["baseline_experiment"]
                ),
                effects=tuple(_decode_audit(effect) for effect in item["effects"]),
                run_bundle=deserialize_run_bundle(
                    json.dumps(
                        item["run_bundle"],
                        ensure_ascii=False,
                        allow_nan=False,
                        sort_keys=True,
                    )
                ),
            )
            for item in payload["populations"]
        )
        return PopulationTransportRun(
            study=study,
            populations=populations,
            unexecuted_effects=tuple(
                _decode_audit(item)
                for item in payload.get("unexecuted_effects", [])
            ),
        )
    except KeyError as exc:
        raise ValueError(
            f"population run bundle is missing required field {exc.args[0]!r}"
        ) from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid population run bundle: {exc}") from exc


def write_population_run_bundle(
    path: Path,
    run: PopulationTransportRun,
) -> Path:
    """Atomically write one deterministic multi-population run."""

    output = Path(path)
    if output.exists() and output.is_dir():
        raise ValueError("population run output path must be a file")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = serialize_population_run_bundle(run)

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


def read_population_run_bundle(path: Path) -> PopulationTransportRun:
    """Read and validate one durable multi-population run bundle."""

    source = Path(path)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read population run bundle: {source}") from exc
    return deserialize_population_run_bundle(data)
