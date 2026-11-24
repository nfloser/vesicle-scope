"""Run the synthetic dose-response demonstration and render its figure."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from vesiclescope.engines.biofvm import BioFVMNumerics
from vesiclescope.figures.dose_response import render_dose_response_figure
from vesiclescope.scenarios.dose_response import (
    synthetic_dose_response_experiment,
    synthetic_dose_responses,
    synthetic_hormone_pulse,
)
from vesiclescope.workflows.dose_response import run_dose_response_comparison


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", default=os.environ.get("VESICLESCOPE_BIOFVM_RUNNER"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.runner:
        raise SystemExit("native runner is required via --runner or VESICLESCOPE_BIOFVM_RUNNER")
    comparison = run_dose_response_comparison(
        experiment=synthetic_dose_response_experiment(),
        exposure=synthetic_hormone_pulse(),
        responses=synthetic_dose_responses(),
        numerics=BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
        runner=Path(args.runner),
        segment_min=5.0,
    )
    print(render_dose_response_figure(comparison, args.output))
    for condition in comparison.conditions:
        ratios = comparison.internalization_rate_ratio(condition)
        peak_time, peak = max(ratios, key=lambda item: abs(item[1] - 1.0))
        print(f"{condition.label}: extreme ratio {peak:.3f} at {peak_time:g} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
