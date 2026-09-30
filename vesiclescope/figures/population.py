"""Scientific figure data and rendering for the synthetic recipient-count sweep."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from vesiclescope.analysis import RecipientPopulationSummary
from vesiclescope.domain import TransportExperiment
from vesiclescope.engines import BioFVMRunResult


_SYNTHETIC_TITLE = "Synthetic fixed-grid verification"
_EXPECTED_COUNTS = (2, 4, 8)


@dataclass(frozen=True, slots=True)
class RecipientCountFigureData:
    """Validated, renderer-neutral inputs for the first population figure."""

    recipient_counts: tuple[int, ...]
    planar_densities: tuple[float, ...]
    planar_density_unit: str
    total_internalized_quantities: tuple[float, ...]
    quantity_unit: str
    concentration_unit: str
    heatmap_rows: tuple[tuple[float, ...], ...]
    heatmap_time_min: float
    domain_width_micron: float
    domain_height_micron: float
    donor_position_micron: tuple[float, float]
    recipient_positions_micron: tuple[tuple[float, float], ...]


def _validate_triplet(name: str, value: tuple[object, ...]) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple")
    if len(value) != len(_EXPECTED_COUNTS):
        raise ValueError(f"{name} must contain the 2/4/8 sweep scenarios")


def prepare_recipient_count_figure_data(
    experiments: tuple[TransportExperiment, ...],
    results: tuple[BioFVMRunResult, ...],
    summaries: tuple[RecipientPopulationSummary, ...],
) -> RecipientCountFigureData:
    """Validate public simulation/analysis outputs and prepare figure-ready data."""

    _validate_triplet("experiments", experiments)
    _validate_triplet("results", results)
    _validate_triplet("summaries", summaries)

    if not all(isinstance(item, TransportExperiment) for item in experiments):
        raise TypeError("experiments must contain TransportExperiment objects")
    if not all(isinstance(item, BioFVMRunResult) for item in results):
        raise TypeError("results must contain BioFVMRunResult objects")
    if not all(isinstance(item, RecipientPopulationSummary) for item in summaries):
        raise TypeError("summaries must contain RecipientPopulationSummary objects")

    observed_counts = tuple(len(experiment.uptake_sinks) for experiment in experiments)
    if observed_counts != _EXPECTED_COUNTS:
        raise ValueError(
            f"figure requires recipient-count scenarios {_EXPECTED_COUNTS}, "
            f"observed={observed_counts}"
        )

    reference_domain = experiments[0].domain
    planar_density_unit = summaries[0].planar_density_unit
    quantity_unit = summaries[0].quantity_unit

    for experiment, result, summary, expected_count in zip(
        experiments,
        results,
        summaries,
        _EXPECTED_COUNTS,
    ):
        if result.experiment_id != experiment.experiment_id:
            raise ValueError("figure result experiment_id does not match scenario")
        if experiment.domain != reference_domain:
            raise ValueError("figure scenarios must share one domain")
        if summary.recipient_count != expected_count:
            raise ValueError("figure summary recipient count does not match scenario")
        if summary.planar_density_unit != planar_density_unit:
            raise ValueError("figure summaries must share one planar-density unit")
        if summary.quantity_unit != quantity_unit:
            raise ValueError("figure summaries must share one uptake quantity unit")
        if result.internalized_quantity_unit != quantity_unit:
            raise ValueError("figure result and summary uptake units do not match")
        if not math.isclose(
            summary.time_min,
            experiment.duration_min,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("figure summaries must describe the final scenario time")

        expected_ids = tuple(sink.identifier for sink in experiment.uptake_sinks)
        observed_ids = tuple(recipient.identifier for recipient in summary.recipients)
        if observed_ids != expected_ids:
            raise ValueError("figure summary recipients do not match scenario ordering")

        if not math.isclose(
            summary.total_internalized_quantity,
            result.samples[-1].internalized_field_quantity,
            rel_tol=1e-12,
            abs_tol=1e-8,
        ):
            raise ValueError("figure summary total does not match normalized result")

    heatmap_experiment = experiments[-1]
    heatmap_result = results[-1]
    if len(heatmap_experiment.release_sources) != 1:
        raise ValueError("heatmap scenario must contain exactly one donor")

    if not heatmap_result.field_snapshots:
        raise ValueError("heatmap result contains no spatial field snapshots")
    final_snapshot = heatmap_result.field_snapshots[-1]
    if not math.isclose(
        final_snapshot.time_min,
        heatmap_experiment.duration_min,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("heatmap must use the final normalized field snapshot")

    grid = heatmap_result.grid
    if len(final_snapshot.values) != grid.voxel_count:
        raise ValueError("heatmap field length does not match normalized grid")

    rows = tuple(
        tuple(
            final_snapshot.values[
                row_index * grid.nx : (row_index + 1) * grid.nx
            ]
        )
        for row_index in range(grid.ny)
    )

    donor = heatmap_experiment.release_sources[0]
    return RecipientCountFigureData(
        recipient_counts=_EXPECTED_COUNTS,
        planar_densities=tuple(summary.planar_density for summary in summaries),
        planar_density_unit=planar_density_unit,
        total_internalized_quantities=tuple(
            summary.total_internalized_quantity for summary in summaries
        ),
        quantity_unit=quantity_unit,
        concentration_unit=heatmap_result.concentration_unit,
        heatmap_rows=rows,
        heatmap_time_min=final_snapshot.time_min,
        domain_width_micron=heatmap_experiment.domain.width_micron,
        domain_height_micron=heatmap_experiment.domain.height_micron,
        donor_position_micron=(donor.x_micron, donor.y_micron),
        recipient_positions_micron=tuple(
            (sink.x_micron, sink.y_micron)
            for sink in heatmap_experiment.uptake_sinks
        ),
    )


def render_recipient_count_figure(
    experiments: tuple[TransportExperiment, ...],
    results: tuple[BioFVMRunResult, ...],
    summaries: tuple[RecipientPopulationSummary, ...],
    output_path: Path,
) -> Path:
    """Render the reviewed two-panel synthetic population figure as SVG."""

    output = Path(output_path)
    if output.suffix.lower() != ".svg":
        raise ValueError("population figure output path must end in .svg")

    data = prepare_recipient_count_figure_data(experiments, results, summaries)

    try:
        import matplotlib
    except ImportError as exc:
        raise RuntimeError(
            "Matplotlib is required for figure rendering; "
            "install requirements-figures.txt"
        ) from exc

    matplotlib.use("Agg", force=True)
    from matplotlib import pyplot as plt

    output.parent.mkdir(parents=True, exist_ok=True)

    with matplotlib.rc_context({"svg.hashsalt": "vesiclescope-population-figure"}):
        figure, axes = plt.subplots(1, 2, figsize=(11.5, 5.0))
        heatmap_axis, count_axis = axes

        image = heatmap_axis.imshow(
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
        donor_x, donor_y = data.donor_position_micron
        recipient_x = tuple(position[0] for position in data.recipient_positions_micron)
        recipient_y = tuple(position[1] for position in data.recipient_positions_micron)
        heatmap_axis.scatter(
            (donor_x,),
            (donor_y,),
            marker="*",
            s=130,
            label="Donor",
        )
        heatmap_axis.scatter(
            recipient_x,
            recipient_y,
            marker="o",
            facecolors="none",
            s=55,
            label="Recipients",
        )
        heatmap_axis.set_xlabel("x [micron]")
        heatmap_axis.set_ylabel("y [micron]")
        heatmap_axis.set_title(
            f"8 recipients — extracellular field at {data.heatmap_time_min:g} min"
        )
        heatmap_axis.legend(loc="upper right")
        colorbar = figure.colorbar(image, ax=heatmap_axis)
        colorbar.set_label(f"Concentration [{data.concentration_unit}]")

        count_axis.plot(
            data.planar_densities,
            data.total_internalized_quantities,
            marker="o",
        )
        for count, density, uptake in zip(
            data.recipient_counts,
            data.planar_densities,
            data.total_internalized_quantities,
        ):
            count_axis.annotate(
                f"n={count}",
                (density, uptake),
                xytext=(4, 5),
                textcoords="offset points",
            )
        count_axis.set_xlabel(
            f"Planar recipient density [{data.planar_density_unit}]"
        )
        count_axis.set_ylabel(
            f"Total internalized quantity [{data.quantity_unit}]"
        )
        count_axis.set_title("Recipient-count sensitivity at 50 micron donor radius")
        count_axis.grid(True, alpha=0.25)

        figure.suptitle(_SYNTHETIC_TITLE)
        figure.text(
            0.5,
            0.01,
            "Synthetic benchmark at one fixed numerical resolution; "
            "not experimental evidence.",
            ha="center",
        )
        figure.tight_layout(rect=(0.0, 0.05, 1.0, 0.94))
        figure.savefig(
            output,
            format="svg",
            metadata={
                "Creator": "VesicleScope",
                "Date": None,
                "Description": _SYNTHETIC_TITLE,
            },
        )
        plt.close(figure)

    return output
