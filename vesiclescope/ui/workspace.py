"""Filesystem-confined local workspace for experiments and completed runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from vesiclescope.combine_archive import (
    deserialize_combine_archive,
    serialize_combine_archive,
    serialize_batch_combine_archive,
    deserialize_batch_combine_archive,
)
from vesiclescope.experiment_editing import derive_synthetic_experiment
from vesiclescope.experiment_files import (
    deserialize_experiment_document,
    read_experiment_document,
    serialize_experiment_document,
    write_experiment_document,
)
from vesiclescope.measurement_files import (
    deserialize_measurement_document,
    read_measurement_document,
    serialize_measurement_document,
)
from vesiclescope.perturbation_files import (
    deserialize_perturbation_document,
    serialize_perturbation_document,
)
from vesiclescope.population_run_bundles import (
    deserialize_population_run_bundle,
    read_population_run_bundle,
    serialize_population_run_bundle,
    write_population_run_bundle,
)
from vesiclescope.run_bundles import (read_run_bundle, write_run_bundle,
    serialize_run_bundle, run_bundle_payload_sha256)
from vesiclescope.scenarios import diffusion_uptake_factor_conditions
from vesiclescope.engines import BioFVMNumerics
from vesiclescope.workflows import (
    PopulationTransportSpec,
    resolve_perturbation_transport,
    run_external_experiment,
    run_population_transport,
)


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

    @property
    def measurements_dir(self) -> Path:
        return self.root / "measurements"

    @property
    def perturbations_dir(self) -> Path:
        return self.root / "perturbations"

    @property
    def population_runs_dir(self) -> Path:
        return self.root / "population-runs"

    def initialize(self) -> "Workspace":
        for directory in (
            self.experiments_dir,
            self.runs_dir,
            self.measurements_dir,
            self.perturbations_dir,
            self.population_runs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
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

    def measurement_path(self, name: str) -> Path:
        return self._safe_path(self.measurements_dir, name)

    def perturbation_path(self, name: str) -> Path:
        return self._safe_path(self.perturbations_dir, name)

    def population_run_path(self, name: str) -> Path:
        return self._safe_path(self.population_runs_dir, name)

    def list_experiment_names(self) -> tuple[str, ...]:
        self.initialize()
        return tuple(sorted(path.name for path in self.experiments_dir.glob("*.json")))

    def list_run_names(self) -> tuple[str, ...]:
        self.initialize()
        return tuple(sorted(path.name for path in self.runs_dir.glob("*.json")))

    def list_measurement_names(self) -> tuple[str, ...]:
        self.initialize()
        return tuple(sorted(path.name for path in self.measurements_dir.glob("*.json")))

    def list_perturbation_names(self) -> tuple[str, ...]:
        self.initialize()
        return tuple(sorted(path.name for path in self.perturbations_dir.glob("*.json")))

    def list_population_run_names(self) -> tuple[str, ...]:
        self.initialize()
        return tuple(sorted(path.name for path in self.population_runs_dir.glob("*.json")))

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



    def import_measurement(self, name: str, document: str) -> Path:
        self.initialize()
        output = self.measurement_path(name)
        if output.exists():
            raise ValueError(f"measurement dataset already exists: {name}")
        dataset = deserialize_measurement_document(document)
        output.write_text(
            serialize_measurement_document(dataset),
            encoding="utf-8",
            newline="\n",
        )
        return output

    def import_perturbation(self, name: str, document: str) -> Path:
        self.initialize()
        output = self.perturbation_path(name)
        if output.exists():
            raise ValueError(f"perturbation study already exists: {name}")
        study = deserialize_perturbation_document(document)
        output.write_text(
            serialize_perturbation_document(study),
            encoding="utf-8",
            newline="\n",
        )
        return output

    def import_population_run(self, name: str, document: bytes | str) -> Path:
        self.initialize()
        output = self.population_run_path(name)
        if output.exists():
            raise ValueError(f"population run already exists: {name}")
        run = deserialize_population_run_bundle(document)
        output.write_bytes(serialize_population_run_bundle(run))
        return output

    def read_measurement(self, name: str):
        return read_measurement_document(self.measurement_path(name))

    def read_perturbation(self, name: str):
        path = self.perturbation_path(name)
        try:
            document = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"cannot read perturbation document: {path}") from exc
        return deserialize_perturbation_document(document)

    def read_population_run(self, name: str):
        return read_population_run_bundle(self.population_run_path(name))

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

    def export_batch_archive(self, run_names: tuple[str, ...]) -> bytes:
        """Package an explicit ordered selection, without rerunning simulations."""
        if not isinstance(run_names, tuple) or not run_names:
            raise ValueError("select at least one completed run for batch export")
        if len(run_names) != len(set(run_names)):
            raise ValueError("batch selection contains duplicate run names")
        runs = tuple(self.read_run(name) for name in run_names)
        manifest = {
            "schema": "vesiclescope.experiment-batch",
            "version": 1,
            "scientific_status": "explicit input batch; no sampling or biological distribution implied",
            "vesiclescope_revision": runs[0].vesiclescope_revision,
            "numerics": {
                "grid_spacing_micron": runs[0].numerics.grid_spacing_micron,
                "time_step_min": runs[0].numerics.time_step_min,
            },
            "members": [
                {
                    "index": index,
                    "input_filename": f"member-{index:03d}.json",
                    "experiment_id": run.experiment.experiment_id,
                    "run_filename": f"member-{index:03d}.run.json",
                    "run_bundle_payload_sha256": run_bundle_payload_sha256(run),
                }
                for index, run in enumerate(runs, 1)
            ],
        }
        return serialize_batch_combine_archive(
            manifest, tuple(run.experiment for run in runs), runs,
        )

    def import_batch_archive(self, data: bytes) -> dict[str, object]:
        """Validate before writing and roll back every newly created batch artifact."""
        project = deserialize_batch_combine_archive(data)
        self.initialize()
        reserved: dict[Path, set[str]] = {
            self.experiments_dir: set(), self.runs_dir: set(),
        }
        def reserve(directory: Path, stem: str) -> Path:
            safe_stem = self._safe_import_stem(stem)
            name = f"{safe_stem}.json"
            suffix = 2
            while name in reserved[directory] or self._safe_path(directory, name).exists():
                name = f"{safe_stem}-{suffix}.json"
                suffix += 1
            reserved[directory].add(name)
            return self._safe_path(directory, name)

        experiments = []
        runs = []
        artifacts = []
        for index, (experiment, run) in enumerate(zip(project.experiments, project.runs), 1):
            experiment_path = reserve(self.experiments_dir, f"imported-{experiment.experiment_id}")
            run_path = reserve(self.runs_dir, f"imported-{experiment.experiment_id}-run-{index:03d}")
            experiments.append(experiment_path.name)
            runs.append(run_path.name)
            artifacts.extend([
                (experiment_path, serialize_experiment_document(experiment).encode("utf-8")),
                (run_path, serialize_run_bundle(run)),
            ])
        created = []
        try:
            for path, payload in artifacts:
                with path.open("xb") as handle:
                    created.append(path)
                    handle.write(payload)
        except Exception:
            for path in reversed(created):
                path.unlink(missing_ok=True)
            raise
        return {"project_type": "experiment-batch", "experiments": experiments, "runs": runs}

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

    def execute_population_study(
        self,
        *,
        perturbation_name: str,
        population_experiments: dict[str, str],
        run_name: str,
        runner: Path,
        revision: str,
        grid_spacing_micron: float,
        time_step_min: float,
    ) -> Path:
        self.initialize()
        if not isinstance(population_experiments, dict) or not population_experiments:
            raise ValueError(
                "population_experiments must map at least one phenotype to an experiment"
            )
        if not all(
            isinstance(phenotype_id, str)
            and phenotype_id.strip()
            and isinstance(experiment_name, str)
            and experiment_name.strip()
            for phenotype_id, experiment_name in population_experiments.items()
        ):
            raise ValueError(
                "population_experiments must contain non-blank phenotype and experiment names"
            )

        output = self.population_run_path(run_name)
        if output.exists():
            raise ValueError(f"population run already exists: {run_name}")

        study = self.read_perturbation(perturbation_name)
        declared = {item.identifier for item in study.phenotypes}
        unknown = sorted(set(population_experiments) - declared)
        if unknown:
            raise ValueError(
                "population mapping references unknown study phenotypes: "
                + ", ".join(unknown)
            )

        selected_experiments = {
            phenotype_id: self.read_experiment(experiment_name)
            for phenotype_id, experiment_name in population_experiments.items()
        }
        if study.transport_experiment_ids:
            declared_experiment_ids = set(study.transport_experiment_ids)
            mismatched = sorted(
                experiment.experiment_id
                for experiment in selected_experiments.values()
                if experiment.experiment_id not in declared_experiment_ids
            )
            if mismatched:
                raise ValueError(
                    "population mapping uses transport experiments not declared "
                    "by the perturbation study: "
                    + ", ".join(mismatched)
                )

        specs = tuple(
            PopulationTransportSpec(
                phenotype_id=phenotype.identifier,
                experiment=selected_experiments[phenotype.identifier],
            )
            for phenotype in study.phenotypes
            if phenotype.identifier in selected_experiments
        )
        resolved = resolve_perturbation_transport(study, specs)
        completed = run_population_transport(
            resolved,
            BioFVMNumerics(
                grid_spacing_micron=grid_spacing_micron,
                time_step_min=time_step_min,
            ),
            runner,
            revision,
        )
        return write_population_run_bundle(output, completed)

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
