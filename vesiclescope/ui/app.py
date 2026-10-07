"""Application services shared by the local UI and tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from vesiclescope.analysis import compare_run_bundles_detailed
from vesiclescope.ui.workspace import Workspace


_REVISION_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
_MAX_COMBINE_ARCHIVE_BYTES = 64 * 1024 * 1024


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


def _source_summary(source) -> dict[str, object] | None:
    if source is None:
        return None
    return {
        "identifier": source.identifier,
        "location": source.location,
    }


def _context_summary(context) -> dict[str, object] | None:
    if context is None:
        return None
    return {
        "species": context.species,
        "tissue": context.tissue,
        "cell_type": context.cell_type,
        "cell_line": context.cell_line,
        "ev_preparation": context.ev_preparation,
        "measurement_method": context.measurement_method,
        "experimental_conditions": context.experimental_conditions,
    }


def _measurement_summary(dataset) -> dict[str, object]:
    return {
        "dataset_id": dataset.dataset_id,
        "reference_time_description": dataset.reference_time_description,
        "limitations": list(dataset.limitations),
        "samples": [
            {
                "sample_id": sample.sample_id,
                "specimen": sample.specimen.value,
                "anticoagulant": sample.anticoagulant,
                "collection_to_processing_min": sample.collection_to_processing_min,
                "centrifugation_steps": [
                    {
                        "relative_centrifugal_force_g": step.relative_centrifugal_force_g,
                        "duration_min": step.duration_min,
                        "retained_fraction": step.retained_fraction,
                        "temperature_c": step.temperature_c,
                    }
                    for step in sample.centrifugation_steps
                ],
                "residual_platelet_count_per_ul": sample.residual_platelet_count_per_ul,
                "hemolysis_assessment": sample.hemolysis_assessment,
                "limitations": list(sample.limitations),
            }
            for sample in dataset.samples
        ],
        "timepoints": [
            {
                "sample_id": timepoint.sample_id,
                "condition_id": timepoint.condition_id,
                "time_min": timepoint.time_min,
                "biological_replicate_id": timepoint.biological_replicate_id,
                "observations": [
                    {
                        "identifier": observation.identifier,
                        "scientific_name": observation.scientific_name,
                        "kind": observation.kind.value,
                        "value": observation.value,
                        "unit": observation.unit,
                        "method": observation.method,
                        "detection_semantics": observation.detection_semantics,
                        "markers": list(observation.markers),
                        "marker_defined": bool(observation.markers),
                        "technical_replicates": observation.technical_replicates,
                        "standard_deviation": observation.standard_deviation,
                        "notes": list(observation.notes),
                    }
                    for observation in timepoint.observations
                ],
            }
            for timepoint in dataset.timepoints
        ],
    }


def _parameter_summary(parameter) -> dict[str, object] | None:
    if parameter is None:
        return None
    return {
        "identifier": parameter.identifier,
        "scientific_name": parameter.scientific_name,
        "value": parameter.value,
        "unit": parameter.unit,
        "evidence": parameter.evidence.value,
        "source": _source_summary(parameter.source),
        "context": _context_summary(parameter.context),
        "assumptions": list(parameter.assumptions),
        "limitations": list(parameter.limitations),
    }


def _perturbation_summary(study) -> dict[str, object]:
    return {
        "study_id": study.study_id,
        "measurement_dataset_ids": list(study.measurement_dataset_ids),
        "transport_experiment_ids": list(study.transport_experiment_ids),
        "limitations": list(study.limitations),
        "exposures": [
            {
                "identifier": exposure.identifier,
                "compound_name": exposure.compound_name,
                "concentration": _parameter_summary(exposure.concentration),
                "target": exposure.target.value,
                "start_min": exposure.start_min,
                "end_min": exposure.end_min,
                "evidence": exposure.evidence.value,
                "source": _source_summary(exposure.source),
                "context": _context_summary(exposure.context),
                "assumptions": list(exposure.assumptions),
                "limitations": list(exposure.limitations),
            }
            for exposure in study.exposures
        ],
        "phenotypes": [
            {
                "identifier": phenotype.identifier,
                "name": phenotype.name,
                "context": _context_summary(phenotype.context),
                "limitations": list(phenotype.limitations),
                "markers": [
                    {
                        "identifier": marker.identifier,
                        "marker_name": marker.marker_name,
                        "state": marker.state.value,
                        "evidence": marker.evidence.value,
                        "source": _source_summary(marker.source),
                        "context": _context_summary(marker.context),
                        "limitations": list(marker.limitations),
                    }
                    for marker in phenotype.markers
                ],
                "cargo": [
                    {
                        "identifier": cargo.identifier,
                        "molecule_name": cargo.molecule_name,
                        "cargo_class": cargo.cargo_class.value,
                        "evidence": cargo.evidence.value,
                        "source": _source_summary(cargo.source),
                        "context": _context_summary(cargo.context),
                        "abundance": _parameter_summary(cargo.abundance),
                        "qualitative_state": cargo.qualitative_state,
                        "limitations": list(cargo.limitations),
                    }
                    for cargo in phenotype.cargo
                ],
            }
            for phenotype in study.phenotypes
        ],
        "effects": [
            {
                "identifier": effect.identifier,
                "exposure_id": effect.exposure_id,
                "outcome": effect.outcome.value,
                "direction": effect.direction.value,
                "evidence": effect.evidence.value,
                "source": _source_summary(effect.source),
                "context": _context_summary(effect.context),
                "phenotype_id": effect.phenotype_id,
                "feature_id": effect.feature_id,
                "magnitude": _parameter_summary(effect.magnitude),
                "model_mapping": (
                    {
                        "target": effect.model_mapping.target.value,
                        "operation": effect.model_mapping.operation.value,
                        "value": _parameter_summary(effect.model_mapping.value),
                        "target_identifier": effect.model_mapping.target_identifier,
                    }
                    if effect.model_mapping is not None
                    else None
                ),
                "limitations": list(effect.limitations),
            }
            for effect in study.effects
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

        measurements: list[dict[str, object]] = []
        for name in self.workspace.list_measurement_names():
            try:
                dataset = self.workspace.read_measurement(name)
                measurements.append(
                    {
                        "name": name,
                        "valid": True,
                        "dataset_id": dataset.dataset_id,
                        "samples": len(dataset.samples),
                        "timepoints": len(dataset.timepoints),
                    }
                )
            except Exception as exc:
                measurements.append(
                    {"name": name, "valid": False, "error": str(exc)}
                )

        perturbations: list[dict[str, object]] = []
        for name in self.workspace.list_perturbation_names():
            try:
                study = self.workspace.read_perturbation(name)
                perturbations.append(
                    {
                        "name": name,
                        "valid": True,
                        "study_id": study.study_id,
                        "exposures": len(study.exposures),
                        "phenotypes": len(study.phenotypes),
                        "effects": len(study.effects),
                    }
                )
            except Exception as exc:
                perturbations.append(
                    {"name": name, "valid": False, "error": str(exc)}
                )

        population_runs: list[dict[str, object]] = []
        for name in self.workspace.list_population_run_names():
            try:
                run = self.workspace.read_population_run(name)
                population_runs.append(
                    {
                        "name": name,
                        "valid": True,
                        "study_id": run.study.study_id,
                        "populations": [item.phenotype_id for item in run.populations],
                    }
                )
            except Exception as exc:
                population_runs.append(
                    {"name": name, "valid": False, "error": str(exc)}
                )

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
            "measurements": measurements,
            "perturbations": perturbations,
            "population_runs": population_runs,
        }

    def import_measurement(self, name: str, document: str) -> dict[str, object]:
        if not isinstance(document, str):
            raise ValueError("measurement document must be text")
        if len(document.encode("utf-8")) > 2_000_000:
            raise ValueError("measurement document exceeds 2 MB")
        path = self.workspace.import_measurement(name, document)
        return {"name": path.name}

    def import_perturbation(self, name: str, document: str) -> dict[str, object]:
        if not isinstance(document, str):
            raise ValueError("perturbation document must be text")
        if len(document.encode("utf-8")) > 2_000_000:
            raise ValueError("perturbation document exceeds 2 MB")
        path = self.workspace.import_perturbation(name, document)
        return {"name": path.name}

    def measurement(self, name: str) -> dict[str, object]:
        return _measurement_summary(self.workspace.read_measurement(name))

    def perturbation(self, name: str) -> dict[str, object]:
        return _perturbation_summary(self.workspace.read_perturbation(name))

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


    def export_archive(self, experiment_name: str) -> tuple[str, bytes]:
        data = self.workspace.export_combine_archive(experiment_name)
        filename = re.sub(r"\.json\Z", "", experiment_name) + ".omex"
        return filename, data

    def export_batch_archive(self, run_names: list[str]) -> tuple[str, bytes]:
        if not isinstance(run_names, list) or not all(isinstance(name, str) for name in run_names):
            raise ValueError("batch run selection must be a list of filenames")
        data = self.workspace.export_batch_archive(tuple(run_names))
        if len(data) > _MAX_COMBINE_ARCHIVE_BYTES:
            raise ValueError("COMBINE batch archive exceeds 64 MB browser limit")
        return "experiment-batch.omex", data

    def import_batch_archive(self, data: bytes) -> dict[str, object]:
        if not isinstance(data, bytes) or len(data) > _MAX_COMBINE_ARCHIVE_BYTES:
            raise ValueError("COMBINE batch upload must be binary and at most 64 MB")
        return self.workspace.import_batch_archive(data)

    def import_archive(self, data: bytes) -> dict[str, object]:
        if not isinstance(data, bytes):
            raise ValueError("COMBINE archive upload must be binary")
        if len(data) > _MAX_COMBINE_ARCHIVE_BYTES:
            raise ValueError("COMBINE archive upload exceeds 64 MB")
        return self.workspace.import_combine_archive(data)

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
        summary = compare_run_bundles_detailed(
            self.workspace.read_run(left),
            self.workspace.read_run(right),
        )
        endpoint = summary.endpoint
        spatial = summary.spatial
        return {
            "left_experiment_id": endpoint.left_experiment_id,
            "right_experiment_id": endpoint.right_experiment_id,
            "quantity_unit": endpoint.quantity_unit,
            "left_grid_spacing_micron": endpoint.left_grid_spacing_micron,
            "right_grid_spacing_micron": endpoint.right_grid_spacing_micron,
            "left_time_step_min": endpoint.left_time_step_min,
            "right_time_step_min": endpoint.right_time_step_min,
            "extracellular_delta": endpoint.extracellular_delta,
            "internalized_delta": endpoint.internalized_delta,
            "extracellular_ratio_right_over_left": endpoint.extracellular_ratio_right_over_left,
            "internalized_ratio_right_over_left": endpoint.internalized_ratio_right_over_left,
            "left_revision": summary.left_revision,
            "right_revision": summary.right_revision,
            "left_engine": {
                "name": summary.left_engine,
                "physicell_release": summary.left_physicell_release,
                "biofvm_version": summary.left_biofvm_version,
            },
            "right_engine": {
                "name": summary.right_engine,
                "physicell_release": summary.right_physicell_release,
                "biofvm_version": summary.right_biofvm_version,
            },
            "left_series": [
                {
                    "time_min": item.time_min,
                    "extracellular_quantity": item.extracellular_quantity,
                    "internalized_quantity": item.internalized_quantity,
                }
                for item in summary.left_series
            ],
            "right_series": [
                {
                    "time_min": item.time_min,
                    "extracellular_quantity": item.extracellular_quantity,
                    "internalized_quantity": item.internalized_quantity,
                }
                for item in summary.right_series
            ],
            "spatial": {
                "compatible": spatial.compatible,
                "reason": spatial.reason,
                "nx": spatial.nx,
                "ny": spatial.ny,
                "concentration_unit": spatial.concentration_unit,
                "time_min": spatial.time_min,
                "values": list(spatial.values),
                "minimum_difference": spatial.minimum_difference,
                "maximum_difference": spatial.maximum_difference,
                "mean_absolute_difference": spatial.mean_absolute_difference,
            },
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
