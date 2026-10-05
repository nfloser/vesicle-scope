"""Engine-independent empirical uncertainty summaries from stored run bundles."""

from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import fmean, median

from vesiclescope.run_bundles import SimulationRunBundle


_MIN_MEMBERS_FOR_95_PERCENTILE_INTERVAL = 40


@dataclass(frozen=True, slots=True)
class EmpiricalQuantitySummary:
    """Descriptive statistics for one explicitly supplied run ensemble."""

    member_count: int
    minimum: float
    maximum: float
    mean: float
    median: float
    empirical_percentile_interval_95: tuple[float, float] | None


@dataclass(frozen=True, slots=True)
class RunEnsembleSummary:
    """Auditable final-endpoint summary across stored VesicleScope runs."""

    member_experiment_ids: tuple[str, ...]
    quantity_unit: str
    final_extracellular: EmpiricalQuantitySummary
    final_internalized: EmpiricalQuantitySummary


def _linear_quantile(values: tuple[float, ...], probability: float) -> float:
    ordered = tuple(sorted(values))
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _summarize(values: tuple[float, ...]) -> EmpiricalQuantitySummary:
    if not values:
        raise ValueError("uncertainty ensemble must contain at least one value")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("uncertainty ensemble values must be finite")

    interval = None
    if len(values) >= _MIN_MEMBERS_FOR_95_PERCENTILE_INTERVAL:
        interval = (
            _linear_quantile(values, 0.025),
            _linear_quantile(values, 0.975),
        )

    return EmpiricalQuantitySummary(
        member_count=len(values),
        minimum=min(values),
        maximum=max(values),
        mean=fmean(values),
        median=median(values),
        empirical_percentile_interval_95=interval,
    )


def summarize_run_ensemble(
    bundles: tuple[SimulationRunBundle, ...],
) -> RunEnsembleSummary:
    """Summarize final quantities from an explicit finite ensemble of stored runs.

    When at least 40 members are supplied, the returned 95% empirical
    percentile interval uses linear interpolation at the 2.5th and 97.5th
    percentiles. The 40-member reporting guard ensures at least one member per
    nominal 2.5% tail; it is not a claim of statistical adequacy. The interval
    is not a confidence interval and does not imply probability-distribution
    sampling.
    """

    if not isinstance(bundles, tuple):
        raise TypeError("bundles must be a tuple")
    if not bundles:
        raise ValueError("uncertainty ensemble must contain at least one run bundle")
    if not all(isinstance(bundle, SimulationRunBundle) for bundle in bundles):
        raise TypeError("bundles must contain SimulationRunBundle objects")

    member_ids = tuple(bundle.experiment.experiment_id for bundle in bundles)
    if len(set(member_ids)) != len(member_ids):
        raise ValueError("uncertainty ensemble experiment IDs must be unique")

    quantity_units = {
        bundle.result.integrated_quantity_unit
        for bundle in bundles
    } | {
        bundle.result.internalized_quantity_unit
        for bundle in bundles
    }
    if len(quantity_units) != 1:
        raise ValueError("uncertainty ensemble quantity units are incompatible")

    extracellular = tuple(
        bundle.result.samples[-1].integrated_field_quantity
        for bundle in bundles
    )
    internalized = tuple(
        bundle.result.samples[-1].internalized_field_quantity
        for bundle in bundles
    )

    return RunEnsembleSummary(
        member_experiment_ids=member_ids,
        quantity_unit=next(iter(quantity_units)),
        final_extracellular=_summarize(extracellular),
        final_internalized=_summarize(internalized),
    )
