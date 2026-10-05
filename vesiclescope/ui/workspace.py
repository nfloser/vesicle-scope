"""Filesystem-confined local workspace for experiments and completed runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from vesiclescope.experiment_files import (
    deserialize_experiment_document,
    read_experiment_document,
    serialize_experiment_document,
    write_experiment_document,
)
from vesiclescope.run_bundles import read_run_bundle
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
