"""Verified installation/build support for the pinned BioFVM transport engine."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
import os
import re
import shutil
import subprocess

from vesiclescope.engines.biofvm import BioFVMEngineMetadata, pinned_engine_metadata


PHYSICELL_UPSTREAM = "https://github.com/MathCancer/PhysiCell.git"
_BIOFVM_VERSION_RE = re.compile(r'BioFVM_Version\s*=\s*"([^"]+)"')


@dataclass(frozen=True, slots=True)
class EngineSetupStatus:
    metadata: BioFVMEngineMetadata
    git_path: str | None
    compiler_path: str | None
    default_physicell_dir: Path
    default_runner_path: Path
    runner_exists: bool


def _is_windows() -> bool:
    return os.name == "nt"


def default_cache_root() -> Path:
    override = os.environ.get("VESICLESCOPE_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    if _is_windows():
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "VesicleScope" / "Cache"
    return Path.home() / ".cache" / "vesiclescope"


def default_physicell_dir(metadata: BioFVMEngineMetadata | None = None) -> Path:
    metadata = metadata or pinned_engine_metadata()
    return default_cache_root() / "physicell" / metadata.physicell_commit


def default_runner_path(metadata: BioFVMEngineMetadata | None = None) -> Path:
    metadata = metadata or pinned_engine_metadata()
    filename = "biofvm_transport_runner.exe" if _is_windows() else "biofvm_transport_runner"
    return default_cache_root() / "engines" / metadata.physicell_commit / filename


def engine_setup_status() -> EngineSetupStatus:
    metadata = pinned_engine_metadata()
    runner = default_runner_path(metadata)
    return EngineSetupStatus(
        metadata=metadata,
        git_path=shutil.which("git"),
        compiler_path=shutil.which("g++"),
        default_physicell_dir=default_physicell_dir(metadata),
        default_runner_path=runner,
        runner_exists=runner.is_file(),
    )


def _run_checked(command: list[str], *, description: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"{description} requires executable: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(f"{description} failed{suffix}") from exc


def _reported_biofvm_version(physicell_dir: Path) -> str:
    source = physicell_dir / "BioFVM" / "BioFVM_MultiCellDS.cpp"
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read BioFVM version source: {source}") from exc
    match = _BIOFVM_VERSION_RE.search(text)
    if match is None:
        raise ValueError(f"cannot determine BioFVM version from: {source}")
    return match.group(1)


def verify_physicell_checkout(
    physicell_dir: Path,
    metadata: BioFVMEngineMetadata | None = None,
) -> BioFVMEngineMetadata:
    metadata = metadata or pinned_engine_metadata()
    checkout = Path(physicell_dir)
    if not (checkout / ".git").is_dir():
        raise ValueError(f"PhysiCell checkout is not a git repository: {checkout}")

    result = _run_checked(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        description="PhysiCell commit verification",
    )
    actual_commit = result.stdout.strip()
    if actual_commit != metadata.physicell_commit:
        raise ValueError(
            "PhysiCell checkout commit does not match the reviewed pin: "
            f"{actual_commit or '<missing>'} != {metadata.physicell_commit}"
        )

    actual_version = _reported_biofvm_version(checkout)
    if actual_version != metadata.biofvm_version:
        raise ValueError(
            "BioFVM source version does not match the reviewed pin: "
            f"{actual_version} != {metadata.biofvm_version}"
        )
    return metadata


def fetch_physicell(
    target: Path,
    metadata: BioFVMEngineMetadata | None = None,
) -> Path:
    metadata = metadata or pinned_engine_metadata()
    target = Path(target)

    if (target / ".git").is_dir():
        verify_physicell_checkout(target, metadata)
        return target
    if target.exists():
        raise ValueError(f"refusing to overwrite existing non-git path: {target}")

    if shutil.which("git") is None:
        raise RuntimeError("PhysiCell fetch requires git on PATH")

    target.parent.mkdir(parents=True, exist_ok=True)
    _run_checked(
        [
            "git",
            "clone",
            "--quiet",
            "--depth",
            "1",
            "--branch",
            metadata.physicell_release,
            PHYSICELL_UPSTREAM,
            str(target),
        ],
        description="PhysiCell fetch",
    )
    verify_physicell_checkout(target, metadata)
    return target


def _runner_source_resource():
    return resources.files("vesiclescope.engines.native").joinpath("transport_runner.cpp")


def _compile_command(
    *,
    compiler: str,
    runner_source: Path,
    physicell_dir: Path,
    output_path: Path,
    metadata: BioFVMEngineMetadata,
) -> list[str]:
    biofvm = physicell_dir / "BioFVM"
    core_sources = [
        "BioFVM_vector.cpp",
        "BioFVM_mesh.cpp",
        "BioFVM_microenvironment.cpp",
        "BioFVM_solvers.cpp",
        "BioFVM_utilities.cpp",
        "BioFVM_basic_agent.cpp",
        "BioFVM_agent_container.cpp",
    ]
    return [
        compiler,
        "-O2",
        "-std=c++11",
        "-fopenmp",
        "-Wall",
        "-Wextra",
        "-Wpedantic",
        "-ffunction-sections",
        "-fdata-sections",
        f'-DVESICLESCOPE_PHYSICELL_RELEASE="{metadata.physicell_release}"',
        f'-DVESICLESCOPE_PHYSICELL_COMMIT="{metadata.physicell_commit}"',
        f'-DVESICLESCOPE_BIOFVM_VERSION="{metadata.biofvm_version}"',
        f"-I{biofvm}",
        str(runner_source),
        *(str(biofvm / name) for name in core_sources),
        "-Wl,--gc-sections",
        "-o",
        str(output_path),
    ]


def build_biofvm_runner(
    *,
    physicell_dir: Path | None = None,
    output_path: Path | None = None,
    fetch_if_missing: bool = True,
) -> Path:
    metadata = pinned_engine_metadata()
    compiler = shutil.which("g++")
    if compiler is None:
        raise RuntimeError("BioFVM runner build requires g++ on PATH")

    checkout = Path(physicell_dir) if physicell_dir is not None else default_physicell_dir(metadata)
    if (checkout / ".git").is_dir():
        verify_physicell_checkout(checkout, metadata)
    elif fetch_if_missing:
        fetch_physicell(checkout, metadata)
    else:
        raise ValueError(f"verified PhysiCell checkout does not exist: {checkout}")

    target = Path(output_path) if output_path is not None else default_runner_path(metadata)
    target.parent.mkdir(parents=True, exist_ok=True)

    with resources.as_file(_runner_source_resource()) as runner_source:
        command = _compile_command(
            compiler=compiler,
            runner_source=Path(runner_source),
            physicell_dir=checkout,
            output_path=target,
            metadata=metadata,
        )
        _run_checked(command, description="BioFVM transport runner build")
    if not target.is_file():
        raise RuntimeError(f"compiler completed without producing runner: {target}")
    return target
