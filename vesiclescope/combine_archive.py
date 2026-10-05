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
import zipfile

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
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True, slots=True)
class CombineArchiveProject:
    """Validated VesicleScope content recovered from one OMEX archive."""

    experiment: TransportExperiment
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


def write_combine_archive(
    path: Path,
    experiment: TransportExperiment,
    runs: tuple[SimulationRunBundle, ...] = (),
) -> Path:
    output = Path(path)
    if output.exists() and output.is_dir():
        raise ValueError("COMBINE archive output path must be a file")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(serialize_combine_archive(experiment, runs))
    return output


def _validate_manifest(manifest_data: bytes, member_names: tuple[str, ...]) -> None:
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
    if entries.get(EXPERIMENT_NAME) != (JSON_MEDIA_TYPE_URI, "true"):
        raise ValueError("experiment.json must be the master JSON resource")
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


def deserialize_combine_archive(data: bytes) -> CombineArchiveProject:
    """Read and validate one VesicleScope COMBINE archive without solver execution."""

    if not isinstance(data, bytes):
        raise TypeError("COMBINE archive data must be bytes")
    try:
        archive = zipfile.ZipFile(BytesIO(data), mode="r")
    except zipfile.BadZipFile as exc:
        raise ValueError("COMBINE archive is not a valid ZIP container") from exc

    with archive:
        names = tuple(info.filename for info in archive.infolist())
        if len(names) != len(set(names)):
            raise ValueError("COMBINE archive contains duplicate member names")
        if not all(_member_name_is_safe(name) for name in names):
            raise ValueError("COMBINE archive contains an unsafe member path")
        if MANIFEST_NAME not in names:
            raise ValueError("COMBINE archive is missing manifest.xml")
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


def read_combine_archive(path: Path) -> CombineArchiveProject:
    source = Path(path)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read COMBINE archive: {source}") from exc
    return deserialize_combine_archive(data)
