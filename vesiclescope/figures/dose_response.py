"""Figure for an exposure-driven dose-response comparison."""

from __future__ import annotations

from pathlib import Path

from vesiclescope.dose_response import effect_concentration
from vesiclescope.workflows.dose_response import DoseResponseComparison


_TITLE = "Exposure, delayed rate change and EV uptake response"


def render_dose_response_figure(comparison: DoseResponseComparison, output: Path) -> Path:
    try:
        import matplotlib
    except ImportError as exc:
        raise RuntimeError(
            "Matplotlib is required for figure rendering; install requirements-figures.txt"
        ) from exc
    matplotlib.use("Agg", force=True)
    from matplotlib import pyplot as plt

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    exposure = comparison.exposure
    duration = comparison.baseline_experiment.duration_min
    times = [duration * i / 480 for i in range(481)]
    unit = exposure.concentration.unit

    with matplotlib.rc_context(
        {"svg.hashsalt": "vesiclescope-dose-response-figure", "svg.fonttype": "none"}
    ):
        figure, (exp_axis, mult_axis, ratio_axis) = plt.subplots(1, 3, figsize=(15.5, 4.8))

        exposure_curve = [
            exposure.concentration.value if exposure.start_min <= t < exposure.end_min else 0.0
            for t in times
        ]
        exp_axis.plot(times, exposure_curve, color="black", linewidth=1.2, label="added exposure C(t)")
        first = comparison.conditions[0].response
        exp_axis.plot(
            times,
            [
                effect_concentration(first, exposure, t, duration_min=duration)
                - first.baseline_concentration.value
                for t in times
            ],
            linestyle="--",
            label=f"effect compartment Ce(t), 1/ke0 = {1 / first.ke0.value:g} min",
        )
        exp_axis.set_xlabel("Time [min]")
        exp_axis.set_ylabel(f"Concentration above baseline [{unit}]")
        exp_axis.set_title("(a) Exposure and delayed effect concentration")
        exp_axis.grid(True, alpha=0.25)
        exp_axis.legend(fontsize=8)

        for condition in comparison.conditions:
            xs, ys = [], []
            for segment in condition.schedule.segments:
                xs += [segment.start_min, segment.end_min]
                ys += [segment.multiplier, segment.multiplier]
            mult_axis.plot(xs, ys, linewidth=1.5, label=f"{condition.label} ({condition.response.target.value})")
        mult_axis.axhline(1.0, color="grey", linewidth=0.6)
        mult_axis.set_xlabel("Time [min]")
        mult_axis.set_ylabel("Rate multiplier (segment mean)")
        mult_axis.set_title("(b) Rate schedules passed to BioFVM")
        mult_axis.grid(True, alpha=0.25)
        mult_axis.legend(fontsize=8)

        for condition in comparison.conditions:
            ratios = comparison.internalization_rate_ratio(condition)
            ratio_axis.plot([t for t, _ in ratios], [r for _, r in ratios], linewidth=1.5, label=condition.label)
        ratio_axis.axhline(1.0, color="grey", linewidth=0.6)
        for edge in (exposure.start_min, exposure.end_min):
            ratio_axis.axvline(edge, color="black", linewidth=0.6, linestyle=":")
        ratio_axis.set_xlabel("Time [min]")
        ratio_axis.set_ylabel("Recipient internalization rate / baseline")
        ratio_axis.set_title("(c) Simulated recipient uptake response")
        ratio_axis.grid(True, alpha=0.25)
        ratio_axis.legend(fontsize=8)

        figure.suptitle(_TITLE)
        figure.text(
            0.5,
            0.012,
            "Synthetic exposure and dose-response parameters exercising the workflow; "
            "simulated BioFVM transport, not a hormone calibration or experimental evidence.",
            ha="center",
            fontsize=8.5,
        )
        figure.tight_layout(rect=(0.0, 0.05, 1.0, 0.93))
        figure.savefig(
            output,
            format="svg",
            metadata={"Creator": "VesicleScope", "Date": None, "Description": _TITLE},
        )
        plt.close(figure)
    return output
