"""Deterministic COMBINE Archive packaging for VesicleScope-native projects.

OMEX is used as a standards-oriented container only. This module deliberately
does not claim that the VesicleScope spatial BioFVM experiment is encoded in
SED-ML or another standardized model language.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree
import os
import tempfile
import zipfile

from vesiclescope.batch_manifests import (
    ExperimentBatchManifest,
    deserialize_batch_manifest,
    serialize_batch_manifest,
)
from vesiclescope.domain import TransportExperiment
from vesiclescope.experiment_files import (
    deserialize_experiment_document,
    serialize_experiment_document,
)
from vesiclescope.run_bundles import (
    SimulationRunBundle,
    deserialize_run_bundle,
    run_bundle_payload_sha256,
    serialize_run_bundle,
)


OMEX_NAMESPACE = "http://identifiers.org/combine.specifications/omex"
OMEX_MANIFEST_NAMESPACE = "http://identifiers.org/combine.specifications/omex-manifest"
JSON_MEDIA_TYPE_URI = "http://purl.org/NET/mediatypes/application/json"
MARKDOWN_MEDIA_TYPE_URI = "http://purl.org/NET/mediatypes/text/markdown"

MANIFEST_NAME = "manifest.xml"
EXPERIMENT_NAME = "experiment.json"
README_NAME = "README.md"
BATCH_MANIFEST_NAME = "batch-manifest.json"
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_MAX_ARCHIVE_MEMBERS = 1024
_MAX_MEMBER_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
_MAX_TOTAL_UNCOMPRESSED_BYTES = 512 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class CombineArchiveProject:
    """Validated VesicleScope content recovered from one OMEX archive."""

    experiment: TransportExperiment
    runs: tuple[SimulationRunBundle, ...]


@dataclass(frozen=True, slots=True)
class CombineBatchArchiveProject:
    """Validated completed VesicleScope batch recovered from one OMEX archive."""

    manifest: ExperimentBatchManifest
    experiments: tuple[TransportExperiment, ...]
    runs: tuple[SimulationRunBundle, ...]


def _member_name_is_safe(name: str) -> bool:
    if not isinstance(name, str) or not name or "\\" in name:
        return False
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return False
    return True


def _manifest_bytes(run_count: int) -> bytes:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<omexManifest xmlns="{OMEX_MANIFEST_NAMESPACE}">',
        f'  <content location="." format="{OMEX_NAMESPACE}"/>',
        f'  <content location="./{MANIFEST_NAME}" format="{OMEX_MANIFEST_NAMESPACE}"/>',
        f'  <content location="./{EXPERIMENT_NAME}" format="{JSON_MEDIA_TYPE_URI}" master="true"/>',
        f'  <content location="./{README_NAME}" format="{MARKDOWN_MEDIA_TYPE_URI}"/>',
    ]
    for index in range(1, run_count + 1):
        lines.append(
            f'  <content location="./runs/run-{index:03d}.json" '
            f'format="{JSON_MEDIA_TYPE_URI}"/>'
        )
    lines.append("</omexManifest>")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _readme_bytes(
    experiment: TransportExperiment,
    runs: tuple[SimulationRunBundle, ...],
) -> bytes:
    evidence = sorted(
        {
            experiment.diffusion.evidence.value,
            experiment.decay.evidence.value,
            experiment.initial_concentration.evidence.value,
            *(source.release_rate.evidence.value for source in experiment.release_sources),
            *(sink.uptake_rate.evidence.value for sink in experiment.uptake_sinks),
        }
    )
    lines = [
        "# VesicleScope COMBINE Archive",
        "",
        "This OMEX file is a standards-oriented container for VesicleScope-native artifacts.",
        "It does not claim SED-ML compatibility or generic execution by third-party simulators.",
        "",
        f"- Experiment: {experiment.experiment_id}",
        f"- Evidence categories: {', '.join(evidence)}",
        f"- Stored runs: {len(runs)}",
        "",
        "Embedded run bundles remain authoritative for solver identity, numerics, exact",
        "VesicleScope revision, normalized results and payload integrity.",
    ]
    if runs:
        lines.extend(["", "## Run payload digests", ""])
        for index, bundle in enumerate(runs, start=1):
            lines.append(
                f"- runs/run-{index:03d}.json: {run_bundle_payload_sha256(bundle)}"
            )
    lines.extend(
        [
            "",
            "Scientific status: numerical/simulation artifacts are not experimental evidence",
            "unless an embedded parameter source explicitly documents measured evidence.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _batch_manifest_bytes(member_count: int) -> bytes:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<omexManifest xmlns="{OMEX_MANIFEST_NAMESPACE}">',
        f'  <content location="." format="{OMEX_NAMESPACE}"/>',
        f'  <content location="./{MANIFEST_NAME}" format="{OMEX_MANIFEST_NAMESPACE}"/>',
        f'  <content location="./{BATCH_MANIFEST_NAME}" format="{JSON_MEDIA_TYPE_URI}" master="true"/>',
        f'  <content location="./{README_NAME}" format="{MARKDOWN_MEDIA_TYPE_URI}"/>',
    ]
    for index in range(1, member_count + 1):
        lines.append(
            f'  <content location="./experiments/member-{index:03d}.json" '
            f'format="{JSON_MEDIA_TYPE_URI}"/>'
        )
        lines.append(
            f'  <content location="./runs/member-{index:03d}.run.json" '
            f'format="{JSON_MEDIA_TYPE_URI}"/>'
        )
    lines.append("</omexManifest>")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _batch_readme_bytes(
    manifest: ExperimentBatchManifest,
    experiments: tuple[TransportExperiment, ...],
) -> bytes:
    lines = [
        "# VesicleScope COMBINE Batch Archive",
        "",
        "This OMEX file contains a completed explicit VesicleScope experiment batch.",
        "It does not claim SED-ML compatibility for the VesicleScope BioFVM experiments.",
        "",
        f"- Members: {len(manifest.members)}",
        f"- VesicleScope revision: {manifest.vesiclescope_revision}",
        f"- Grid spacing: {manifest.numerics.grid_spacing_micron:g} micron",
        f"- Time step: {manifest.numerics.time_step_min:g} min",
        "",
        "Member order is authoritative and comes from batch-manifest.json.",
        "The batch is an explicit input set; no random sampling or biological distribution is implied.",
        "",
        "## Members",
        "",
    ]
    for member, experiment in zip(manifest.members, experiments):
        lines.append(
            f"- {member.index:03d}: {experiment.experiment_id}; "
            f"run digest {member.run_bundle_payload_sha256}"
        )
    lines.extend(
        [
            "",
            "Simulation output is not experimental evidence by itself.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _validate_batch_inputs(
    manifest: ExperimentBatchManifest,
    runs: tuple[SimulationRunBundle, ...],
) -> tuple[TransportExperiment, ...]:
    if not isinstance(manifest, ExperimentBatchManifest):
        raise TypeError("manifest must be an ExperimentBatchManifest")
    if not isinstance(runs, tuple) or not all(
        isinstance(bundle, SimulationRunBundle) for bundle in runs
    ):
        raise TypeError("runs must be a tuple of SimulationRunBundle objects")
    if len(runs) != len(manifest.members):
        raise ValueError("batch archive run count does not match the batch manifest")

    experiments: list[TransportExperiment] = []
    for member, bundle in zip(manifest.members, runs):
        if bundle.experiment.experiment_id != member.experiment_id:
            raise ValueError(
                "batch archive run experiment_id does not match the batch manifest"
            )
        if bundle.vesiclescope_revision != manifest.vesiclescope_revision:
            raise ValueError(
                "batch archive run revision does not match the batch manifest"
            )
        if bundle.numerics != manifest.numerics:
            raise ValueError(
                "batch archive run numerics do not match the batch manifest"
            )
        if run_bundle_payload_sha256(bundle) != member.run_bundle_payload_sha256:
            raise ValueError(
                "batch archive run payload digest does not match the batch manifest"
            )
        experiments.append(bundle.experiment)
    return tuple(experiments)


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def serialize_combine_archive(
    experiment: TransportExperiment,
    runs: tuple[SimulationRunBundle, ...] = (),
) -> bytes:
    """Serialize one deterministic OMEX archive without changing scientific content."""

    if not isinstance(experiment, TransportExperiment):
        raise TypeError("experiment must be a TransportExperiment")
    if not isinstance(runs, tuple) or not all(
        isinstance(bundle, SimulationRunBundle) for bundle in runs
    ):
        raise TypeError("runs must be a tuple of SimulationRunBundle objects")
    for bundle in runs:
        if bundle.experiment != experiment:
            raise ValueError("every run bundle must contain the exact archived experiment")

    members: list[tuple[str, bytes]] = [
        (MANIFEST_NAME, _manifest_bytes(len(runs))),
        (README_NAME, _readme_bytes(experiment, runs)),
        (EXPERIMENT_NAME, serialize_experiment_document(experiment).encode("utf-8")),
    ]
    members.extend(
        (f"runs/run-{index:03d}.json", serialize_run_bundle(bundle))
        for index, bundle in enumerate(runs, start=1)
    )
    members.sort(key=lambda item: item[0])

    output = BytesIO()
    with zipfile.ZipFile(output, mode="w", allowZip64=False) as archive:
        for name, data in members:
            archive.writestr(_zip_info(name), data)
    return output.getvalue()


def serialize_batch_combine_archive(
    manifest: ExperimentBatchManifest,
    runs: tuple[SimulationRunBundle, ...],
) -> bytes:
    """Serialize one completed batch as deterministic OMEX without solver execution."""

    experiments = _validate_batch_inputs(manifest, runs)
    members: list[tuple[str, bytes]] = [
        (MANIFEST_NAME, _batch_manifest_bytes(len(runs))),
        (README_NAME, _batch_readme_bytes(manifest, experiments)),
        (BATCH_MANIFEST_NAME, serialize_batch_manifest(manifest).encode("utf-8")),
    ]
    for member, experiment, bundle in zip(manifest.members, experiments, runs):
        index = member.index
        members.append(
            (
                f"experiments/member-{index:03d}.json",
                serialize_experiment_document(experiment).encode("utf-8"),
            )
        )
        members.append(
            (
                f"runs/member-{index:03d}.run.json",
                serialize_run_bundle(bundle),
            )
        )
    members.sort(key=lambda item: item[0])

    output = BytesIO()
    with zipfile.ZipFile(output, mode="w", allowZip64=False) as archive:
        for name, data in members:
            archive.writestr(_zip_info(name), data)
    return output.getvalue()


def write_batch_combine_archive(
    path: Path,
    manifest: ExperimentBatchManifest,
    runs: tuple[SimulationRunBundle, ...],
) -> Path:
    output = Path(path)
    if output.exists() and output.is_dir():
        raise ValueError("COMBINE batch archive output path must be a file")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = serialize_batch_combine_archive(manifest, runs)
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


def write_combine_archive(
    path: Path,
    experiment: TransportExperiment,
    runs: tuple[SimulationRunBundle, ...] = (),
) -> Path:
    output = Path(path)
    if output.exists() and output.is_dir():
        raise ValueError("COMBINE archive output path must be a file")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = serialize_combine_archive(experiment, runs)
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


def _parse_manifest_entries(
    manifest_data: bytes,
    member_names: tuple[str, ...],
) -> dict[str, tuple[str, str | None]]:
    try:
        root = ElementTree.fromstring(manifest_data)
    except ElementTree.ParseError as exc:
        raise ValueError("COMBINE archive manifest is malformed XML") from exc

    expected_tag = f"{{{OMEX_MANIFEST_NAMESPACE}}}omexManifest"
    if root.tag != expected_tag:
        raise ValueError("unsupported COMBINE archive manifest namespace")

    content_tag = f"{{{OMEX_MANIFEST_NAMESPACE}}}content"
    entries: dict[str, tuple[str, str | None]] = {}
    for child in root:
        if child.tag != content_tag:
            raise ValueError("COMBINE archive manifest contains an unsupported element")
        location = child.attrib.get("location")
        format_uri = child.attrib.get("format")
        if not location or not format_uri:
            raise ValueError("COMBINE archive manifest content is missing location/format")
        normalized = location[2:] if location.startswith("./") else location
        if normalized in entries:
            raise ValueError("COMBINE archive manifest contains duplicate locations")
        entries[normalized] = (format_uri, child.attrib.get("master"))

    if entries.get(".") != (OMEX_NAMESPACE, None):
        raise ValueError("COMBINE archive manifest must declare the archive itself")
    if MANIFEST_NAME not in entries:
        raise ValueError("COMBINE archive manifest does not declare manifest.xml")
    if entries[MANIFEST_NAME][0] != OMEX_MANIFEST_NAMESPACE:
        raise ValueError("manifest.xml has an incompatible COMBINE format")
    if README_NAME not in entries:
        raise ValueError("COMBINE archive manifest does not declare README.md")

    for name in member_names:
        if name not in entries:
            raise ValueError(f"archive member is not declared in manifest: {name}")
    for location in entries:
        if location == ".":
            continue
        if not _member_name_is_safe(location):
            raise ValueError("COMBINE archive manifest contains an unsafe location")
        if location not in member_names:
            raise ValueError(f"COMBINE archive manifest declares missing member: {location}")
    return entries


def _validate_manifest(manifest_data: bytes, member_names: tuple[str, ...]) -> None:
    entries = _parse_manifest_entries(manifest_data, member_names)
    if entries.get(EXPERIMENT_NAME) != (JSON_MEDIA_TYPE_URI, "true"):
        raise ValueError("experiment.json must be the master JSON resource")


def _validate_batch_manifest_entries(
    manifest_data: bytes,
    member_names: tuple[str, ...],
) -> None:
    entries = _parse_manifest_entries(manifest_data, member_names)
    if entries.get(BATCH_MANIFEST_NAME) != (JSON_MEDIA_TYPE_URI, "true"):
        raise ValueError("batch-manifest.json must be the master JSON resource")


def _open_validated_archive(data: bytes) -> zipfile.ZipFile:
    if not isinstance(data, bytes):
        raise TypeError("COMBINE archive data must be bytes")
    try:
        archive = zipfile.ZipFile(BytesIO(data), mode="r")
    except zipfile.BadZipFile as exc:
        raise ValueError("COMBINE archive is not a valid ZIP container") from exc

    infos = archive.infolist()
    try:
        if len(infos) > _MAX_ARCHIVE_MEMBERS:
            raise ValueError("COMBINE archive contains too many members")
        if any(info.is_dir() for info in infos):
            raise ValueError("COMBINE archive must not contain directory entries")
        if any(info.flag_bits & 0x1 for info in infos):
            raise ValueError("encrypted COMBINE archive members are not supported")
        if any(info.file_size > _MAX_MEMBER_UNCOMPRESSED_BYTES for info in infos):
            raise ValueError("COMBINE archive member exceeds the size limit")
        if sum(info.file_size for info in infos) > _MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ValueError("COMBINE archive exceeds the total uncompressed size limit")
        names = tuple(info.filename for info in infos)
        if len(names) != len(set(names)):
            raise ValueError("COMBINE archive contains duplicate member names")
        if not all(_member_name_is_safe(name) for name in names):
            raise ValueError("COMBINE archive contains an unsafe member path")
        if MANIFEST_NAME not in names:
            raise ValueError("COMBINE archive is missing manifest.xml")
    except Exception:
        archive.close()
        raise
    return archive

def combine_archive_project_type(data: bytes) -> str:
    """Return the VesicleScope project kind without executing or deserializing payloads."""

    with _open_validated_archive(data) as archive:
        names = set(info.filename for info in archive.infolist())
        has_experiment = EXPERIMENT_NAME in names
        has_batch = BATCH_MANIFEST_NAME in names
        if has_experiment == has_batch:
            raise ValueError(
                "COMBINE archive must contain exactly one VesicleScope master project type"
            )
        return "batch" if has_batch else "experiment"


def deserialize_any_combine_archive(
    data: bytes,
) -> CombineArchiveProject | CombineBatchArchiveProject:
    kind = combine_archive_project_type(data)
    if kind == "batch":
        return deserialize_batch_combine_archive(data)
    return deserialize_combine_archive(data)


def deserialize_combine_archive(data: bytes) -> CombineArchiveProject:
    """Read and validate one VesicleScope COMBINE archive without solver execution."""

    with _open_validated_archive(data) as archive:
        names = tuple(info.filename for info in archive.infolist())
        if EXPERIMENT_NAME not in names:
            raise ValueError("COMBINE archive is missing experiment.json")

        _validate_manifest(archive.read(MANIFEST_NAME), names)
        try:
            experiment_text = archive.read(EXPERIMENT_NAME).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("archived experiment.json must be UTF-8") from exc
        experiment = deserialize_experiment_document(experiment_text)

        run_names = tuple(
            sorted(
                name
                for name in names
                if name.startswith("runs/") and name.endswith(".json")
            )
        )
        runs = tuple(deserialize_run_bundle(archive.read(name)) for name in run_names)
        for bundle in runs:
            if bundle.experiment != experiment:
                raise ValueError("archived run bundle does not contain the archived experiment")
        return CombineArchiveProject(experiment=experiment, runs=runs)


def deserialize_batch_combine_archive(data: bytes) -> CombineBatchArchiveProject:
    """Read and validate a completed VesicleScope batch OMEX without execution."""

    with _open_validated_archive(data) as archive:
        names = tuple(info.filename for info in archive.infolist())
        if BATCH_MANIFEST_NAME not in names:
            raise ValueError("COMBINE batch archive is missing batch-manifest.json")
        _validate_batch_manifest_entries(archive.read(MANIFEST_NAME), names)
        try:
            manifest_document = archive.read(BATCH_MANIFEST_NAME).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("archived batch-manifest.json must be UTF-8") from exc
        manifest = deserialize_batch_manifest(manifest_document)

        expected_experiment_names = tuple(
            f"experiments/member-{member.index:03d}.json"
            for member in manifest.members
        )
        expected_run_names = tuple(
            f"runs/member-{member.index:03d}.run.json"
            for member in manifest.members
        )
        actual_experiment_names = tuple(
            sorted(
                name
                for name in names
                if name.startswith("experiments/") and name.endswith(".json")
            )
        )
        actual_run_names = tuple(
            sorted(
                name
                for name in names
                if name.startswith("runs/") and name.endswith(".run.json")
            )
        )
        if actual_experiment_names != expected_experiment_names:
            raise ValueError("COMBINE batch archive experiment members do not match manifest")
        if actual_run_names != expected_run_names:
            raise ValueError("COMBINE batch archive run members do not match manifest")

        experiments: list[TransportExperiment] = []
        runs: list[SimulationRunBundle] = []
        for member, experiment_name, run_name in zip(
            manifest.members,
            expected_experiment_names,
            expected_run_names,
        ):
            try:
                experiment_document = archive.read(experiment_name).decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("archived batch experiment must be UTF-8") from exc
            experiment = deserialize_experiment_document(experiment_document)
            bundle = deserialize_run_bundle(archive.read(run_name))
            if experiment.experiment_id != member.experiment_id:
                raise ValueError(
                    "archived batch experiment_id does not match batch manifest"
                )
            if bundle.experiment != experiment:
                raise ValueError(
                    "archived batch run does not contain its archived experiment"
                )
            experiments.append(experiment)
            runs.append(bundle)

        validated_experiments = _validate_batch_inputs(manifest, tuple(runs))
        if tuple(experiments) != validated_experiments:
            raise ValueError("archived batch experiment documents do not match run bundles")
        return CombineBatchArchiveProject(
            manifest=manifest,
            experiments=tuple(experiments),
            runs=tuple(runs),
        )


def read_any_combine_archive(
    path: Path,
) -> CombineArchiveProject | CombineBatchArchiveProject:
    source = Path(path)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read COMBINE archive: {source}") from exc
    return deserialize_any_combine_archive(data)


def read_batch_combine_archive(path: Path) -> CombineBatchArchiveProject:
    source = Path(path)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read COMBINE batch archive: {source}") from exc
    return deserialize_batch_combine_archive(data)


def read_combine_archive(path: Path) -> CombineArchiveProject:
    source = Path(path)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read COMBINE archive: {source}") from exc
    return deserialize_combine_archive(data)
