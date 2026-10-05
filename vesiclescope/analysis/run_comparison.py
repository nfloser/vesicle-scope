"""Engine-independent comparison for completed VesicleScope runs."""

from __future__ import annotations

from dataclasses import dataclass
import math

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


@dataclass(frozen=True, slots=True)
class StoredQuantitySample:
    """One stored normalized quantity sample; no interpolation is implied."""

    time_min: float
    extracellular_quantity: float
    internalized_quantity: float


@dataclass(frozen=True, slots=True)
class SpatialDifferenceSummary:
    """Direct final-field subtraction when stored grids are exactly compatible."""

    compatible: bool
    reason: str | None
    nx: int | None
    ny: int | None
    concentration_unit: str | None
    time_min: float | None
    values: tuple[float, ...]
    minimum_difference: float | None
    maximum_difference: float | None
    mean_absolute_difference: float | None


@dataclass(frozen=True, slots=True)
class DetailedRunComparison:
    """Stored-run comparison with endpoint, time-series and optional spatial detail."""

    endpoint: RunComparisonSummary
    left_revision: str
    right_revision: str
    left_engine: str
    right_engine: str
    left_physicell_release: str
    right_physicell_release: str
    left_biofvm_version: str
    right_biofvm_version: str
    left_series: tuple[StoredQuantitySample, ...]
    right_series: tuple[StoredQuantitySample, ...]
    spatial: SpatialDifferenceSummary


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


def _series(bundle: SimulationRunBundle) -> tuple[StoredQuantitySample, ...]:
    return tuple(
        StoredQuantitySample(
            time_min=sample.time_min,
            extracellular_quantity=sample.integrated_field_quantity,
            internalized_quantity=sample.internalized_field_quantity,
        )
        for sample in bundle.result.samples
    )


def _spatial_incompatibility(
    left: SimulationRunBundle,
    right: SimulationRunBundle,
) -> str | None:
    if left.result.concentration_unit != right.result.concentration_unit:
        return "concentration unit mismatch"
    if not left.result.field_snapshots or not right.result.field_snapshots:
        return "final spatial field is missing"
    if left.result.grid.nx != right.result.grid.nx or left.result.grid.ny != right.result.grid.ny:
        return "grid dimensions differ"
    if not math.isclose(
        left.result.grid.grid_spacing_micron,
        right.result.grid.grid_spacing_micron,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        return "grid spacing differs"
    if not math.isclose(
        left.result.grid.slice_thickness_micron,
        right.result.grid.slice_thickness_micron,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        return "grid slice thickness differs"
    if not math.isclose(
        left.experiment.domain.width_micron,
        right.experiment.domain.width_micron,
        rel_tol=0.0,
        abs_tol=1e-12,
    ) or not math.isclose(
        left.experiment.domain.height_micron,
        right.experiment.domain.height_micron,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        return "physical domain dimensions differ"
    if not math.isclose(
        left.result.field_snapshots[-1].time_min,
        right.result.field_snapshots[-1].time_min,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        return "final spatial snapshot times differ"
    return None


def _spatial_difference(
    left: SimulationRunBundle,
    right: SimulationRunBundle,
) -> SpatialDifferenceSummary:
    reason = _spatial_incompatibility(left, right)
    if reason is not None:
        return SpatialDifferenceSummary(
            compatible=False,
            reason=reason,
            nx=None,
            ny=None,
            concentration_unit=None,
            time_min=None,
            values=(),
            minimum_difference=None,
            maximum_difference=None,
            mean_absolute_difference=None,
        )

    left_snapshot = left.result.field_snapshots[-1]
    right_snapshot = right.result.field_snapshots[-1]
    if len(left_snapshot.values) != len(right_snapshot.values):
        return SpatialDifferenceSummary(
            compatible=False,
            reason="spatial field lengths differ",
            nx=None,
            ny=None,
            concentration_unit=None,
            time_min=None,
            values=(),
            minimum_difference=None,
            maximum_difference=None,
            mean_absolute_difference=None,
        )

    values = tuple(
        right_value - left_value
        for left_value, right_value in zip(left_snapshot.values, right_snapshot.values)
    )
    return SpatialDifferenceSummary(
        compatible=True,
        reason=None,
        nx=left.result.grid.nx,
        ny=left.result.grid.ny,
        concentration_unit=left.result.concentration_unit,
        time_min=left_snapshot.time_min,
        values=values,
        minimum_difference=min(values),
        maximum_difference=max(values),
        mean_absolute_difference=sum(abs(value) for value in values) / len(values),
    )


def compare_run_bundles_detailed(
    left: SimulationRunBundle,
    right: SimulationRunBundle,
) -> DetailedRunComparison:
    """Compare stored runs without interpolation, resampling or biological ranking."""

    endpoint = compare_run_bundles(left, right)
    return DetailedRunComparison(
        endpoint=endpoint,
        left_revision=left.vesiclescope_revision,
        right_revision=right.vesiclescope_revision,
        left_engine=left.result.engine.engine,
        right_engine=right.result.engine.engine,
        left_physicell_release=left.result.engine.physicell_release,
        right_physicell_release=right.result.engine.physicell_release,
        left_biofvm_version=left.result.engine.biofvm_version,
        right_biofvm_version=right.result.engine.biofvm_version,
        left_series=_series(left),
        right_series=_series(right),
        spatial=_spatial_difference(left, right),
    )
