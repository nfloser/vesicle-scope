"""Filesystem-confined local workspace for experiments and completed runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from vesiclescope.combine_archive import (
    deserialize_combine_archive,
    serialize_combine_archive,
)
from vesiclescope.experiment_editing import derive_synthetic_experiment
from vesiclescope.experiment_files import (
    deserialize_experiment_document,
    read_experiment_document,
    serialize_experiment_document,
    write_experiment_document,
)
from vesiclescope.run_bundles import read_run_bundle, write_run_bundle
from vesiclescope.scenarios import diffusion_uptake_factor_conditions
from vesiclescope.workflows import run_external_experiment


_SAFE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.json\Z")


@dataclass(frozen=True, slots=True)
class Workspace:
    root: Path

    def __post_init__(self) -> None:
        root = Path(self.root).expanduser().resolve()
        object.__setattr__(self, "root", root)

    @property
    def experiments_dir(self) -> Path:
        return self.root / "experiments"

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    def initialize(self) -> "Workspace":
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        return self

    def _safe_path(self, directory: Path, name: str) -> Path:
        if not isinstance(name, str) or not _SAFE_NAME_RE.fullmatch(name):
            raise ValueError(
                "workspace artifact name must be a simple .json filename "
                "using letters, digits, dot, underscore or hyphen"
            )
        candidate = (directory / name).resolve()
        if candidate.parent != directory.resolve():
            raise ValueError("workspace artifact path escapes its directory")
        return candidate

    def experiment_path(self, name: str) -> Path:
        return self._safe_path(self.experiments_dir, name)

    def run_path(self, name: str) -> Path:
        return self._safe_path(self.runs_dir, name)

    def list_experiment_names(self) -> tuple[str, ...]:
        self.initialize()
        return tuple(sorted(path.name for path in self.experiments_dir.glob("*.json")))

    def list_run_names(self) -> tuple[str, ...]:
        self.initialize()
        return tuple(sorted(path.name for path in self.runs_dir.glob("*.json")))

    def create_baseline_experiment(
        self,
        name: str = "diffusion-uptake-baseline.json",
    ) -> Path:
        self.initialize()
        output = self.experiment_path(name)
        if output.exists():
            raise ValueError(f"experiment already exists: {name}")
        experiment = next(
            condition.experiment
            for condition in diffusion_uptake_factor_conditions()
            if condition.diffusion_factor == 1.0 and condition.uptake_factor == 1.0
        )
        return write_experiment_document(output, experiment)

    def import_experiment(self, name: str, document: str) -> Path:
        self.initialize()
        output = self.experiment_path(name)
        if output.exists():
            raise ValueError(f"experiment already exists: {name}")
        experiment = deserialize_experiment_document(document)
        output.write_text(
            serialize_experiment_document(experiment),
            encoding="utf-8",
            newline="\n",
        )
        return output



    def _safe_import_stem(self, stem: str) -> str:
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("._-")
        if not safe_stem or not safe_stem[0].isalnum():
            safe_stem = "imported"
        return safe_stem[:120].rstrip("._-") or "imported"

    def _available_name(self, directory: Path, stem: str) -> str:
        safe_stem = self._safe_import_stem(stem)
        candidate = f"{safe_stem}.json"
        index = 2
        while self._safe_path(directory, candidate).exists():
            candidate = f"{safe_stem}-{index}.json"
            index += 1
        return candidate

    def export_combine_archive(self, experiment_name: str) -> bytes:
        self.initialize()
        experiment = self.read_experiment(experiment_name)
        runs = []
        for name in self.list_run_names():
            try:
                bundle = self.read_run(name)
            except ValueError:
                continue
            if bundle.experiment == experiment:
                runs.append(bundle)
        return serialize_combine_archive(experiment, tuple(runs))

    def import_combine_archive(self, data: bytes) -> dict[str, object]:
        self.initialize()
        project = deserialize_combine_archive(data)

        experiment_stem = f"imported-{project.experiment.experiment_id}"
        experiment_name = self._available_name(
            self.experiments_dir,
            experiment_stem,
        )

        reserved_run_names: set[str] = set()
        run_names: list[str] = []
        for index, _bundle in enumerate(project.runs, start=1):
            stem = f"imported-{project.experiment.experiment_id}-run-{index:03d}"
            safe_stem = self._safe_import_stem(stem)
            candidate = f"{safe_stem}.json"
            suffix = 2
            while (
                candidate in reserved_run_names
                or self.run_path(candidate).exists()
            ):
                candidate = f"{safe_stem}-{suffix}.json"
                suffix += 1
            reserved_run_names.add(candidate)
            run_names.append(candidate)

        experiment_path = self.experiment_path(experiment_name)
        run_paths = tuple(self.run_path(name) for name in run_names)
        created: list[Path] = []
        try:
            write_experiment_document(experiment_path, project.experiment)
            created.append(experiment_path)
            for path, bundle in zip(run_paths, project.runs):
                write_run_bundle(path, bundle)
                created.append(path)
        except Exception:
            for path in reversed(created):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            raise

        return {
            "experiment": experiment_name,
            "runs": run_names,
        }

    def derive_synthetic_variant(
        self,
        *,
        source_name: str,
        output_name: str,
        experiment_id: str,
        duration_min: float,
        sample_every_min: float,
        diffusion_value: float,
        decay_value: float,
        initial_concentration_value: float,
        release_rates: dict[str, float],
        uptake_rates: dict[str, float],
    ) -> Path:
        self.initialize()
        source = self.read_experiment(source_name)
        output = self.experiment_path(output_name)
        if output.exists():
            raise ValueError(f"experiment already exists: {output_name}")

        derived = derive_synthetic_experiment(
            source,
            experiment_id=experiment_id,
            duration_min=duration_min,
            sample_every_min=sample_every_min,
            diffusion_value=diffusion_value,
            decay_value=decay_value,
            initial_concentration_value=initial_concentration_value,
            release_rates=release_rates,
            uptake_rates=uptake_rates,
        )
        return write_experiment_document(output, derived)

    def read_experiment(self, name: str):
        return read_experiment_document(self.experiment_path(name))

    def read_run(self, name: str):
        return read_run_bundle(self.run_path(name))

    def execute_experiment(
        self,
        *,
        experiment_name: str,
        run_name: str,
        runner: Path,
        revision: str,
        grid_spacing_micron: float,
        time_step_min: float,
    ) -> Path:
        self.initialize()
        experiment_path = self.experiment_path(experiment_name)
        output = self.run_path(run_name)
        if output.exists():
            raise ValueError(f"run already exists: {run_name}")
        result = run_external_experiment(
            experiment_path=experiment_path,
            runner=runner,
            revision=revision,
            output_path=output,
            grid_spacing_micron=grid_spacing_micron,
            time_step_min=time_step_min,
        )
        return result.bundle_path
