"""Figure: what the Colombo 2025 landmarks constrain about EV transport."""

from __future__ import annotations

import math
from pathlib import Path

from vesiclescope.analysis.reach import (
    ReachGeometry,
    cumulative_signal_fraction,
    perturbed_reach,
    stokes_einstein_diffusion_micron2_per_min,
)
from vesiclescope.validation.colombo_length_scale import (
    COLOMBO_2025_TAIL_BOUND,
    ColomboLengthScaleSummary,
    colombo_2025_landmarks,
)


_TITLE = "Colombo 2025 landmarks constrain one transport length scale"

# Free-solution reference: water at 37 degC. Viscosity 0.6913 mPa s is the
# tabulated value for liquid water at 310.15 K (IAPWS 2008 formulation).
WATER_37C_VISCOSITY_PA_S = 0.6913e-3
BODY_TEMPERATURE_K = 310.15
REFERENCE_DIAMETERS_NM = (50.0, 100.0, 200.0)
ASSUMED_BOUNDARY_TO_THRESHOLD_RATIO = 10.0


def render_length_scale_figure(
    summary: ColomboLengthScaleSummary,
    output: Path,
) -> Path:
    """Render a three-panel SVG from an explicit length-scale summary."""

    try:
        import matplotlib
    except ImportError as exc:
        raise RuntimeError(
            "Matplotlib is required for figure rendering; "
            "install requirements-figures.txt"
        ) from exc

    matplotlib.use("Agg", force=True)
    from matplotlib import pyplot as plt

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    low, high = summary.length_scale_range_micron
    landmarks = colombo_2025_landmarks()

    with matplotlib.rc_context(
        {"svg.hashsalt": "vesiclescope-length-scale-figure", "svg.fonttype": "none"}
    ):
        figure, (cum_axis, time_axis, reach_axis) = plt.subplots(
            1, 3, figsize=(15.5, 5.0)
        )

        # (a) cumulative signal: landmarks versus model curves
        distances = [0.5 * i for i in range(0, 241)]
        for inference in summary.inferences:
            lam = inference.least_squares_length_scale_micron
            if inference.geometry is ReachGeometry.PLANAR_BOUNDARY:
                label = f"planar boundary, lambda = {lam:.1f} micron"
                style = "-"
            else:
                label = (
                    f"2D slab, donor radius {inference.donor_radius_micron:g} micron, "
                    f"lambda = {lam:.1f} micron"
                )
                style = "--"
            cum_axis.plot(
                distances,
                [
                    cumulative_signal_fraction(
                        inference.geometry,
                        length_scale_micron=lam,
                        distance_micron=d,
                        donor_radius_micron=inference.donor_radius_micron,
                    )
                    for d in distances
                ],
                style,
                linewidth=1.3,
                label=label,
            )
        cum_axis.plot(
            [item.distance_micron for item in landmarks],
            [item.cumulative_fraction for item in landmarks],
            "ko",
            markersize=7,
            label="published fit-derived landmarks",
        )
        cum_axis.plot(
            [COLOMBO_2025_TAIL_BOUND.distance_micron],
            [1.0 - COLOMBO_2025_TAIL_BOUND.max_fraction_beyond],
            marker="^",
            color="black",
            linestyle="none",
            markersize=7,
            label="published bound: <5% beyond 100 micron",
        )
        cum_axis.set_xlabel("Distance from donor boundary [micron]")
        cum_axis.set_ylabel("Cumulative fraction of EV-associated signal")
        cum_axis.set_title("(a) One length scale reproduces all landmarks")
        cum_axis.set_xlim(0, 120)
        cum_axis.set_ylim(0, 1.02)
        cum_axis.grid(True, alpha=0.25)
        cum_axis.legend(fontsize=7.5, loc="lower right")

        # (b) implied loss timescale versus assumed diffusion coefficient
        diffusions = [10 ** (-2 + 0.02 * i) for i in range(0, 251)]  # 0.01..1000
        time_axis.fill_between(
            diffusions,
            [low * low / d for d in diffusions],
            [high * high / d for d in diffusions],
            alpha=0.3,
            label=f"lambda = {low:.1f}-{high:.1f} micron",
        )
        for diameter in REFERENCE_DIAMETERS_NM:
            free = stokes_einstein_diffusion_micron2_per_min(
                hydrodynamic_diameter_nm=diameter,
                temperature_kelvin=BODY_TEMPERATURE_K,
                viscosity_pa_s=WATER_37C_VISCOSITY_PA_S,
            )
            time_axis.axvline(free, color="black", linewidth=0.8, linestyle=":")
            time_axis.text(
                free,
                3e4,
                f"free {diameter:g} nm",
                rotation=90,
                fontsize=7.5,
                ha="right",
                va="top",
            )
        for minutes, label in ((60.0, "1 h"), (1440.0, "1 day")):
            time_axis.axhline(minutes, color="grey", linewidth=0.6)
            time_axis.text(0.012, minutes * 1.15, label, fontsize=7.5)
        time_axis.set_xscale("log")
        time_axis.set_yscale("log")
        time_axis.set_xlim(0.01, 1000)
        time_axis.set_ylim(0.1, 1e5)
        time_axis.set_xlabel("Assumed effective EV diffusion D [micron^2/min]")
        time_axis.set_ylabel("Implied effective loss timescale 1/k_eff [min]")
        time_axis.set_title("(b) Free diffusion would require minute-scale loss")
        time_axis.grid(True, which="both", alpha=0.2)
        time_axis.legend(fontsize=7.5, loc="lower left")

        # (c) perturbation propagation in the planar model
        folds = [2 ** (-2 + 0.05 * i) for i in range(0, 81)]  # 0.25..4
        lam_mid = 0.5 * (low + high)

        def reach(**kwargs: float) -> float:
            return perturbed_reach(
                length_scale_micron=lam_mid,
                boundary_to_threshold_ratio=ASSUMED_BOUNDARY_TO_THRESHOLD_RATIO,
                **kwargs,
            ).perturbed_threshold_reach_micron

        for label, key in (
            ("release x fold", "release_fold"),
            ("loss (uptake/clearance) x fold", "loss_fold"),
            ("diffusion x fold", "diffusion_fold"),
        ):
            values = []
            for fold in folds:
                arguments = {"release_fold": 1.0, "loss_fold": 1.0, "diffusion_fold": 1.0}
                arguments[key] = fold
                values.append(reach(**arguments))
            reach_axis.plot(folds, values, linewidth=1.5, label=label)
        reach_axis.set_xscale("log", base=2)
        reach_axis.set_xlabel("Perturbation fold change (e.g. hormone effect)")
        reach_axis.set_ylabel("Threshold reach [micron]")
        reach_axis.set_title("(c) Uptake/clearance changes reach most")
        reach_axis.text(
            0.02,
            0.02,
            f"lambda = {lam_mid:.1f} micron, assumed c(0)/c* = "
            f"{ASSUMED_BOUNDARY_TO_THRESHOLD_RATIO:g}",
            transform=reach_axis.transAxes,
            fontsize=7.5,
        )
        reach_axis.grid(True, which="both", alpha=0.25)
        reach_axis.legend(fontsize=7.5)

        figure.suptitle(_TITLE)
        figure.text(
            0.5,
            0.012,
            "Conditional on steady-state linear reaction-diffusion; landmarks are "
            "fit-derived publication summaries, not raw data. "
            "D and loss are not separately identifiable; c(0)/c* in (c) is an assumption.",
            ha="center",
            fontsize=8.5,
        )
        figure.tight_layout(rect=(0.0, 0.05, 1.0, 0.94))
        figure.savefig(
            output,
            format="svg",
            metadata={"Creator": "VesicleScope", "Date": None, "Description": _TITLE},
        )
        plt.close(figure)
    return output


def length_scale_summary_record(summary: ColomboLengthScaleSummary) -> dict:
    """JSON-serializable record of the summary for reproducible reporting."""

    low, high = summary.length_scale_range_micron
    free = {
        f"{diameter:g}_nm": stokes_einstein_diffusion_micron2_per_min(
            hydrodynamic_diameter_nm=diameter,
            temperature_kelvin=BODY_TEMPERATURE_K,
            viscosity_pa_s=WATER_37C_VISCOSITY_PA_S,
        )
        for diameter in REFERENCE_DIAMETERS_NM
    }
    return {
        "source": "doi:10.1002/jev2.70169 (fit-derived landmarks only)",
        "assumptions": list(summary.assumptions),
        "non_claims": list(summary.non_claims),
        "length_scale_range_micron": [low, high],
        "inferences": [
            {
                "geometry": item.geometry.value,
                "donor_radius_micron": item.donor_radius_micron,
                "per_landmark_length_scale_micron": list(
                    item.per_landmark_length_scale_micron
                ),
                "least_squares_length_scale_micron": item.least_squares_length_scale_micron,
                "landmark_residuals": list(item.residuals),
                "landmark_consistency_ratio": item.landmark_consistency_ratio,
                "tail_fraction_beyond_100_micron": item.tail_fraction_beyond,
                "tail_bound_satisfied": item.tail_bound_satisfied,
            }
            for item in summary.inferences
        ],
        "free_solution_diffusion_micron2_per_min": free,
        "implied_loss_timescale_min_at_free_diffusion": {
            key: list(summary.loss_timescale_range_min(value)) for key, value in free.items()
        },
        "reference_constants": {
            "temperature_kelvin": BODY_TEMPERATURE_K,
            "water_viscosity_pa_s": WATER_37C_VISCOSITY_PA_S,
        },
        "math_note": "lambda = sqrt(D / k_eff); 1/k_eff = lambda^2 / D",
        "rounding_note": f"lambda range rounded: {math.floor(low)}-{math.ceil(high)} micron",
    }
