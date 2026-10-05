"""Deterministic external VesicleScope experiment documents."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from vesiclescope.domain import TransportExperiment
from vesiclescope.run_bundles import (
    decode_experiment_payload,
    encode_experiment_payload,
)


EXPERIMENT_DOCUMENT_SCHEMA = "vesiclescope.experiment"
EXPERIMENT_DOCUMENT_VERSION = 1


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


def serialize_experiment_document(experiment: TransportExperiment) -> str:
    payload = {"experiment": encode_experiment_payload(experiment)}
    document = {
        "schema": EXPERIMENT_DOCUMENT_SCHEMA,
        "version": EXPERIMENT_DOCUMENT_VERSION,
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


def deserialize_experiment_document(text: str) -> TransportExperiment:
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("experiment document is not valid JSON") from exc

    if not isinstance(document, dict):
        raise ValueError("experiment document must be an object")
    if set(document) != {"schema", "version", "payload_sha256", "payload"}:
        raise ValueError("experiment document has unexpected or missing top-level fields")
    if document["schema"] != EXPERIMENT_DOCUMENT_SCHEMA:
        raise ValueError("unsupported experiment document schema")
    if document["version"] != EXPERIMENT_DOCUMENT_VERSION:
        raise ValueError("unsupported experiment document version")

    payload = document["payload"]
    if not isinstance(payload, dict) or set(payload) != {"experiment"}:
        raise ValueError("experiment document payload must contain exactly one experiment")
    digest = document["payload_sha256"]
    if not isinstance(digest, str) or digest != _payload_digest(payload):
        raise ValueError("experiment document payload digest does not match content")

    try:
        return decode_experiment_payload(payload["experiment"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid experiment payload: {exc}") from exc


def write_experiment_document(
    path: Path,
    experiment: TransportExperiment,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    content = serialize_experiment_document(experiment)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, output)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return output


def read_experiment_document(path: Path) -> TransportExperiment:
    input_path = Path(path)
    try:
        text = input_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read experiment document: {input_path}") from exc
    return deserialize_experiment_document(text)
