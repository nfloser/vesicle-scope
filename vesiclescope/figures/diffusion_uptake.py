"""Scientific figure for the synthetic diffusion × uptake factor experiment."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from vesiclescope.analysis import DiffusionUptakeSummary


_TITLE = "Synthetic diffusion × uptake factor experiment"


@dataclass(frozen=True, slots=True)
class DiffusionUptakeFigureData:
    diffusion_factors: tuple[float, ...]
    uptake_factors: tuple[float, ...]
    internalized_fraction_rows: tuple[tuple[float, ...], ...]


def prepare_diffusion_uptake_figure_data(
    summaries: tuple[DiffusionUptakeSummary, ...],
) -> DiffusionUptakeFigureData:
    if not isinstance(summaries, tuple) or len(summaries) != 9:
        raise ValueError("figure requires exactly nine factor-condition summaries")

    diffusion_factors = tuple(sorted({item.diffusion_factor for item in summaries}))
    uptake_factors = tuple(sorted({item.uptake_factor for item in summaries}))
    if diffusion_factors != (0.5, 1.0, 2.0) or uptake_factors != (0.5, 1.0, 2.0):
        raise ValueError("figure requires the reviewed 0.5/1/2 factor levels")

    lookup = {}
    for item in summaries:
        key = (item.diffusion_factor, item.uptake_factor)
        if key in lookup:
            raise ValueError("factor-condition summaries must be unique")
        if not math.isfinite(item.internalized_fraction):
            raise ValueError("internalized fraction must be finite")
        if item.internalized_fraction < 0.0 or item.internalized_fraction > 1.0:
            raise ValueError("internalized fraction must lie within [0, 1]")
        lookup[key] = item.internalized_fraction

    rows = tuple(
        tuple(lookup[(diffusion, uptake)] for diffusion in diffusion_factors)
        for uptake in uptake_factors
    )
    return DiffusionUptakeFigureData(
        diffusion_factors=diffusion_factors,
        uptake_factors=uptake_factors,
        internalized_fraction_rows=rows,
    )


def render_diffusion_uptake_figure(
    summaries: tuple[DiffusionUptakeSummary, ...],
    output_path: Path,
) -> Path:
    output = Path(output_path)
    if output.suffix.lower() != ".svg":
        raise ValueError("diffusion × uptake figure output path must end in .svg")

    data = prepare_diffusion_uptake_figure_data(summaries)

    try:
        import matplotlib
    except ImportError as exc:
        raise RuntimeError(
            "Matplotlib is required for figure rendering; install requirements-figures.txt"
        ) from exc

    matplotlib.use("Agg", force=True)
    from matplotlib import pyplot as plt

    output.parent.mkdir(parents=True, exist_ok=True)
    with matplotlib.rc_context(
        {"svg.hashsalt": "vesiclescope-diffusion-uptake-factor", "svg.fonttype": "none"}
    ):
        figure, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
        heatmap_axis, line_axis = axes

        image = heatmap_axis.imshow(
            data.internalized_fraction_rows,
            origin="lower",
            interpolation="nearest",
            aspect="auto",
            vmin=0.0,
            vmax=1.0,
        )
        heatmap_axis.set_xticks(range(3), [f"{value:g}×" for value in data.diffusion_factors])
        heatmap_axis.set_yticks(range(3), [f"{value:g}×" for value in data.uptake_factors])
        heatmap_axis.set_xlabel("Diffusion factor relative to synthetic baseline")
        heatmap_axis.set_ylabel("Uptake factor relative to synthetic baseline")
        heatmap_axis.set_title("Final internalized fraction")

        for row_index, row in enumerate(data.internalized_fraction_rows):
            for column_index, value in enumerate(row):
                heatmap_axis.text(
                    column_index,
                    row_index,
                    f"{100.0 * value:.1f}%",
                    ha="center",
                    va="center",
                )

        colorbar = figure.colorbar(image, ax=heatmap_axis)
        colorbar.set_label("Fraction of released model quantity internalized")

        for uptake_index, uptake in enumerate(data.uptake_factors):
            line_axis.plot(
                data.diffusion_factors,
                data.internalized_fraction_rows[uptake_index],
                marker="o",
                label=f"uptake {uptake:g}×",
            )
        line_axis.set_xlabel("Diffusion factor relative to synthetic baseline")
        line_axis.set_ylabel("Fraction of released model quantity internalized")
        line_axis.set_ylim(0.0, 1.0)
        line_axis.set_title("Interaction lines")
        line_axis.grid(True, alpha=0.25)
        line_axis.legend()

        figure.suptitle(_TITLE)
        figure.text(
            0.5,
            0.01,
            "Controlled synthetic model-behaviour experiment; not experimental evidence. "
            "Factors are relative to synthetic baselines.",
            ha="center",
        )
        figure.tight_layout(rect=(0.0, 0.06, 1.0, 0.94))
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
