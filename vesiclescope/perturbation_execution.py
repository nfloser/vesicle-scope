"""Resolve explicit perturbation mappings into auditable transport variants."""

from __future__ import annotations

from dataclasses import dataclass, replace

from vesiclescope.domain import (
    EffectOperation,
    EvidenceCategory,
    EVPopulationExperiment,
    EVPopulationTransport,
    ModelEffectTarget,
    PerturbationEffect,
    PerturbationStudy,
    ScientificParameter,
)


@dataclass(frozen=True, slots=True)
class AppliedModelEffect:
    """Audit record for one numerical perturbation mapping."""

    effect_id: str
    population_id: str
    target: ModelEffectTarget
    target_identifier: str | None
    operation: EffectOperation
    base_value: float
    mapping_value: float
    effective_value: float
    unit: str


@dataclass(frozen=True, slots=True)
class ResolvedPopulationExperiment:
    """Derived population experiment plus every numerical transformation applied."""

    experiment: EVPopulationExperiment
    applied_effects: tuple[AppliedModelEffect, ...]


def _effective_parameter(
    base: ScientificParameter,
    effect: PerturbationEffect,
    value: float,
) -> ScientificParameter:
    mapping = effect.model_mapping
    if mapping is None:
        raise ValueError("effect has no model mapping")

    mapping_evidence = mapping.value.evidence
    if mapping_evidence in {
        EvidenceCategory.SYNTHETIC_BENCHMARK,
        EvidenceCategory.ASSUMED,
    }:
        evidence = mapping_evidence
        source = None
    else:
        evidence = EvidenceCategory.INFERRED
        source = mapping.value.source or effect.source
        if source is None:
            raise ValueError(
                "evidence-backed model mapping requires a source for the derived parameter"
            )

    return ScientificParameter(
        identifier=f"{base.identifier}.effective.{effect.identifier}",
        scientific_name=f"effective {base.scientific_name}",
        value=value,
        unit=base.unit,
        evidence=evidence,
        source=source,
        context=base.context,
        assumptions=(
            *base.assumptions,
            f"Derived by explicit {mapping.operation.value} mapping from effect {effect.identifier}.",
        ),
        limitations=(
            *base.limitations,
            *effect.limitations,
            "Effective simulation input; the perturbation mapping and source context remain part of the audit trail.",
        ),
    )


def _multiply_parameter(
    base: ScientificParameter,
    effect: PerturbationEffect,
) -> tuple[ScientificParameter, AppliedModelEffect]:
    mapping = effect.model_mapping
    if mapping is None:
        raise ValueError("effect has no model mapping")
    if mapping.operation is not EffectOperation.MULTIPLY:
        raise ValueError(
            "only explicit multiplicative perturbation mappings are executable"
        )
    if mapping.value.unit != "fold":
        raise ValueError("multiplicative perturbation mapping must use unit 'fold'")
    if mapping.value.value < 0.0:
        raise ValueError("multiplicative perturbation factor must be non-negative")

    effective_value = base.value * mapping.value.value
    parameter = _effective_parameter(base, effect, effective_value)
    return parameter, AppliedModelEffect(
        effect_id=effect.identifier,
        population_id="",
        target=mapping.target,
        target_identifier=mapping.target_identifier,
        operation=mapping.operation,
        base_value=base.value,
        mapping_value=mapping.value.value,
        effective_value=effective_value,
        unit=base.unit,
    )


def _apply_one(
    population: EVPopulationTransport,
    effect: PerturbationEffect,
) -> tuple[EVPopulationTransport, AppliedModelEffect]:
    mapping = effect.model_mapping
    if mapping is None:
        raise ValueError("effect has no model mapping")

    transport = population.transport

    if mapping.target is ModelEffectTarget.RELEASE_RATE:
        if mapping.target_identifier is None:
            raise ValueError("release-rate mapping requires target_identifier")
        matches = [
            index
            for index, source in enumerate(transport.release_sources)
            if source.identifier == mapping.target_identifier
        ]
        if len(matches) != 1:
            raise ValueError(
                f"release-rate mapping target {mapping.target_identifier!r} "
                "must identify exactly one release source"
            )
        index = matches[0]
        source = transport.release_sources[index]
        effective, audit = _multiply_parameter(source.release_rate, effect)
        sources = list(transport.release_sources)
        sources[index] = replace(source, release_rate=effective)
        updated = replace(transport, release_sources=tuple(sources))

    elif mapping.target is ModelEffectTarget.UPTAKE_RATE:
        if mapping.target_identifier is None:
            raise ValueError("uptake-rate mapping requires target_identifier")
        matches = [
            index
            for index, sink in enumerate(transport.uptake_sinks)
            if sink.identifier == mapping.target_identifier
        ]
        if len(matches) != 1:
            raise ValueError(
                f"uptake-rate mapping target {mapping.target_identifier!r} "
                "must identify exactly one uptake sink"
            )
        index = matches[0]
        sink = transport.uptake_sinks[index]
        effective, audit = _multiply_parameter(sink.uptake_rate, effect)
        sinks = list(transport.uptake_sinks)
        sinks[index] = replace(sink, uptake_rate=effective)
        updated = replace(transport, uptake_sinks=tuple(sinks))

    elif mapping.target is ModelEffectTarget.DECAY_RATE:
        if mapping.target_identifier is not None:
            raise ValueError("decay-rate mapping must not set target_identifier")
        effective, audit = _multiply_parameter(transport.decay, effect)
        updated = replace(transport, decay=effective)

    else:
        raise ValueError(
            f"model effect target {mapping.target.value!r} is not executable "
            "in the transport composition layer"
        )

    audit = replace(audit, population_id=population.population_id)
    return replace(population, transport=updated), audit


def apply_model_effects(
    experiment: EVPopulationExperiment,
    study: PerturbationStudy,
) -> ResolvedPopulationExperiment:
    """Apply only explicit executable mappings; observational effects stay inert."""

    if not isinstance(experiment, EVPopulationExperiment):
        raise TypeError("experiment must be an EVPopulationExperiment")
    if not isinstance(study, PerturbationStudy):
        raise TypeError("study must be a PerturbationStudy")

    populations = list(experiment.populations)
    by_phenotype = {
        item.phenotype_id: index for index, item in enumerate(populations)
    }
    applied: list[AppliedModelEffect] = []

    for effect in study.effects:
        if effect.model_mapping is None:
            continue
        if effect.phenotype_id is None:
            raise ValueError(
                f"mapped effect {effect.identifier!r} requires phenotype_id"
            )
        population_index = by_phenotype.get(effect.phenotype_id)
        if population_index is None:
            raise ValueError(
                f"mapped effect {effect.identifier!r} references phenotype "
                f"{effect.phenotype_id!r} that is not simulated"
            )
        population, audit = _apply_one(populations[population_index], effect)
        populations[population_index] = population
        applied.append(audit)

    return ResolvedPopulationExperiment(
        experiment=replace(experiment, populations=tuple(populations)),
        applied_effects=tuple(applied),
    )
