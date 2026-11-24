"""Run one experiment with and without exposure-driven rate schedules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from vesiclescope.domain import BiologicalExposure, RateSchedule, TransportExperiment
from vesiclescope.dose_response import (
    DoseResponseTarget,
    EffectCompartmentDoseResponse,
    dose_response_rate_schedule,
)
from vesiclescope.engines.biofvm import BioFVMNumerics, BioFVMRunResult, run_transport


@dataclass(frozen=True, slots=True)
class DoseResponseCondition:
    label: str
    response: EffectCompartmentDoseResponse
    schedule: RateSchedule
    experiment: TransportExperiment
    result: BioFVMRunResult


@dataclass(frozen=True, slots=True)
class DoseResponseComparison:
    exposure: BiologicalExposure
    baseline_experiment: TransportExperiment
    baseline_result: BioFVMRunResult
    conditions: tuple[DoseResponseCondition, ...]

    def internalization_rate_ratio(
        self, condition: DoseResponseCondition
    ) -> tuple[tuple[float, float], ...]:
        """(interval midpoint, perturbed/baseline internalization rate) per sample interval."""

        ratios = []
        base = self.baseline_result.samples
        pert = condition.result.samples
        for i in range(1, len(base)):
            dt = base[i].time_min - base[i - 1].time_min
            b = (base[i].internalized_field_quantity - base[i - 1].internalized_field_quantity) / dt
            p = (pert[i].internalized_field_quantity - pert[i - 1].internalized_field_quantity) / dt
            if b > 0.0:
                ratios.append((0.5 * (base[i].time_min + base[i - 1].time_min), p / b))
        return tuple(ratios)


def run_dose_response_comparison(
    *,
    experiment: TransportExperiment,
    exposure: BiologicalExposure,
    responses: tuple[tuple[str, EffectCompartmentDoseResponse], ...],
    numerics: BioFVMNumerics,
    runner: Path,
    segment_min: float,
) -> DoseResponseComparison:
    """Run the baseline and one schedule-driven variant per labelled response."""

    if experiment.release_schedule is not None or experiment.uptake_schedule is not None:
        raise ValueError("baseline experiment must not already carry rate schedules")
    baseline_result = run_transport(experiment, numerics, Path(runner))
    conditions = []
    for index, (label, response) in enumerate(responses):
        schedule = dose_response_rate_schedule(
            response,
            exposure,
            duration_min=experiment.duration_min,
            segment_min=segment_min,
        )
        field = (
            "release_schedule"
            if response.target is DoseResponseTarget.RELEASE_RATE
            else "uptake_schedule"
        )
        variant = replace(
            experiment,
            experiment_id=f"{experiment.experiment_id}.dose-response.{index + 1}",
            **{field: schedule},
        )
        conditions.append(
            DoseResponseCondition(
                label=label,
                response=response,
                schedule=schedule,
                experiment=variant,
                result=run_transport(variant, numerics, Path(runner)),
            )
        )
    return DoseResponseComparison(
        exposure=exposure,
        baseline_experiment=experiment,
        baseline_result=baseline_result,
        conditions=tuple(conditions),
    )
