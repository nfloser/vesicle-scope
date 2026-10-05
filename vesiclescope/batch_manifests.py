"""Deterministic manifest contract for completed explicit experiment batches."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile

from vesiclescope.engines import BioFVMNumerics


BATCH_MANIFEST_SCHEMA = "vesiclescope.experiment-batch"
BATCH_MANIFEST_VERSION = 1
BATCH_SCIENTIFIC_STATUS = (
    "explicit input batch; no sampling or biological distribution implied"
)
_SHA_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, slots=True)
class ExperimentBatchManifestMember:
    index: int
    input_filename: str
    experiment_id: str
    run_filename: str
    run_bundle_payload_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.index, int) or isinstance(self.index, bool) or self.index < 1:
            raise ValueError("batch member index must be a positive integer")
        for value, field_name in (
            (self.input_filename, "input_filename"),
            (self.experiment_id, "experiment_id"),
            (self.run_filename, "run_filename"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"batch member {field_name} must be non-blank")
        for filename, field_name in (
            (self.input_filename, "input_filename"),
            (self.run_filename, "run_filename"),
        ):
            if Path(filename).name != filename or "/" in filename or "\\" in filename:
                raise ValueError(f"batch member {field_name} must be a plain filename")
        digest = self.run_bundle_payload_sha256
        if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
            raise ValueError("batch member run_bundle_payload_sha256 must be lowercase SHA-256")


@dataclass(frozen=True, slots=True)
class ExperimentBatchManifest:
    vesiclescope_revision: str
    numerics: BioFVMNumerics
    members: tuple[ExperimentBatchManifestMember, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.vesiclescope_revision, str) or _SHA_RE.fullmatch(
            self.vesiclescope_revision
        ) is None:
            raise ValueError(
                "batch vesiclescope_revision must be a 40- or 64-character hexadecimal SHA"
            )
        object.__setattr__(
            self,
            "vesiclescope_revision",
            self.vesiclescope_revision.lower(),
        )
        if not isinstance(self.numerics, BioFVMNumerics):
            raise TypeError("batch numerics must be BioFVMNumerics")
        if not isinstance(self.members, tuple) or not self.members:
            raise ValueError("batch manifest requires at least one member")
        if not all(
            isinstance(member, ExperimentBatchManifestMember)
            for member in self.members
        ):
            raise TypeError("batch members must be ExperimentBatchManifestMember objects")

        expected = tuple(range(1, len(self.members) + 1))
        observed = tuple(member.index for member in self.members)
        if observed != expected:
            raise ValueError("batch member indices must be contiguous and ordered from 1")
        experiment_ids = tuple(member.experiment_id for member in self.members)
        if len(set(experiment_ids)) != len(experiment_ids):
            raise ValueError("batch manifest contains duplicate experiment_id values")
        run_filenames = tuple(member.run_filename for member in self.members)
        if len(set(run_filenames)) != len(run_filenames):
            raise ValueError("batch manifest contains duplicate run filenames")


def batch_manifest_payload(manifest: ExperimentBatchManifest) -> dict[str, object]:
    if not isinstance(manifest, ExperimentBatchManifest):
        raise TypeError("manifest must be an ExperimentBatchManifest")
    return {
        "schema": BATCH_MANIFEST_SCHEMA,
        "version": BATCH_MANIFEST_VERSION,
        "scientific_status": BATCH_SCIENTIFIC_STATUS,
        "vesiclescope_revision": manifest.vesiclescope_revision,
        "numerics": {
            "grid_spacing_micron": manifest.numerics.grid_spacing_micron,
            "time_step_min": manifest.numerics.time_step_min,
        },
        "members": [
            {
                "index": member.index,
                "input_filename": member.input_filename,
                "experiment_id": member.experiment_id,
                "run_filename": member.run_filename,
                "run_bundle_payload_sha256": member.run_bundle_payload_sha256,
            }
            for member in manifest.members
        ],
    }


def serialize_batch_manifest(manifest: ExperimentBatchManifest) -> str:
    return (
        json.dumps(
            batch_manifest_payload(manifest),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


def deserialize_batch_manifest(document: str) -> ExperimentBatchManifest:
    if not isinstance(document, str):
        raise TypeError("batch manifest document must be text")
    try:
        payload = json.loads(document)
    except json.JSONDecodeError as exc:
        raise ValueError("batch manifest is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("batch manifest root must be an object")
    if payload.get("schema") != BATCH_MANIFEST_SCHEMA:
        raise ValueError("unsupported batch manifest schema")
    if payload.get("version") != BATCH_MANIFEST_VERSION:
        raise ValueError("unsupported batch manifest version")
    if payload.get("scientific_status") != BATCH_SCIENTIFIC_STATUS:
        raise ValueError("batch manifest scientific_status is incompatible")

    numerics_payload = payload.get("numerics")
    if not isinstance(numerics_payload, dict):
        raise ValueError("batch manifest numerics must be an object")
    try:
        numerics = BioFVMNumerics(
            grid_spacing_micron=numerics_payload["grid_spacing_micron"],
            time_step_min=numerics_payload["time_step_min"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("batch manifest numerics are invalid") from exc

    members_payload = payload.get("members")
    if not isinstance(members_payload, list) or not members_payload:
        raise ValueError("batch manifest members must be a non-empty array")
    members: list[ExperimentBatchManifestMember] = []
    for item in members_payload:
        if not isinstance(item, dict):
            raise ValueError("batch manifest member must be an object")
        try:
            members.append(
                ExperimentBatchManifestMember(
                    index=item["index"],
                    input_filename=item["input_filename"],
                    experiment_id=item["experiment_id"],
                    run_filename=item["run_filename"],
                    run_bundle_payload_sha256=item["run_bundle_payload_sha256"],
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("batch manifest member is invalid") from exc

    revision = payload.get("vesiclescope_revision")
    return ExperimentBatchManifest(
        vesiclescope_revision=revision,
        numerics=numerics,
        members=tuple(members),
    )


def write_batch_manifest(path: Path, manifest: ExperimentBatchManifest) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    content = serialize_batch_manifest(manifest)
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
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return output


def read_batch_manifest(path: Path) -> ExperimentBatchManifest:
    source = Path(path)
    try:
        document = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read batch manifest: {source}") from exc
    return deserialize_batch_manifest(document)
