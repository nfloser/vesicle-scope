"""Resolve explicit perturbation mappings into phenotype-specific transport inputs.

This module is deliberately conservative. A biological exposure or qualitative
reported effect never changes a transport parameter by itself. Only an explicit
ModelEffectMapping can alter release, uptake, or decay, and the transformation is
recorded in an immutable audit object.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math
from pathlib import Path

from vesiclescope.domain import (
    EffectDirection,
    EffectOperation,
    EffectOutcome,
    ModelEffectTarget,
    PerturbationEffect,
    PerturbationStudy,
    PointReleaseSource,
    CircularReleaseSource,
    PointUptakeSink,
    CircularUptakeSink,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines import (
    BioFVMNumerics,
    BioFVMRunResult,
    SpatialFieldSnapshot2D,
    TransportSample,
    run_transport,
)
from vesiclescope.run_bundles import SimulationRunBundle


class EffectExecutionStatus(str, Enum):
    """Whether one declared biological effect changed transport."""

    APPLIED = "applied"
    NOT_EXECUTED = "not_executed"


@dataclass(frozen=True, slots=True)
class EffectExecutionAudit:
    """Auditable execution disposition for one perturbation effect."""

    effect_id: str
    exposure_id: str
    phenotype_id: str | None
    direction: EffectDirection
    status: EffectExecutionStatus
    reason: str
    model_target: ModelEffectTarget | None = None
    target_identifier: str | None = None
    operation: EffectOperation | None = None
    mapping_parameter_id: str | None = None
    mapping_evidence: str | None = None
    mapping_source_id: str | None = None
    baseline_value: float | None = None
    effective_value: float | None = None
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class PopulationTransportSpec:
    """Baseline transport model assigned explicitly to one EV phenotype."""

    phenotype_id: str
    experiment: TransportExperiment

    def __post_init__(self) -> None:
        if not isinstance(self.phenotype_id, str) or not self.phenotype_id.strip():
            raise ValueError("phenotype_id must be a non-blank string")
        object.__setattr__(self, "phenotype_id", self.phenotype_id.strip())
        if not isinstance(self.experiment, TransportExperiment):
            raise TypeError("experiment must be a TransportExperiment")


@dataclass(frozen=True, slots=True)
class ResolvedPopulationTransport:
    """One population before and after all executable mappings."""

    phenotype_id: str
    baseline_experiment: TransportExperiment
    effective_experiment: TransportExperiment
    effects: tuple[EffectExecutionAudit, ...]


@dataclass(frozen=True, slots=True)
class ResolvedPerturbationTransport:
    """Complete resolved plan including effects that were deliberately not executed."""

    study: PerturbationStudy
    populations: tuple[ResolvedPopulationTransport, ...]
    unexecuted_effects: tuple[EffectExecutionAudit, ...]


def _not_executed(effect: PerturbationEffect, reason: str) -> EffectExecutionAudit:
    mapping = effect.model_mapping
    return EffectExecutionAudit(
        effect_id=effect.identifier,
        exposure_id=effect.exposure_id,
        phenotype_id=effect.phenotype_id,
        direction=effect.direction,
        status=EffectExecutionStatus.NOT_EXECUTED,
        reason=reason,
        model_target=mapping.target if mapping is not None else None,
        target_identifier=mapping.target_identifier if mapping is not None else None,
        operation=mapping.operation if mapping is not None else None,
        mapping_parameter_id=mapping.value.identifier if mapping is not None else None,
        mapping_evidence=mapping.value.evidence.value if mapping is not None else None,
        mapping_source_id=(
            mapping.value.source.identifier
            if mapping is not None and mapping.value.source is not None
            else None
        ),
    )


def _validate_direction(
    effect: PerturbationEffect,
    baseline: float,
    effective: float,
) -> None:
    if effect.direction in {EffectDirection.UNKNOWN, EffectDirection.MIXED}:
        raise ValueError(
            f"effect {effect.identifier!r} has a deterministic model mapping but "
            f"reported direction is {effect.direction.value!r}"
        )

    same = math.isclose(baseline, effective, rel_tol=1e-12, abs_tol=1e-15)
    if effect.direction is EffectDirection.INCREASE and not effective > baseline:
        raise ValueError(
            f"effect {effect.identifier!r} mapping contradicts reported increase direction"
        )
    if effect.direction is EffectDirection.DECREASE and not effective < baseline:
        raise ValueError(
            f"effect {effect.identifier!r} mapping contradicts reported decrease direction"
        )
    if effect.direction is EffectDirection.NO_CHANGE and not same:
        raise ValueError(
            f"effect {effect.identifier!r} mapping contradicts reported no_change direction"
        )


def _mapped_value(
    baseline: ScientificParameter,
    effect: PerturbationEffect,
) -> tuple[ScientificParameter, EffectExecutionAudit]:
    mapping = effect.model_mapping
    if mapping is None:
        raise ValueError("internal error: executable mapping is missing")

    mapping_value = mapping.value
    if mapping.operation is EffectOperation.MULTIPLY:
        if mapping_value.unit != "fold":
            raise ValueError(
                f"effect {effect.identifier!r} multiply mapping must use 'fold' units"
            )
        if mapping_value.value < 0.0:
            raise ValueError(
                f"effect {effect.identifier!r} multiply mapping must be non-negative"
            )
        effective_value = baseline.value * mapping_value.value
    elif mapping.operation in {EffectOperation.ADD, EffectOperation.SET}:
        if mapping_value.unit != baseline.unit:
            raise ValueError(
                f"effect {effect.identifier!r} {mapping.operation.value} mapping must "
                f"use the same unit as its target ({baseline.unit!r})"
            )
        effective_value = (
            baseline.value + mapping_value.value
            if mapping.operation is EffectOperation.ADD
            else mapping_value.value
        )
    else:
        raise ValueError(
            f"unsupported effect operation for {effect.identifier!r}: "
            f"{mapping.operation.value!r}"
        )

    if effective_value < 0.0 or not math.isfinite(effective_value):
        raise ValueError(
            f"effect {effect.identifier!r} produces an invalid negative/non-finite value"
        )

    _validate_direction(effect, baseline.value, effective_value)

    limitation = (
        f"Derived from baseline parameter {baseline.identifier!r} through explicit "
        f"perturbation effect {effect.identifier!r} using mapping parameter "
        f"{mapping_value.identifier!r}; inspect the population-run audit for full "
        "mapping provenance."
    )
    effective = replace(
        baseline,
        value=effective_value,
        limitations=baseline.limitations + (limitation,),
    )
    audit = EffectExecutionAudit(
        effect_id=effect.identifier,
        exposure_id=effect.exposure_id,
        phenotype_id=effect.phenotype_id,
        direction=effect.direction,
        status=EffectExecutionStatus.APPLIED,
        reason="explicit transport mapping applied",
        model_target=mapping.target,
        target_identifier=mapping.target_identifier,
        operation=mapping.operation,
        mapping_parameter_id=mapping_value.identifier,
        mapping_evidence=mapping_value.evidence.value,
        mapping_source_id=(
            mapping_value.source.identifier
            if mapping_value.source is not None
            else None
        ),
        baseline_value=baseline.value,
        effective_value=effective_value,
        unit=baseline.unit,
    )
    return effective, audit


def _apply_release_mapping(
    experiment: TransportExperiment,
    effect: PerturbationEffect,
) -> tuple[TransportExperiment, EffectExecutionAudit]:
    mapping = effect.model_mapping
    if mapping is None or not mapping.target_identifier:
        raise ValueError(
            f"effect {effect.identifier!r} release mapping requires target_identifier"
        )

    found = False
    updated = []
    audit: EffectExecutionAudit | None = None
    for source in experiment.release_sources:
        if source.identifier != mapping.target_identifier:
            updated.append(source)
            continue
        found = True
        rate, audit = _mapped_value(source.release_rate, effect)
        if isinstance(source, PointReleaseSource):
            updated.append(replace(source, release_rate=rate))
        elif isinstance(source, CircularReleaseSource):
            updated.append(replace(source, release_rate=rate))
        else:
            raise TypeError("unsupported release source type")
    if not found:
        raise ValueError(
            f"effect {effect.identifier!r} references unknown release source "
            f"{mapping.target_identifier!r}"
        )
    if audit is None:
        raise RuntimeError("release mapping did not produce an audit")
    return replace(experiment, release_sources=tuple(updated)), audit


def _apply_uptake_mapping(
    experiment: TransportExperiment,
    effect: PerturbationEffect,
) -> tuple[TransportExperiment, EffectExecutionAudit]:
    mapping = effect.model_mapping
    if mapping is None or not mapping.target_identifier:
        raise ValueError(
            f"effect {effect.identifier!r} uptake mapping requires target_identifier"
        )

    found = False
    updated = []
    audit: EffectExecutionAudit | None = None
    for sink in experiment.uptake_sinks:
        if sink.identifier != mapping.target_identifier:
            updated.append(sink)
            continue
        found = True
        rate, audit = _mapped_value(sink.uptake_rate, effect)
        if isinstance(sink, PointUptakeSink):
            updated.append(replace(sink, uptake_rate=rate))
        elif isinstance(sink, CircularUptakeSink):
            updated.append(replace(sink, uptake_rate=rate))
        else:
            raise TypeError("unsupported uptake sink type")
    if not found:
        raise ValueError(
            f"effect {effect.identifier!r} references unknown uptake sink "
            f"{mapping.target_identifier!r}"
        )
    if audit is None:
        raise RuntimeError("uptake mapping did not produce an audit")
    return replace(experiment, uptake_sinks=tuple(updated)), audit


def _apply_decay_mapping(
    experiment: TransportExperiment,
    effect: PerturbationEffect,
) -> tuple[TransportExperiment, EffectExecutionAudit]:
    mapping = effect.model_mapping
    if mapping is None:
        raise ValueError("internal error: decay mapping is missing")
    if mapping.target_identifier is not None:
        raise ValueError(
            f"effect {effect.identifier!r} decay mapping is population-wide and "
            "must not set target_identifier"
        )
    decay, audit = _mapped_value(experiment.decay, effect)
    return replace(experiment, decay=decay), audit


def resolve_perturbation_transport(
    study: PerturbationStudy,
    populations: tuple[PopulationTransportSpec, ...],
) -> ResolvedPerturbationTransport:
    """Resolve only explicit transport mappings for explicitly named EV populations.

    Qualitative effects, unassigned effects, marker/cargo mappings and phenotype
    fractions remain visible as NOT_EXECUTED audit entries. No response curve,
    phenotype fraction, measured assay value, or missing parameter is inferred.
    """

    if not isinstance(study, PerturbationStudy):
        raise TypeError("study must be a PerturbationStudy")
    if not isinstance(populations, tuple) or not populations:
        raise ValueError("populations must be a non-empty tuple")
    if not all(isinstance(item, PopulationTransportSpec) for item in populations):
        raise TypeError("populations must contain PopulationTransportSpec objects")

    phenotype_ids = {item.identifier for item in study.phenotypes}
    population_ids = tuple(item.phenotype_id for item in populations)
    if len(set(population_ids)) != len(population_ids):
        raise ValueError("population phenotype identifiers must be unique")
    unknown = sorted(set(population_ids) - phenotype_ids)
    if unknown:
        raise ValueError(
            "population specs reference unknown study phenotypes: " + ", ".join(unknown)
        )

    by_population: dict[str, list[PerturbationEffect]] = {
        phenotype_id: [] for phenotype_id in population_ids
    }
    unassigned: list[EffectExecutionAudit] = []
    for declared_effect in study.effects:
        if declared_effect.phenotype_id is None:
            unassigned.append(
                _not_executed(
                    declared_effect,
                    "effect has no phenotype_id; it is not broadcast across populations",
                )
            )
            continue
        if declared_effect.phenotype_id not in by_population:
            unassigned.append(
                _not_executed(
                    declared_effect,
                    "no transport population is configured for this phenotype",
                )
            )
            continue
        by_population[declared_effect.phenotype_id].append(declared_effect)

    resolved: list[ResolvedPopulationTransport] = []
    for population in populations:
        effective = population.experiment
        audits: list[EffectExecutionAudit] = []
        claimed_targets: set[tuple[ModelEffectTarget, str | None]] = set()

        for declared_effect in by_population[population.phenotype_id]:
            mapping = declared_effect.model_mapping
            if mapping is None:
                audits.append(
                    _not_executed(
                        declared_effect,
                        "effect has no model mapping; qualitative evidence is preserved only",
                    )
                )
                continue

            if mapping.target in {
                ModelEffectTarget.PHENOTYPE_FRACTION,
                ModelEffectTarget.CARGO_ABUNDANCE,
            }:
                audits.append(
                    _not_executed(
                        declared_effect,
                        f"{mapping.target.value} is not a transport parameter in the "
                        "current execution model",
                    )
                )
                continue

            if declared_effect.direction in {
                EffectDirection.UNKNOWN,
                EffectDirection.MIXED,
            }:
                raise ValueError(
                    f"effect {declared_effect.identifier!r} has a deterministic model "
                    f"mapping but reported direction is {declared_effect.direction.value!r}"
                )

            expected_outcome = {
                ModelEffectTarget.RELEASE_RATE: EffectOutcome.EV_RELEASE,
                ModelEffectTarget.UPTAKE_RATE: EffectOutcome.EV_UPTAKE,
                ModelEffectTarget.DECAY_RATE: EffectOutcome.EV_CLEARANCE,
            }[mapping.target]
            if declared_effect.outcome is not expected_outcome:
                raise ValueError(
                    f"effect {declared_effect.identifier!r} outcome "
                    f"{declared_effect.outcome.value!r} cannot execute as "
                    f"{mapping.target.value!r}"
                )

            key = (mapping.target, mapping.target_identifier)
            if key in claimed_targets:
                raise ValueError(
                    "multiple effects target the same transport parameter for phenotype "
                    f"{population.phenotype_id!r}: {mapping.target.value}/"
                    f"{mapping.target_identifier!r}"
                )
            claimed_targets.add(key)

            if mapping.target is ModelEffectTarget.RELEASE_RATE:
                effective, audit = _apply_release_mapping(effective, declared_effect)
            elif mapping.target is ModelEffectTarget.UPTAKE_RATE:
                effective, audit = _apply_uptake_mapping(effective, declared_effect)
            elif mapping.target is ModelEffectTarget.DECAY_RATE:
                effective, audit = _apply_decay_mapping(effective, declared_effect)
            else:
                raise ValueError(
                    f"unsupported transport mapping target: {mapping.target.value!r}"
                )
            audits.append(audit)

        resolved.append(
            ResolvedPopulationTransport(
                phenotype_id=population.phenotype_id,
                baseline_experiment=population.experiment,
                effective_experiment=effective,
                effects=tuple(audits),
            )
        )

    return ResolvedPerturbationTransport(
        study=study,
        populations=tuple(resolved),
        unexecuted_effects=tuple(unassigned),
    )


@dataclass(frozen=True, slots=True)
class PopulationRunRecord:
    """Completed reproducible run for one phenotype-specific population."""

    phenotype_id: str
    baseline_experiment: TransportExperiment
    effects: tuple[EffectExecutionAudit, ...]
    run_bundle: SimulationRunBundle

    def __post_init__(self) -> None:
        if not isinstance(self.phenotype_id, str) or not self.phenotype_id.strip():
            raise ValueError("phenotype_id must be a non-blank string")
        object.__setattr__(self, "phenotype_id", self.phenotype_id.strip())
        if not isinstance(self.baseline_experiment, TransportExperiment):
            raise TypeError("baseline_experiment must be a TransportExperiment")
        if not isinstance(self.effects, tuple) or not all(
            isinstance(item, EffectExecutionAudit) for item in self.effects
        ):
            raise TypeError("effects must be a tuple of EffectExecutionAudit objects")
        if not isinstance(self.run_bundle, SimulationRunBundle):
            raise TypeError("run_bundle must be a SimulationRunBundle")
        if (
            self.baseline_experiment.experiment_id
            != self.run_bundle.experiment.experiment_id
        ):
            raise ValueError(
                "baseline and effective run experiments must keep the same experiment id"
            )
        if any(item.phenotype_id != self.phenotype_id for item in self.effects):
            raise ValueError(
                "population effect audits must reference the record phenotype"
            )

    @property
    def effective_experiment(self) -> TransportExperiment:
        return self.run_bundle.experiment

    @property
    def result(self) -> BioFVMRunResult:
        return self.run_bundle.result


@dataclass(frozen=True, slots=True)
class PopulationTransportRun:
    """Completed independently transported EV populations for one study."""

    study: PerturbationStudy
    populations: tuple[PopulationRunRecord, ...]
    unexecuted_effects: tuple[EffectExecutionAudit, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.study, PerturbationStudy):
            raise TypeError("study must be a PerturbationStudy")
        if not isinstance(self.populations, tuple) or not self.populations:
            raise ValueError("populations must be a non-empty tuple")
        if not all(isinstance(item, PopulationRunRecord) for item in self.populations):
            raise TypeError("populations must contain PopulationRunRecord objects")
        identifiers = tuple(item.phenotype_id for item in self.populations)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("population run phenotype identifiers must be unique")
        study_phenotypes = {item.identifier for item in self.study.phenotypes}
        unknown = sorted(set(identifiers) - study_phenotypes)
        if unknown:
            raise ValueError(
                "population run references an unknown study phenotype: "
                + ", ".join(unknown)
            )
        if not isinstance(self.unexecuted_effects, tuple) or not all(
            isinstance(item, EffectExecutionAudit)
            for item in self.unexecuted_effects
        ):
            raise TypeError(
                "unexecuted_effects must be a tuple of EffectExecutionAudit objects"
            )


def _same_times(left: tuple[float, ...], right: tuple[float, ...]) -> bool:
    return len(left) == len(right) and all(
        math.isclose(a, b, rel_tol=0.0, abs_tol=1e-9)
        for a, b in zip(left, right)
    )


def _validate_composable_results(records: tuple[PopulationRunRecord, ...]) -> None:
    first = records[0].result
    first_sample_times = tuple(item.time_min for item in first.samples)
    first_field_times = tuple(item.time_min for item in first.field_snapshots)

    for record in records[1:]:
        result = record.result
        if result.concentration_unit != first.concentration_unit:
            raise ValueError("population results must use the same concentration unit")
        if result.integrated_quantity_unit != first.integrated_quantity_unit:
            raise ValueError(
                "population results must use the same integrated quantity unit"
            )
        if result.internalized_quantity_unit != first.internalized_quantity_unit:
            raise ValueError(
                "population results must use the same internalized quantity unit"
            )
        if result.engine != first.engine:
            raise ValueError("population results must use the same engine identity")
        if result.grid != first.grid:
            raise ValueError("population results must use the same numerical grid")
        if not _same_times(
            first_sample_times,
            tuple(item.time_min for item in result.samples),
        ):
            raise ValueError("population results must use identical sample times")
        if not _same_times(
            first_field_times,
            tuple(item.time_min for item in result.field_snapshots),
        ):
            raise ValueError("population results must use identical field snapshot times")
        if len(result.samples) != len(result.field_snapshots):
            raise ValueError(
                "population results require one field snapshot per summary sample"
            )


def run_population_transport(
    resolved: ResolvedPerturbationTransport,
    numerics: BioFVMNumerics,
    runner: Path | str,
    vesiclescope_revision: str,
) -> PopulationTransportRun:
    """Execute each phenotype as an independent BioFVM substrate-equivalent run.

    The current native runner is intentionally left unchanged. Independent EV
    populations are executed separately through the already verified single-
    population adapter and may be composed only when grid, time, units and
    engine identity are exactly compatible. This does not model interactions
    between EV populations.
    """

    if not isinstance(resolved, ResolvedPerturbationTransport):
        raise TypeError("resolved must be a ResolvedPerturbationTransport")
    if not isinstance(numerics, BioFVMNumerics):
        raise TypeError("numerics must be BioFVMNumerics")

    executable = Path(runner)
    records: list[PopulationRunRecord] = []
    for population in resolved.populations:
        result = run_transport(population.effective_experiment, numerics, executable)
        bundle = SimulationRunBundle(
            vesiclescope_revision=vesiclescope_revision,
            experiment=population.effective_experiment,
            numerics=numerics,
            result=result,
        )
        records.append(
            PopulationRunRecord(
                phenotype_id=population.phenotype_id,
                baseline_experiment=population.baseline_experiment,
                effects=population.effects,
                run_bundle=bundle,
            )
        )

    completed = tuple(records)
    _validate_composable_results(completed)
    return PopulationTransportRun(
        study=resolved.study,
        populations=completed,
        unexecuted_effects=resolved.unexecuted_effects,
    )


def aggregate_population_fields(
    run: PopulationTransportRun,
) -> tuple[SpatialFieldSnapshot2D, ...]:
    """Return pointwise total extracellular fields without discarding child fields."""

    if not isinstance(run, PopulationTransportRun):
        raise TypeError("run must be a PopulationTransportRun")
    _validate_composable_results(run.populations)

    first = run.populations[0].result
    snapshots: list[SpatialFieldSnapshot2D] = []
    for index, first_snapshot in enumerate(first.field_snapshots):
        values = tuple(
            sum(
                record.result.field_snapshots[index].values[value_index]
                for record in run.populations
            )
            for value_index in range(len(first_snapshot.values))
        )
        snapshots.append(
            SpatialFieldSnapshot2D(
                time_min=first_snapshot.time_min,
                values=values,
            )
        )
    return tuple(snapshots)


def aggregate_population_samples(
    run: PopulationTransportRun,
) -> tuple[TransportSample, ...]:
    """Return total EV transport summaries derived from compatible child results."""

    fields = aggregate_population_fields(run)
    first = run.populations[0].result
    samples: list[TransportSample] = []

    for index, field in enumerate(fields):
        values = field.values
        samples.append(
            TransportSample(
                time_min=field.time_min,
                mean_concentration=sum(values) / len(values),
                min_concentration=min(values),
                max_concentration=max(values),
                integrated_field_quantity=sum(
                    record.result.samples[index].integrated_field_quantity
                    for record in run.populations
                ),
                internalized_field_quantity=sum(
                    record.result.samples[index].internalized_field_quantity
                    for record in run.populations
                ),
            )
        )

    if not _same_times(
        tuple(item.time_min for item in first.samples),
        tuple(item.time_min for item in samples),
    ):
        raise ValueError("aggregate sample times do not match population samples")
    return tuple(samples)
