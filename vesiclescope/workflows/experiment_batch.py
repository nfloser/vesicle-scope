"""Deterministic batch execution for explicit external experiment documents."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from vesiclescope.batch_manifests import (
    ExperimentBatchManifest,
    ExperimentBatchManifestMember,
    write_batch_manifest,
)
from vesiclescope.experiment_files import read_experiment_document
from vesiclescope.run_bundles import run_bundle_payload_sha256
from .external_experiment import ExternalExperimentRunResult, run_external_experiment


_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True, slots=True)
class ExperimentBatchMember:
    input_path: Path
    experiment_id: str
    output_filename: str


@dataclass(frozen=True, slots=True)
class ExperimentBatchResult:
    manifest_path: Path
    run_paths: tuple[Path, ...]


def _safe_output_filename(index: int, experiment_id: str) -> str:
    component = _SAFE_COMPONENT_RE.sub("-", experiment_id).strip(".-_")
    if not component:
        component = "experiment"
    if len(component) > 80:
        digest = hashlib.sha256(experiment_id.encode("utf-8")).hexdigest()[:12]
        component = f"{component[:64].rstrip('.-_')}-{digest}"
    return f"{index:03d}-{component}.run.json"


def _prepare_members(
    experiment_paths: tuple[Path, ...],
) -> tuple[ExperimentBatchMember, ...]:
    if not isinstance(experiment_paths, tuple):
        raise TypeError("experiment_paths must be a tuple")
    if not experiment_paths:
        raise ValueError("experiment batch requires at least one experiment document")

    members: list[ExperimentBatchMember] = []
    seen_ids: set[str] = set()
    for index, supplied_path in enumerate(experiment_paths, start=1):
        path = Path(supplied_path)
        experiment = read_experiment_document(path)
        if experiment.experiment_id in seen_ids:
            raise ValueError(
                f"experiment batch contains duplicate experiment_id: "
                f"{experiment.experiment_id}"
            )
        seen_ids.add(experiment.experiment_id)
        members.append(
            ExperimentBatchMember(
                input_path=path,
                experiment_id=experiment.experiment_id,
                output_filename=_safe_output_filename(index, experiment.experiment_id),
            )
        )
    return tuple(members)


def run_experiment_batch(
    *,
    experiment_paths: tuple[Path, ...],
    runner: Path,
    revision: str,
    output_dir: Path,
    grid_spacing_micron: float,
    time_step_min: float,
) -> ExperimentBatchResult:
    """Execute an explicit ordered experiment set and persist an audit manifest."""

    members = _prepare_members(experiment_paths)
    runner = Path(runner)
    if not runner.is_file():
        raise ValueError(f"native runner does not exist: {runner}")

    output_dir = Path(output_dir)
    manifest_path = output_dir / "batch-manifest.json"
    target_paths = tuple(output_dir / member.output_filename for member in members)

    if manifest_path.exists():
        raise ValueError(f"batch manifest already exists: {manifest_path}")
    collisions = tuple(path for path in target_paths if path.exists())
    if collisions:
        raise ValueError(f"batch output already exists: {collisions[0]}")

    output_dir.mkdir(parents=True, exist_ok=True)

    completed: list[tuple[ExperimentBatchMember, ExternalExperimentRunResult]] = []
    for member, target in zip(members, target_paths):
        completed.append(
            (
                member,
                run_external_experiment(
                    experiment_path=member.input_path,
                    runner=runner,
                    revision=revision,
                    output_path=target,
                    grid_spacing_micron=grid_spacing_micron,
                    time_step_min=time_step_min,
                ),
            )
        )

    normalized_revision = completed[0][1].bundle.vesiclescope_revision
    manifest = ExperimentBatchManifest(
        vesiclescope_revision=normalized_revision,
        numerics=completed[0][1].bundle.numerics,
        members=tuple(
            ExperimentBatchManifestMember(
                index=index,
                input_filename=member.input_path.name,
                experiment_id=member.experiment_id,
                run_filename=result.bundle_path.name,
                run_bundle_payload_sha256=run_bundle_payload_sha256(result.bundle),
            )
            for index, (member, result) in enumerate(completed, start=1)
        ),
    )
    write_batch_manifest(manifest_path, manifest)
    return ExperimentBatchResult(
        manifest_path=manifest_path,
        run_paths=tuple(result.bundle_path for _, result in completed),
    )
