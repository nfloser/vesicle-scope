"""Engine-independent endpoint for the controlled diffusion × uptake experiment."""

from __future__ import annotations

from dataclasses import dataclass
import math

from vesiclescope.domain import BoundaryCondition
from vesiclescope.engines import BioFVMRunResult
from vesiclescope.scenarios.diffusion_uptake import DiffusionUptakeCondition


@dataclass(frozen=True, slots=True)
class DiffusionUptakeSummary:
    diffusion_factor: float
    uptake_factor: float
    diffusion_value: float
    diffusion_unit: str
    uptake_value: float
    uptake_unit: str
    total_released_quantity: float
    final_extracellular_quantity: float
    final_internalized_quantity: float
    extracellular_fraction: float
    internalized_fraction: float
    quantity_unit: str


def analyze_diffusion_uptake_condition(
    condition: DiffusionUptakeCondition,
    result: BioFVMRunResult,
    *,
    conservation_tolerance: float = 5e-3,
) -> DiffusionUptakeSummary:
    """Calculate the synthetic endpoint without depending on native BioFVM state."""

    experiment = condition.experiment
    if result.experiment_id != experiment.experiment_id:
        raise ValueError("result experiment_id does not match condition experiment_id")
    if experiment.boundary is not BoundaryCondition.NO_FLUX:
        raise ValueError("conservation endpoint requires no-flux boundaries")
    if experiment.decay.value != 0.0:
        raise ValueError("conservation endpoint requires zero decay")
    if experiment.initial_concentration.value != 0.0:
        raise ValueError("conservation endpoint requires zero initial concentration")
    if not experiment.release_sources:
        raise ValueError("conservation endpoint requires a declared release source")
    if not experiment.uptake_sinks:
        raise ValueError("conservation endpoint requires recipient uptake sinks")
    if not result.samples:
        raise ValueError("normalized result contains no samples")

    final = result.samples[-1]
    if not math.isclose(final.time_min, experiment.duration_min, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("normalized result does not contain the experiment final time")

    total_released = sum(
        source.release_rate.value * experiment.duration_min
        for source in experiment.release_sources
    )
    if total_released <= 0.0:
        raise ValueError("total released quantity must be positive")

    extracellular = final.integrated_field_quantity
    internalized = final.internalized_field_quantity
    if result.integrated_quantity_unit != result.internalized_quantity_unit:
        raise ValueError("extracellular and internalized quantity units must match")

    accounted = extracellular + internalized
    relative_error = abs(accounted - total_released) / total_released
    if relative_error > conservation_tolerance:
        raise ValueError(
            "conservation endpoint does not close within tolerance: "
            f"relative error {relative_error:.6g}"
        )

    uptake_values = {sink.uptake_rate.value for sink in experiment.uptake_sinks}
    uptake_units = {sink.uptake_rate.unit for sink in experiment.uptake_sinks}
    if len(uptake_values) != 1 or len(uptake_units) != 1:
        raise ValueError("factor experiment requires one common recipient uptake value")

    return DiffusionUptakeSummary(
        diffusion_factor=condition.diffusion_factor,
        uptake_factor=condition.uptake_factor,
        diffusion_value=experiment.diffusion.value,
        diffusion_unit=experiment.diffusion.unit,
        uptake_value=next(iter(uptake_values)),
        uptake_unit=next(iter(uptake_units)),
        total_released_quantity=total_released,
        final_extracellular_quantity=extracellular,
        final_internalized_quantity=internalized,
        extracellular_fraction=extracellular / total_released,
        internalized_fraction=internalized / total_released,
        quantity_unit=result.integrated_quantity_unit,
    )
