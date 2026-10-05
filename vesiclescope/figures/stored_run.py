"""Offline scientific overview rendered from a completed run bundle."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from vesiclescope.run_bundles import SimulationRunBundle


_TITLE = "VesicleScope stored-run overview"


@dataclass(frozen=True, slots=True)
class StoredRunFigureData:
    experiment_id: str
    scientific_status: str
    evidence_categories: tuple[str, ...]
    vesiclescope_revision: str
    engine_label: str
    grid_spacing_micron: float
    time_step_min: float
    concentration_unit: str
    quantity_unit: str
    field_time_min: float
    field_rows: tuple[tuple[float, ...], ...]
    domain_width_micron: float
    domain_height_micron: float
    sample_times_min: tuple[float, ...]
    extracellular_quantities: tuple[float, ...]
    internalized_quantities: tuple[float, ...]


def _evidence_categories(bundle: SimulationRunBundle) -> tuple[str, ...]:
    experiment = bundle.experiment
    return tuple(
        sorted(
            {
                experiment.diffusion.evidence.value,
                experiment.decay.evidence.value,
                experiment.initial_concentration.evidence.value,
                *(source.release_rate.evidence.value for source in experiment.release_sources),
                *(sink.uptake_rate.evidence.value for sink in experiment.uptake_sinks),
            }
        )
    )


def prepare_stored_run_figure_data(bundle: SimulationRunBundle) -> StoredRunFigureData:
    if not isinstance(bundle, SimulationRunBundle):
        raise TypeError("bundle must be a SimulationRunBundle")

    experiment = bundle.experiment
    result = bundle.result
    if result.integrated_quantity_unit != result.internalized_quantity_unit:
        raise ValueError(
            "stored-run overview requires matching extracellular and internalized quantity units"
        )
    final_snapshots = tuple(
        snapshot
        for snapshot in result.field_snapshots
        if math.isclose(
            snapshot.time_min,
            experiment.duration_min,
            rel_tol=0.0,
            abs_tol=1e-9,
        )
    )
    if len(final_snapshots) != 1:
        raise ValueError("stored-run overview requires exactly one final field snapshot")
    final_snapshot = final_snapshots[0]
    if len(final_snapshot.values) != result.grid.voxel_count:
        raise ValueError("final field length does not match the normalized grid")

    rows = tuple(
        tuple(
            final_snapshot.values[
                row_index * result.grid.nx : (row_index + 1) * result.grid.nx
            ]
        )
        for row_index in range(result.grid.ny)
    )
    evidence = _evidence_categories(bundle)
    status = (
        "synthetic benchmark; not experimental evidence"
        if evidence == ("synthetic_benchmark",)
        else "simulation with mixed or evidence-backed inputs; not biological truth"
    )
    return StoredRunFigureData(
        experiment_id=experiment.experiment_id,
        scientific_status=status,
        evidence_categories=evidence,
        vesiclescope_revision=bundle.vesiclescope_revision,
        engine_label=(
            f"{result.engine.engine}; PhysiCell {result.engine.physicell_release}; "
            f"BioFVM {result.engine.biofvm_version}"
        ),
        grid_spacing_micron=bundle.numerics.grid_spacing_micron,
        time_step_min=bundle.numerics.time_step_min,
        concentration_unit=result.concentration_unit,
        quantity_unit=result.integrated_quantity_unit,
        field_time_min=final_snapshot.time_min,
        field_rows=rows,
        domain_width_micron=experiment.domain.width_micron,
        domain_height_micron=experiment.domain.height_micron,
        sample_times_min=tuple(sample.time_min for sample in result.samples),
        extracellular_quantities=tuple(
            sample.integrated_field_quantity for sample in result.samples
        ),
        internalized_quantities=tuple(
            sample.internalized_field_quantity for sample in result.samples
        ),
    )


def render_stored_run_figure(
    bundle: SimulationRunBundle,
    output_path: Path,
) -> Path:
    output = Path(output_path)
    if output.suffix.lower() != ".svg":
        raise ValueError("stored-run figure output path must end in .svg")
    data = prepare_stored_run_figure_data(bundle)

    try:
        import matplotlib
    except ImportError as exc:
        raise RuntimeError(
            "Matplotlib is required for figure rendering; install vesicle-scope[figures]"
        ) from exc

    matplotlib.use("Agg", force=True)
    from matplotlib import pyplot as plt

    output.parent.mkdir(parents=True, exist_ok=True)
    with matplotlib.rc_context(
        {"svg.hashsalt": "vesiclescope-stored-run-overview", "svg.fonttype": "none"}
    ):
        figure, axes = plt.subplots(1, 2, figsize=(12.0, 5.2))
        field_axis, series_axis = axes

        image = field_axis.imshow(
            data.field_rows,
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
        field_axis.set_xlabel("x [micron]")
        field_axis.set_ylabel("y [micron]")
        field_axis.set_title(f"Final extracellular field at {data.field_time_min:g} min")
        colorbar = figure.colorbar(image, ax=field_axis)
        colorbar.set_label(f"Concentration [{data.concentration_unit}]")

        series_axis.plot(
            data.sample_times_min,
            data.extracellular_quantities,
            marker="o",
            label="Extracellular",
        )
        series_axis.plot(
            data.sample_times_min,
            data.internalized_quantities,
            marker="o",
            label="Internalized",
        )
        series_axis.set_xlabel("Time [min]")
        series_axis.set_ylabel(f"Model quantity [{data.quantity_unit}]")
        series_axis.set_title("Stored normalized time series")
        series_axis.grid(True, alpha=0.25)
        series_axis.legend()

        figure.suptitle(f"{_TITLE} — {data.experiment_id}")
        figure.text(
            0.5,
            0.045,
            data.scientific_status,
            ha="center",
        )
        figure.text(
            0.5,
            0.015,
            (
                f"{data.engine_label}; grid {data.grid_spacing_micron:g} micron; "
                f"dt {data.time_step_min:g} min; revision {data.vesiclescope_revision}"
            ),
            ha="center",
            fontsize=7,
        )
        figure.tight_layout(rect=(0.0, 0.085, 1.0, 0.94))
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
