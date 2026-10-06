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
import json
import tempfile
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
_MAX_ARCHIVE_MEMBERS = 1024
_MAX_MEMBER_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
_MAX_TOTAL_UNCOMPRESSED_BYTES = 512 * 1024 * 1024


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


def _validate_manifest(manifest_data: bytes, member_names: tuple[str, ...], master_name: str = EXPERIMENT_NAME) -> None:
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
    if entries.get(master_name) != (JSON_MEDIA_TYPE_URI, "true"):
        raise ValueError(f"{master_name} must be the master JSON resource")
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
        names = _validate_zip_members(archive)
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


def _validate_zip_members(archive: zipfile.ZipFile) -> tuple[str, ...]:
    infos = archive.infolist()
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
    return names


BATCH_MANIFEST_NAME = "batch-manifest.json"


@dataclass(frozen=True, slots=True)
class BatchCombineArchiveProject:
    manifest: dict[str, object]
    experiments: tuple[TransportExperiment, ...]
    runs: tuple[SimulationRunBundle, ...]


def _validate_batch(
    manifest: dict[str, object],
    experiments: tuple[TransportExperiment, ...],
    runs: tuple[SimulationRunBundle, ...],
) -> None:
    if not isinstance(manifest, dict) or manifest.get('schema') != 'vesiclescope.experiment-batch' or type(manifest.get('version')) is not int or manifest['version'] != 1:
        raise ValueError('unsupported experiment batch manifest')
    members = manifest.get('members')
    if not isinstance(members, list) or not members or len(members) != len(experiments) or len(members) != len(runs):
        raise ValueError('batch members must match experiments and runs exactly')
    seen_ids, seen_runs = set(), set()
    for index, (member, experiment, run) in enumerate(zip(members, experiments, runs), 1):
        if not isinstance(member, dict) or type(member.get('index')) is not int or member['index'] != index:
            raise ValueError('batch member index must preserve consecutive input order')
        if member.get('experiment_id') != experiment.experiment_id or run.experiment != experiment:
            raise ValueError('batch experiment identity mismatch')
        if experiment.experiment_id in seen_ids:
            raise ValueError('duplicate batch experiment identity')
        seen_ids.add(experiment.experiment_id)
        for field in ('input_filename', 'run_filename'):
            name = member.get(field)
            if not _member_name_is_safe(name) or '/' in name:
                raise ValueError('batch artifact filenames must be safe basenames')
        if member['run_filename'] in seen_runs:
            raise ValueError('duplicate batch run filename')
        seen_runs.add(member['run_filename'])
        if member.get('run_bundle_payload_sha256') != run_bundle_payload_sha256(run):
            raise ValueError('batch run payload digest mismatch')
        if manifest.get('vesiclescope_revision') != run.vesiclescope_revision or manifest.get('numerics') != {
            'grid_spacing_micron': run.numerics.grid_spacing_micron,
            'time_step_min': run.numerics.time_step_min,
        }:
            raise ValueError('batch revision or numerical settings mismatch')
    if not isinstance(manifest.get('scientific_status'), str) or not manifest['scientific_status'].strip():
        raise ValueError('batch scientific status is required')


def serialize_batch_combine_archive(
    manifest: dict[str, object],
    experiments: tuple[TransportExperiment, ...],
    runs: tuple[SimulationRunBundle, ...],
) -> bytes:
    """Package a completed explicit batch without executing its solver."""
    _validate_batch(manifest, experiments, runs)
    # Rewrite source filenames to stable embedded paths; retain all other audit data.
    embedded = dict(manifest)
    embedded['members'] = [dict(member, input_filename=f'member-{i:03d}.json',
                                run_filename=f'member-{i:03d}.run.json')
                           for i, member in enumerate(manifest['members'], 1)]
    members = [(BATCH_MANIFEST_NAME, (json.dumps(embedded, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2)+'\n').encode()),
               (README_NAME, b'# VesicleScope explicit batch\n\nMember order follows batch-manifest.json. No sampling or biological distribution is implied.\nVesicleScope-native experiments and runs preserve provenance and solver identity.\nSimulation outputs are not experimental evidence. SED-ML compatibility is not claimed.\n')]
    for i, (experiment, run) in enumerate(zip(experiments, runs), 1):
        members.extend([(f'experiments/member-{i:03d}.json', serialize_experiment_document(experiment).encode()),
                        (f'runs/member-{i:03d}.run.json', serialize_run_bundle(run))])
    root = ElementTree.Element('omexManifest', xmlns=OMEX_MANIFEST_NAMESPACE)
    for name, format_uri in [('.', OMEX_NAMESPACE), (MANIFEST_NAME, OMEX_MANIFEST_NAMESPACE),
                            *[(n, MARKDOWN_MEDIA_TYPE_URI if n == README_NAME else JSON_MEDIA_TYPE_URI) for n, _ in members]]:
        attributes = dict(location='.' if name == '.' else './'+name, format=format_uri)
        if name == BATCH_MANIFEST_NAME:
            attributes['master'] = 'true'
        ElementTree.SubElement(root, 'content', attributes)
    members.append((MANIFEST_NAME, ElementTree.tostring(root, encoding='utf-8', xml_declaration=True)))
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', allowZip64=False) as archive:
        for name, payload in sorted(members):
            archive.writestr(_zip_info(name), payload)
    data = output.getvalue()
    deserialize_batch_combine_archive(data)  # enforce reader limits on generated archives
    return data


def deserialize_batch_combine_archive(data: bytes) -> BatchCombineArchiveProject:
    if not isinstance(data, bytes):
        raise TypeError('COMBINE archive data must be bytes')
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = _validate_zip_members(archive)
            _validate_manifest(archive.read(MANIFEST_NAME), names, BATCH_MANIFEST_NAME)
            manifest = json.loads(archive.read(BATCH_MANIFEST_NAME))
            if not isinstance(manifest, dict) or not isinstance(manifest.get('members'), list):
                raise ValueError('invalid batch manifest')
            count = len(manifest['members'])
            expected = {MANIFEST_NAME, README_NAME, BATCH_MANIFEST_NAME}
            expected.update(f'experiments/member-{i:03d}.json' for i in range(1, count+1))
            expected.update(f'runs/member-{i:03d}.run.json' for i in range(1, count+1))
            if set(names) != expected:
                raise ValueError('batch archive contains missing or extra members')
            for i, member in enumerate(manifest['members'], 1):
                if not isinstance(member, dict) or member.get('input_filename') != f'member-{i:03d}.json' or member.get('run_filename') != f'member-{i:03d}.run.json':
                    raise ValueError('batch manifest artifact paths do not match ordered members')
            experiments = tuple(deserialize_experiment_document(archive.read(f'experiments/member-{i:03d}.json').decode('utf-8')) for i in range(1, count+1))
            runs = tuple(deserialize_run_bundle(archive.read(f'runs/member-{i:03d}.run.json')) for i in range(1, count+1))
            _validate_batch(manifest, experiments, runs)
            return BatchCombineArchiveProject(manifest, experiments, runs)
    except (zipfile.BadZipFile, KeyError, UnicodeDecodeError) as exc:
        raise ValueError('invalid batch COMBINE archive') from exc


def write_batch_combine_archive(manifest_path: Path, output: Path) -> Path:
    """Resolve completed runs next to their manifest; recover exact input from each run."""
    from vesiclescope.run_bundles import read_run_bundle
    manifest_path, output = Path(manifest_path), Path(output)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(manifest, dict) or not isinstance(manifest.get('members'), list):
        raise ValueError('invalid batch manifest')
    paths = []
    for member in manifest['members']:
        name = member.get('run_filename') if isinstance(member, dict) else None
        if not _member_name_is_safe(name) or '/' in name:
            raise ValueError('batch run filename must be a safe basename')
        path = manifest_path.parent / name
        if path.resolve().parent != manifest_path.parent.resolve():
            raise ValueError('batch run must remain within manifest directory')
        paths.append(path)
    runs = tuple(read_run_bundle(path) for path in paths)
    data = serialize_batch_combine_archive(manifest, tuple(run.experiment for run in runs), runs)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return output


def read_combine_project(path: Path) -> CombineArchiveProject | BatchCombineArchiveProject:
    """Inspect either supported project kind through the same defensive reader."""
    data = Path(path).read_bytes()
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = _validate_zip_members(archive)
    except zipfile.BadZipFile as exc:
        raise ValueError("COMBINE archive is not a valid ZIP container") from exc
    if BATCH_MANIFEST_NAME in names:
        return deserialize_batch_combine_archive(data)
    return deserialize_combine_archive(data)
