"""Reproducible figure for synthetic finite-donor boundary-profile analysis."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from vesiclescope.analysis import (
    analyze_donor_boundary_profile,
    fixed_width_distance_edges,
)
from vesiclescope.domain import CircularReleaseSource, TransportExperiment
from vesiclescope.engines import BioFVMRunResult


_TITLE = "Synthetic donor-boundary transport verification"
_FIVE_MICRON_LABEL = "5 micron public-code bins"
_TEN_MICRON_LABEL = "10 micron paper-described zones"


def _display_concentration_unit(unit: str) -> str:
    if unit == "particle_equivalent/micron^3":
        return "particle equiv. / µm³"
    return unit


@dataclass(frozen=True, slots=True)
class DonorBoundaryFigureData:
    """Validated renderer-neutral data derived from one normalized simulation field."""

    heatmap_rows: tuple[tuple[float, ...], ...]
    heatmap_time_min: float
    domain_width_micron: float
    domain_height_micron: float
    donor_position_micron: tuple[float, float]
    donor_radius_micron: float
    max_distance_micron: float
    ring_boundary_distances_micron: tuple[float, ...]
    concentration_unit: str
    quantity_unit: str
    five_micron_bin_width: float
    five_micron_bin_centers: tuple[float, ...]
    five_micron_mean_concentrations: tuple[float, ...]
    ten_micron_bin_width: float
    ten_micron_bin_centers: tuple[float, ...]
    ten_micron_mean_concentrations: tuple[float, ...]


def _profile_centers(profile) -> tuple[float, ...]:
    return tuple(
        (item.lower_bound_micron + item.upper_bound_micron) / 2.0
        for item in profile.bins
    )


def _profile_means(profile) -> tuple[float, ...]:
    return tuple(item.mean_concentration for item in profile.bins)


def prepare_donor_boundary_figure_data(
    experiment: TransportExperiment,
    result: BioFVMRunResult,
    *,
    time_min: float,
    max_distance_micron: float,
) -> DonorBoundaryFigureData:
    """Prepare one spatial field plus 5/10-micron radial views of that same field."""

    if not isinstance(experiment, TransportExperiment):
        raise TypeError("experiment must be a TransportExperiment")
    if not isinstance(result, BioFVMRunResult):
        raise TypeError("result must be a BioFVMRunResult")
    if result.experiment_id != experiment.experiment_id:
        raise ValueError("figure result experiment_id does not match experiment")
    if len(experiment.release_sources) != 1 or not isinstance(
        experiment.release_sources[0],
        CircularReleaseSource,
    ):
        raise ValueError("donor-boundary figure requires one CircularReleaseSource")

    five_edges = fixed_width_distance_edges(
        max_distance_micron=max_distance_micron,
        bin_width_micron=5.0,
    )
    ten_edges = fixed_width_distance_edges(
        max_distance_micron=max_distance_micron,
        bin_width_micron=10.0,
    )
    if not math.isclose(
        five_edges[-1],
        ten_edges[-1],
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("5 and 10 micron profiles must share one radial extent")

    five_profile = analyze_donor_boundary_profile(
        experiment,
        result,
        time_min=time_min,
        edges_micron=five_edges,
    )
    ten_profile = analyze_donor_boundary_profile(
        experiment,
        result,
        time_min=time_min,
        edges_micron=ten_edges,
    )
    if not math.isclose(
        five_profile.time_min,
        ten_profile.time_min,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("5 and 10 micron profiles must describe one sample time")
    if (
        five_profile.concentration_unit != ten_profile.concentration_unit
        or five_profile.quantity_unit != ten_profile.quantity_unit
    ):
        raise ValueError("5 and 10 micron profile units must match")

    matching_fields = tuple(
        snapshot
        for snapshot in result.field_snapshots
        if math.isclose(
            snapshot.time_min,
            five_profile.time_min,
            rel_tol=0.0,
            abs_tol=1e-9,
        )
    )
    if len(matching_fields) != 1:
        raise ValueError("figure time must identify exactly one normalized field")
    field = matching_fields[0]
    grid = result.grid
    if len(field.values) != grid.voxel_count:
        raise ValueError("figure field length does not match normalized grid")

    if not math.isclose(
        grid.nx * grid.grid_spacing_micron,
        experiment.domain.width_micron,
        rel_tol=0.0,
        abs_tol=1e-9,
    ) or not math.isclose(
        grid.ny * grid.grid_spacing_micron,
        experiment.domain.height_micron,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("figure grid extent does not match experiment domain")

    rows = tuple(
        tuple(field.values[index * grid.nx : (index + 1) * grid.nx])
        for index in range(grid.ny)
    )

    donor = experiment.release_sources[0]
    ring_distances = tuple(
        20.0 * index
        for index in range(1, int(five_edges[-1] // 20.0) + 1)
    )
    if not ring_distances or not math.isclose(
        ring_distances[-1],
        five_edges[-1],
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        ring_distances = (*ring_distances, five_edges[-1])

    return DonorBoundaryFigureData(
        heatmap_rows=rows,
        heatmap_time_min=field.time_min,
        domain_width_micron=experiment.domain.width_micron,
        domain_height_micron=experiment.domain.height_micron,
        donor_position_micron=(donor.x_micron, donor.y_micron),
        donor_radius_micron=donor.footprint_radius_micron,
        max_distance_micron=five_edges[-1],
        ring_boundary_distances_micron=ring_distances,
        concentration_unit=five_profile.concentration_unit,
        quantity_unit=five_profile.quantity_unit,
        five_micron_bin_width=5.0,
        five_micron_bin_centers=_profile_centers(five_profile),
        five_micron_mean_concentrations=_profile_means(five_profile),
        ten_micron_bin_width=10.0,
        ten_micron_bin_centers=_profile_centers(ten_profile),
        ten_micron_mean_concentrations=_profile_means(ten_profile),
    )


def render_donor_boundary_figure(
    experiment: TransportExperiment,
    result: BioFVMRunResult,
    output_path: Path,
    *,
    time_min: float,
    max_distance_micron: float = 80.0,
) -> Path:
    """Render the reviewed two-panel donor-boundary figure as SVG."""

    output = Path(output_path)
    if output.suffix.lower() != ".svg":
        raise ValueError("donor-boundary figure output path must end in .svg")

    data = prepare_donor_boundary_figure_data(
        experiment,
        result,
        time_min=time_min,
        max_distance_micron=max_distance_micron,
    )

    try:
        import matplotlib
    except ImportError as exc:
        raise RuntimeError(
            "Matplotlib is required for figure rendering; "
            "install requirements-figures.txt"
        ) from exc

    matplotlib.use("Agg", force=True)
    from matplotlib import pyplot as plt
    from matplotlib.patches import Circle

    output.parent.mkdir(parents=True, exist_ok=True)

    with matplotlib.rc_context(
        {
            "svg.hashsalt": "vesiclescope-donor-boundary-figure",
            "svg.fonttype": "none",
        }
    ):
        figure, axes = plt.subplots(1, 2, figsize=(12.2, 5.2))
        field_axis, radial_axis = axes

        image = field_axis.imshow(
            data.heatmap_rows,
            origin="lower",
            interpolation="nearest",
            extent=(
                0.0,
                data.domain_width_micron,
                0.0,
                data.domain_height_micron,
            ),
            aspect="equal",
        )
        donor = Circle(
            data.donor_position_micron,
            radius=data.donor_radius_micron,
            facecolor="none",
            edgecolor="black",
            linewidth=1.6,
            label="Finite donor boundary",
        )
        donor.set_gid("donor-boundary")
        field_axis.add_patch(donor)

        for distance in data.ring_boundary_distances_micron:
            ring = Circle(
                data.donor_position_micron,
                radius=data.donor_radius_micron + distance,
                facecolor="none",
                edgecolor="black",
                linewidth=0.7,
                linestyle="--",
                alpha=0.5,
            )
            ring.set_gid(f"boundary-ring-{int(distance):d}")
            field_axis.add_patch(ring)

        field_axis.set_xlabel("x [micron]")
        field_axis.set_ylabel("y [micron]")
        field_axis.set_title(
            f"Simulated extracellular field at {data.heatmap_time_min:g} min"
        )
        field_axis.legend(loc="upper right")
        display_unit = _display_concentration_unit(data.concentration_unit)
        colorbar = figure.colorbar(image, ax=field_axis)
        colorbar.set_label(f"Simulated concentration [{display_unit}]")

        radial_axis.plot(
            data.five_micron_bin_centers,
            data.five_micron_mean_concentrations,
            marker="o",
            markersize=3,
            label=_FIVE_MICRON_LABEL,
        )
        radial_axis.plot(
            data.ten_micron_bin_centers,
            data.ten_micron_mean_concentrations,
            marker="s",
            markersize=4,
            label=_TEN_MICRON_LABEL,
        )
        radial_axis.set_xlabel("Distance from finite donor boundary [micron]")
        radial_axis.set_ylabel(
            f"Mean simulated concentration [{display_unit}]"
        )
        radial_axis.set_title("Same field, two explicit radial binnings")
        radial_axis.set_xlim(0.0, data.max_distance_micron)
        radial_axis.grid(True, alpha=0.25)
        radial_axis.legend()

        figure.suptitle(_TITLE)
        figure.text(
            0.5,
            0.012,
            "Synthetic parameters and voxel-center boundary classification; "
            "simulated concentration, not experimental evidence. "
            f"Normalized unit: {data.concentration_unit}.",
            ha="center",
        )
        figure.tight_layout(rect=(0.0, 0.055, 1.0, 0.94))
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
