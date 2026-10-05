"""Provenance-safe derivation of user-defined synthetic experiment variants."""

from __future__ import annotations

from dataclasses import replace

from vesiclescope.domain import EvidenceCategory, ScientificParameter, TransportExperiment


def _scientific_parameters(
    experiment: TransportExperiment,
) -> tuple[ScientificParameter, ...]:
    return (
        experiment.diffusion,
        experiment.decay,
        experiment.initial_concentration,
        *(source.release_rate for source in experiment.release_sources),
        *(sink.uptake_rate for sink in experiment.uptake_sinks),
    )


def _require_rate_mapping(
    value: dict[str, float],
    *,
    expected_ids: tuple[str, ...],
    field_name: str,
) -> dict[str, float]:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be an object keyed by identifier")
    expected = set(expected_ids)
    observed = set(value)
    if observed != expected:
        missing = sorted(expected - observed)
        unknown = sorted(observed - expected)
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if unknown:
            details.append("unknown=" + ",".join(unknown))
        raise ValueError(
            f"{field_name} keys must exactly match configured identifiers"
            + (": " + "; ".join(details) if details else "")
        )
    return value


def derive_synthetic_experiment(
    experiment: TransportExperiment,
    *,
    experiment_id: str,
    duration_min: float,
    sample_every_min: float,
    diffusion_value: float,
    decay_value: float,
    initial_concentration_value: float,
    release_rates: dict[str, float],
    uptake_rates: dict[str, float],
) -> TransportExperiment:
    """Create a new synthetic variant while preserving units and geometry.

    This boundary intentionally refuses evidence-backed inputs. A future editor
    for measured/literature/fitted parameters needs an explicit provenance
    editing contract rather than inheriting old evidence onto new values.
    """

    if not isinstance(experiment, TransportExperiment):
        raise TypeError("experiment must be a TransportExperiment")
    if experiment_id == experiment.experiment_id:
        raise ValueError(
            "derived experiment_id must differ from the source experiment_id"
        )

    if any(
        parameter.evidence is not EvidenceCategory.SYNTHETIC_BENCHMARK
        for parameter in _scientific_parameters(experiment)
    ):
        raise ValueError(
            "interactive derivation currently supports synthetic_benchmark "
            "experiments only"
        )

    release_rates = _require_rate_mapping(
        release_rates,
        expected_ids=tuple(source.identifier for source in experiment.release_sources),
        field_name="release_rates",
    )
    uptake_rates = _require_rate_mapping(
        uptake_rates,
        expected_ids=tuple(sink.identifier for sink in experiment.uptake_sinks),
        field_name="uptake_rates",
    )

    release_sources = tuple(
        replace(
            source,
            release_rate=replace(
                source.release_rate,
                value=release_rates[source.identifier],
            ),
        )
        for source in experiment.release_sources
    )
    uptake_sinks = tuple(
        replace(
            sink,
            uptake_rate=replace(
                sink.uptake_rate,
                value=uptake_rates[sink.identifier],
            ),
        )
        for sink in experiment.uptake_sinks
    )

    return replace(
        experiment,
        experiment_id=experiment_id,
        duration_min=duration_min,
        sample_every_min=sample_every_min,
        diffusion=replace(experiment.diffusion, value=diffusion_value),
        decay=replace(experiment.decay, value=decay_value),
        initial_concentration=replace(
            experiment.initial_concentration,
            value=initial_concentration_value,
        ),
        release_sources=release_sources,
        uptake_sinks=uptake_sinks,
    )
