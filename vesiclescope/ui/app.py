"""Application services shared by the local UI and tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from vesiclescope.analysis import compare_run_bundles
from vesiclescope.ui.workspace import Workspace


_REVISION_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")


def _evidence_categories(experiment) -> list[str]:
    return sorted(
        {
            experiment.diffusion.evidence.value,
            experiment.decay.evidence.value,
            experiment.initial_concentration.evidence.value,
            *(source.release_rate.evidence.value for source in experiment.release_sources),
            *(sink.uptake_rate.evidence.value for sink in experiment.uptake_sinks),
        }
    )


def _experiment_summary(experiment) -> dict[str, object]:
    return {
        "experiment_id": experiment.experiment_id,
        "domain": {
            "width_micron": experiment.domain.width_micron,
            "height_micron": experiment.domain.height_micron,
            "slice_thickness_micron": experiment.domain.slice_thickness_micron,
        },
        "duration_min": experiment.duration_min,
        "sample_every_min": experiment.sample_every_min,
        "boundary": experiment.boundary.value,
        "evidence_categories": _evidence_categories(experiment),
        "scientific_status": (
            "synthetic_benchmark"
            if _evidence_categories(experiment) == ["synthetic_benchmark"]
            else "mixed_or_evidence_backed"
        ),
        "diffusion": {
            "value": experiment.diffusion.value,
            "unit": experiment.diffusion.unit,
            "evidence": experiment.diffusion.evidence.value,
        },
        "decay": {
            "value": experiment.decay.value,
            "unit": experiment.decay.unit,
            "evidence": experiment.decay.evidence.value,
        },
        "initial_concentration": {
            "value": experiment.initial_concentration.value,
            "unit": experiment.initial_concentration.unit,
            "evidence": experiment.initial_concentration.evidence.value,
        },
        "release_sources": [
            {
                "identifier": source.identifier,
                "kind": source.__class__.__name__,
                "x_micron": source.x_micron,
                "y_micron": source.y_micron,
                "radius_micron": getattr(source, "footprint_radius_micron", 0.0),
                "rate": source.release_rate.value,
                "rate_unit": source.release_rate.unit,
                "evidence": source.release_rate.evidence.value,
            }
            for source in experiment.release_sources
        ],
        "uptake_sinks": [
            {
                "identifier": sink.identifier,
                "kind": sink.__class__.__name__,
                "x_micron": sink.x_micron,
                "y_micron": sink.y_micron,
                "radius_micron": getattr(sink, "footprint_radius_micron", 0.0),
                "effective_volume_micron3": sink.effective_volume_micron3,
                "uptake_rate": sink.uptake_rate.value,
                "uptake_rate_unit": sink.uptake_rate.unit,
                "evidence": sink.uptake_rate.evidence.value,
            }
            for sink in experiment.uptake_sinks
        ],
    }


def _run_summary(bundle, *, include_field: bool) -> dict[str, object]:
    result = bundle.result
    final = result.samples[-1]
    experiment = bundle.experiment
    payload: dict[str, object] = {
        "experiment": _experiment_summary(experiment),
        "vesiclescope_revision": bundle.vesiclescope_revision,
        "engine": {
            "name": result.engine.engine,
            "physicell_release": result.engine.physicell_release,
            "physicell_commit": result.engine.physicell_commit,
            "biofvm_version": result.engine.biofvm_version,
        },
        "numerics": {
            "grid_spacing_micron": bundle.numerics.grid_spacing_micron,
            "time_step_min": bundle.numerics.time_step_min,
        },
        "grid": {
            "nx": result.grid.nx,
            "ny": result.grid.ny,
            "grid_spacing_micron": result.grid.grid_spacing_micron,
            "slice_thickness_micron": result.grid.slice_thickness_micron,
        },
        "concentration_unit": result.concentration_unit,
        "quantity_unit": result.integrated_quantity_unit,
        "samples": [
            {
                "time_min": sample.time_min,
                "extracellular_quantity": sample.integrated_field_quantity,
                "internalized_quantity": sample.internalized_field_quantity,
                "mean_concentration": sample.mean_concentration,
            }
            for sample in result.samples
        ],
        "final": {
            "time_min": final.time_min,
            "extracellular_quantity": final.integrated_field_quantity,
            "internalized_quantity": final.internalized_field_quantity,
        },
    }
    if include_field:
        snapshot = result.field_snapshots[-1]
        payload["final_field"] = {
            "time_min": snapshot.time_min,
            "values": list(snapshot.values),
        }
    return payload


@dataclass(frozen=True, slots=True)
class WorkspaceApplication:
    workspace: Workspace
    runner: Path
    revision: str

    def __post_init__(self) -> None:
        runner = Path(self.runner).expanduser().resolve()
        if not runner.is_file():
            raise ValueError(f"native runner does not exist: {runner}")
        if not isinstance(self.revision, str) or _REVISION_RE.fullmatch(self.revision) is None:
            raise ValueError("revision must be a 40- or 64-character hexadecimal commit SHA")
        object.__setattr__(self, "runner", runner)
        object.__setattr__(self, "revision", self.revision.lower())
        self.workspace.initialize()

    def state(self) -> dict[str, object]:
        experiments: list[dict[str, object]] = []
        for name in self.workspace.list_experiment_names():
            try:
                experiment = self.workspace.read_experiment(name)
                experiments.append(
                    {
                        "name": name,
                        "valid": True,
                        "experiment_id": experiment.experiment_id,
                        "scientific_status": _experiment_summary(experiment)["scientific_status"],
                    }
                )
            except Exception as exc:
                experiments.append({"name": name, "valid": False, "error": str(exc)})

        runs: list[dict[str, object]] = []
        for name in self.workspace.list_run_names():
            try:
                bundle = self.workspace.read_run(name)
                runs.append(
                    {
                        "name": name,
                        "valid": True,
                        "experiment_id": bundle.experiment.experiment_id,
                        "revision": bundle.vesiclescope_revision,
                    }
                )
            except Exception as exc:
                runs.append({"name": name, "valid": False, "error": str(exc)})

        return {
            "workspace": str(self.workspace.root),
            "runner": str(self.runner),
            "revision": self.revision,
            "experiments": experiments,
            "runs": runs,
        }

    def create_baseline(self, name: str) -> dict[str, object]:
        path = self.workspace.create_baseline_experiment(name)
        return {"name": path.name}

    def import_experiment(self, name: str, document: str) -> dict[str, object]:
        if not isinstance(document, str):
            raise ValueError("experiment document must be text")
        if len(document.encode("utf-8")) > 2_000_000:
            raise ValueError("experiment document exceeds 2 MB")
        path = self.workspace.import_experiment(name, document)
        return {"name": path.name}

    def experiment(self, name: str) -> dict[str, object]:
        return _experiment_summary(self.workspace.read_experiment(name))


    def derive_synthetic_experiment(
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
    ) -> dict[str, object]:
        path = self.workspace.derive_synthetic_variant(
            source_name=source_name,
            output_name=output_name,
            experiment_id=experiment_id,
            duration_min=duration_min,
            sample_every_min=sample_every_min,
            diffusion_value=diffusion_value,
            decay_value=decay_value,
            initial_concentration_value=initial_concentration_value,
            release_rates=release_rates,
            uptake_rates=uptake_rates,
        )
        return {
            "name": path.name,
            "experiment": _experiment_summary(self.workspace.read_experiment(path.name)),
        }

    def execute(
        self,
        *,
        experiment_name: str,
        run_name: str,
        grid_spacing_micron: float,
        time_step_min: float,
    ) -> dict[str, object]:
        path = self.workspace.execute_experiment(
            experiment_name=experiment_name,
            run_name=run_name,
            runner=self.runner,
            revision=self.revision,
            grid_spacing_micron=grid_spacing_micron,
            time_step_min=time_step_min,
        )
        return {"name": path.name}

    def run(self, name: str, *, include_field: bool = True) -> dict[str, object]:
        return _run_summary(self.workspace.read_run(name), include_field=include_field)

    def compare(self, left: str, right: str) -> dict[str, object]:
        summary = compare_run_bundles(
            self.workspace.read_run(left),
            self.workspace.read_run(right),
        )
        return {
            "left_experiment_id": summary.left_experiment_id,
            "right_experiment_id": summary.right_experiment_id,
            "quantity_unit": summary.quantity_unit,
            "left_grid_spacing_micron": summary.left_grid_spacing_micron,
            "right_grid_spacing_micron": summary.right_grid_spacing_micron,
            "left_time_step_min": summary.left_time_step_min,
            "right_time_step_min": summary.right_time_step_min,
            "extracellular_delta": summary.extracellular_delta,
            "internalized_delta": summary.internalized_delta,
            "extracellular_ratio_right_over_left": summary.extracellular_ratio_right_over_left,
            "internalized_ratio_right_over_left": summary.internalized_ratio_right_over_left,
        }

    def artifact_path(self, kind: str, name: str) -> Path:
        if kind == "experiment":
            path = self.workspace.experiment_path(name)
        elif kind == "run":
            path = self.workspace.run_path(name)
        else:
            raise ValueError("artifact kind must be experiment or run")
        if not path.is_file():
            raise ValueError(f"artifact does not exist: {name}")
        return path
