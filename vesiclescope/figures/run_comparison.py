"""Publication-ready comparison of exact snapshots from two stored run bundles."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from vesiclescope.analysis import compare_spatial_snapshots
from vesiclescope.engines import SpatialFieldSnapshot2D
from vesiclescope.run_bundles import SimulationRunBundle


_TITLE = "VesicleScope stored-run comparison"


@dataclass(frozen=True, slots=True)
class RunComparisonFigureData:
    left_name: str
    right_name: str
    left_experiment_id: str
    right_experiment_id: str
    left_revision: str
    right_revision: str
    left_engine_label: str
    right_engine_label: str
    scientific_status: str
    concentration_unit: str
    quantity_unit: str
    left_time_min: float
    right_time_min: float
    left_rows: tuple[tuple[float, ...], ...]
    right_rows: tuple[tuple[float, ...], ...]
    difference_rows: tuple[tuple[float, ...], ...]
    shared_maximum: float
    difference_limit: float
    domain_width_micron: float
    domain_height_micron: float
    left_sample_times_min: tuple[float, ...]
    right_sample_times_min: tuple[float, ...]
    left_extracellular: tuple[float, ...]
    right_extracellular: tuple[float, ...]
    left_internalized: tuple[float, ...]
    right_internalized: tuple[float, ...]


def _exact_snapshot(
    bundle: SimulationRunBundle,
    time_min: float,
    side: str,
) -> SpatialFieldSnapshot2D:
    matches = tuple(
        snapshot
        for snapshot in bundle.result.field_snapshots
        if math.isclose(snapshot.time_min, time_min, rel_tol=0.0, abs_tol=1e-9)
    )
    if len(matches) != 1:
        raise ValueError(
            f"{side} spatial snapshot at {time_min:g} min is not stored exactly"
        )
    return matches[0]


def _rows(
    snapshot: SpatialFieldSnapshot2D,
    nx: int,
    ny: int,
) -> tuple[tuple[float, ...], ...]:
    if len(snapshot.values) != nx * ny:
        raise ValueError("stored field length does not match the normalized grid")
    return tuple(
        tuple(snapshot.values[row * nx : (row + 1) * nx])
        for row in range(ny)
    )


def _evidence_categories(bundle: SimulationRunBundle) -> set[str]:
    experiment = bundle.experiment
    return {
        experiment.diffusion.evidence.value,
        experiment.decay.evidence.value,
        experiment.initial_concentration.evidence.value,
        *(source.release_rate.evidence.value for source in experiment.release_sources),
        *(sink.uptake_rate.evidence.value for sink in experiment.uptake_sinks),
    }


def prepare_run_comparison_figure_data(
    left: SimulationRunBundle,
    left_time_min: float,
    right: SimulationRunBundle,
    right_time_min: float,
    *,
    left_name: str = "left run",
    right_name: str = "right run",
) -> RunComparisonFigureData:
    """Prepare an exact stored-state comparison without interpolation or resampling."""

    if not isinstance(left, SimulationRunBundle) or not isinstance(
        right, SimulationRunBundle
    ):
        raise TypeError("left and right must be SimulationRunBundle instances")
    left_snapshot = _exact_snapshot(left, left_time_min, "left")
    right_snapshot = _exact_snapshot(right, right_time_min, "right")
    spatial = compare_spatial_snapshots(
        left,
        left_time_min,
        right,
        right_time_min,
    )
    if not spatial.compatible:
        raise ValueError(f"comparison figure requires compatible fields: {spatial.reason}")
    if (
        left.result.integrated_quantity_unit
        != right.result.integrated_quantity_unit
    ):
        raise ValueError("comparison figure requires matching quantity units")
    if left.result.internalized_quantity_unit != left.result.integrated_quantity_unit:
        raise ValueError("left extracellular and internalized quantity units differ")
    if right.result.internalized_quantity_unit != right.result.integrated_quantity_unit:
        raise ValueError("right extracellular and internalized quantity units differ")

    grid = left.result.grid
    all_values = tuple(
        value
        for bundle in (left, right)
        for snapshot in bundle.result.field_snapshots
        for value in snapshot.values
    )
    if not all_values:
        raise ValueError("comparison figure requires stored spatial fields")
    shared_maximum = max(all_values)
    if shared_maximum < 0.0:
        raise ValueError("comparison figure requires non-negative concentration fields")
    difference_limit = max((abs(value) for value in spatial.values), default=0.0)

    evidence = _evidence_categories(left) | _evidence_categories(right)
    status = (
        "synthetic benchmark; not experimental evidence"
        if evidence == {"synthetic_benchmark"}
        else "simulation with mixed or evidence-backed inputs; not biological truth"
    )
    return RunComparisonFigureData(
        left_name=left_name,
        right_name=right_name,
        left_experiment_id=left.experiment.experiment_id,
        right_experiment_id=right.experiment.experiment_id,
        left_revision=left.vesiclescope_revision,
        right_revision=right.vesiclescope_revision,
        left_engine_label=(
            f"{left.result.engine.engine}; PhysiCell {left.result.engine.physicell_release}; "
            f"BioFVM {left.result.engine.biofvm_version}"
        ),
        right_engine_label=(
            f"{right.result.engine.engine}; PhysiCell {right.result.engine.physicell_release}; "
            f"BioFVM {right.result.engine.biofvm_version}"
        ),
        scientific_status=status,
        concentration_unit=left.result.concentration_unit,
        quantity_unit=left.result.integrated_quantity_unit,
        left_time_min=left_snapshot.time_min,
        right_time_min=right_snapshot.time_min,
        left_rows=_rows(left_snapshot, grid.nx, grid.ny),
        right_rows=_rows(right_snapshot, grid.nx, grid.ny),
        difference_rows=tuple(
            tuple(spatial.values[row * grid.nx : (row + 1) * grid.nx])
            for row in range(grid.ny)
        ),
        shared_maximum=shared_maximum,
        difference_limit=difference_limit,
        domain_width_micron=left.experiment.domain.width_micron,
        domain_height_micron=left.experiment.domain.height_micron,
        left_sample_times_min=tuple(
            sample.time_min for sample in left.result.samples
        ),
        right_sample_times_min=tuple(
            sample.time_min for sample in right.result.samples
        ),
        left_extracellular=tuple(
            sample.integrated_field_quantity for sample in left.result.samples
        ),
        right_extracellular=tuple(
            sample.integrated_field_quantity for sample in right.result.samples
        ),
        left_internalized=tuple(
            sample.internalized_field_quantity for sample in left.result.samples
        ),
        right_internalized=tuple(
            sample.internalized_field_quantity for sample in right.result.samples
        ),
    )


def render_run_comparison_figure(
    left: SimulationRunBundle,
    left_time_min: float,
    right: SimulationRunBundle,
    right_time_min: float,
    output_path: Path,
    *,
    left_name: str = "left run",
    right_name: str = "right run",
) -> Path:
    output = Path(output_path)
    if output.suffix.lower() != ".svg":
        raise ValueError("run comparison figure output path must end in .svg")
    data = prepare_run_comparison_figure_data(
        left,
        left_time_min,
        right,
        right_time_min,
        left_name=left_name,
        right_name=right_name,
    )
    try:
        import matplotlib
    except ImportError as exc:
        raise RuntimeError(
            "Matplotlib is required for figure rendering; install vesicle-scope[figures]"
        ) from exc

    matplotlib.use("Agg", force=True)
    from matplotlib import pyplot as plt
    from matplotlib.colors import Normalize

    output.parent.mkdir(parents=True, exist_ok=True)
    with matplotlib.rc_context(
        {"svg.hashsalt": "vesiclescope-run-comparison", "svg.fonttype": "none"}
    ):
        figure = plt.figure(figsize=(14.0, 9.0))
        grid = figure.add_gridspec(2, 6, height_ratios=(1.05, 0.85))
        left_axis = figure.add_subplot(grid[0, 0:2])
        right_axis = figure.add_subplot(grid[0, 2:4])
        difference_axis = figure.add_subplot(grid[0, 4:6])
        extracellular_axis = figure.add_subplot(grid[1, 0:3])
        internalized_axis = figure.add_subplot(grid[1, 3:6])
        extent = (0.0, data.domain_width_micron, 0.0, data.domain_height_micron)
        shared_norm = Normalize(
            vmin=0.0,
            vmax=data.shared_maximum if data.shared_maximum > 0.0 else 1e-15,
        )
        images = []
        for axis, rows, name, time_min in (
            (left_axis, data.left_rows, data.left_name, data.left_time_min),
            (right_axis, data.right_rows, data.right_name, data.right_time_min),
        ):
            images.append(
                axis.imshow(
                    rows,
                    origin="lower",
                    interpolation="nearest",
                    extent=extent,
                    aspect="equal",
                    norm=shared_norm,
                    cmap="viridis",
                )
            )
            axis.set_title(f"{name}\nstored t = {time_min:g} min")
            axis.set_xlabel("x [micron]")
            axis.set_ylabel("y [micron]")
        colorbar = figure.colorbar(images[0], ax=[left_axis, right_axis], shrink=0.78)
        colorbar.set_label(f"Concentration [{data.concentration_unit}]")

        rendered_difference_limit = (
            data.difference_limit
            if data.difference_limit > 0.0
            else max(data.shared_maximum * 1e-12, 1e-15)
        )
        difference = difference_axis.imshow(
            data.difference_rows,
            origin="lower",
            interpolation="nearest",
            extent=extent,
            aspect="equal",
            cmap="RdBu_r",
            vmin=-rendered_difference_limit,
            vmax=rendered_difference_limit,
        )
        difference_axis.set_title(
            "Difference: right − left\n"
            + (
                "all stored differences are exactly zero"
                if data.difference_limit == 0.0
                else "positive means higher on right"
            )
        )
        difference_axis.set_xlabel("x [micron]")
        difference_axis.set_ylabel("y [micron]")
        difference_colorbar = figure.colorbar(difference, ax=difference_axis, shrink=0.78)
        difference_colorbar.set_label(f"Δ concentration [{data.concentration_unit}]")

        for axis, left_values, right_values, title in (
            (
                extracellular_axis,
                data.left_extracellular,
                data.right_extracellular,
                "Extracellular quantity",
            ),
            (
                internalized_axis,
                data.left_internalized,
                data.right_internalized,
                "Internalized quantity",
            ),
        ):
            axis.plot(data.left_sample_times_min, left_values, marker="o", label="Left")
            axis.plot(data.right_sample_times_min, right_values, marker="o", label="Right")
            axis.axvline(data.left_time_min, color="#555555", linestyle="--", alpha=0.65)
            axis.set_title(title)
            axis.set_xlabel("Time [min]")
            axis.set_ylabel(f"Model quantity [{data.quantity_unit}]")
            axis.grid(True, alpha=0.25)
            axis.legend()

        figure.suptitle(_TITLE)
        figure.text(
            0.5,
            0.055,
            f"Stable shared concentration scale: 0 to {data.shared_maximum:g} {data.concentration_unit}",
            ha="center",
        )
        figure.text(0.5, 0.033, data.scientific_status, ha="center")
        figure.text(
            0.5,
            0.012,
            (
                f"Left {data.left_experiment_id}: {data.left_engine_label}; revision {data.left_revision}. "
                f"Right {data.right_experiment_id}: {data.right_engine_label}; revision {data.right_revision}. "
                "Exact stored snapshots; no interpolation."
            ),
            ha="center",
            fontsize=7,
        )
        figure.subplots_adjust(
            left=0.065,
            right=0.965,
            top=0.88,
            bottom=0.11,
            wspace=0.9,
            hspace=0.42,
        )
        figure.savefig(
            output,
            format="svg",
            metadata={
                "Creator": "VesicleScope",
                "Date": None,
                "Description": _TITLE,
            },
        )
        plt.close(figure)
    return output
