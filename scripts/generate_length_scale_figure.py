"""Generate the Colombo 2025 length-scale constraint figure and JSON summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vesiclescope.figures.length_scale import (
    length_scale_summary_record,
    render_length_scale_figure,
)
from vesiclescope.validation import colombo_2025_length_scale_constraints

# Assumed donor radii spanning small to large tumour-cell footprints; the
# publication reports no in-vivo donor radius.
DONOR_RADII_MICRON = (5.0, 10.0, 15.0, 20.0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    summary = colombo_2025_length_scale_constraints(DONOR_RADII_MICRON)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    figure = render_length_scale_figure(
        summary, args.output_dir / "colombo-length-scale.svg"
    )
    record = length_scale_summary_record(summary)
    record["assumed_donor_radii_micron"] = list(DONOR_RADII_MICRON)
    summary_path = args.output_dir / "colombo-length-scale.json"
    summary_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(figure)
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
