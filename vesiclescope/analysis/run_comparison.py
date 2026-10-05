"""Engine-independent endpoint comparison for completed VesicleScope runs."""

from __future__ import annotations

from dataclasses import dataclass

from vesiclescope.run_bundles import SimulationRunBundle


@dataclass(frozen=True, slots=True)
class RunComparisonSummary:
    left_experiment_id: str
    right_experiment_id: str
    quantity_unit: str
    left_grid_spacing_micron: float
    right_grid_spacing_micron: float
    left_time_step_min: float
    right_time_step_min: float
    left_final_extracellular_quantity: float
    right_final_extracellular_quantity: float
    extracellular_delta: float
    left_final_internalized_quantity: float
    right_final_internalized_quantity: float
    internalized_delta: float
    extracellular_ratio_right_over_left: float | None
    internalized_ratio_right_over_left: float | None


def compare_run_bundles(
    left: SimulationRunBundle,
    right: SimulationRunBundle,
) -> RunComparisonSummary:
    """Compare final normalized quantities without assigning biological preference."""

    if left.result.integrated_quantity_unit != right.result.integrated_quantity_unit:
        raise ValueError("run bundles use incompatible extracellular quantity units")
    if left.result.internalized_quantity_unit != right.result.internalized_quantity_unit:
        raise ValueError("run bundles use incompatible internalized quantity units")
    if left.result.integrated_quantity_unit != left.result.internalized_quantity_unit:
        raise ValueError("left run uses different extracellular/internalized quantity units")
    if right.result.integrated_quantity_unit != right.result.internalized_quantity_unit:
        raise ValueError("right run uses different extracellular/internalized quantity units")
    if not left.result.samples or not right.result.samples:
        raise ValueError("run comparison requires at least one sample in each bundle")

    left_final = left.result.samples[-1]
    right_final = right.result.samples[-1]
    left_extra = left_final.integrated_field_quantity
    right_extra = right_final.integrated_field_quantity
    left_internal = left_final.internalized_field_quantity
    right_internal = right_final.internalized_field_quantity

    return RunComparisonSummary(
        left_experiment_id=left.experiment.experiment_id,
        right_experiment_id=right.experiment.experiment_id,
        quantity_unit=left.result.integrated_quantity_unit,
        left_grid_spacing_micron=left.numerics.grid_spacing_micron,
        right_grid_spacing_micron=right.numerics.grid_spacing_micron,
        left_time_step_min=left.numerics.time_step_min,
        right_time_step_min=right.numerics.time_step_min,
        left_final_extracellular_quantity=left_extra,
        right_final_extracellular_quantity=right_extra,
        extracellular_delta=right_extra - left_extra,
        left_final_internalized_quantity=left_internal,
        right_final_internalized_quantity=right_internal,
        internalized_delta=right_internal - left_internal,
        extracellular_ratio_right_over_left=(
            None if left_extra == 0.0 else right_extra / left_extra
        ),
        internalized_ratio_right_over_left=(
            None if left_internal == 0.0 else right_internal / left_internal
        ),
    )
