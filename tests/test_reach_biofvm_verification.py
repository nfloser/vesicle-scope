"""Numerical verification of the 2D-slab length-scale model against BioFVM."""

import os
import unittest
from pathlib import Path

from vesiclescope.analysis import (
    analyze_donor_boundary_profile,
    fixed_width_distance_edges,
)
from vesiclescope.analysis.reach import (
    ReachGeometry,
    RetentionLandmark,
    cumulative_signal_fraction,
    infer_length_scale,
)
from vesiclescope.domain import (
    BoundaryCondition,
    CircularReleaseSource,
    EvidenceCategory,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines.biofvm import BioFVMNumerics, run_transport


RUNNER = os.environ.get("VESICLESCOPE_BIOFVM_RUNNER")

DONOR_RADIUS = 10.0
DIFFUSION = 100.0
DECAY = 0.25
LENGTH_SCALE = (DIFFUSION / DECAY) ** 0.5  # 20 micron
WIDTH = 400.0
DURATION = 40.0  # 10 / k: transient below 5e-5 of steady state


def _parameter(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic verification input; not a biological default.",),
    )


def steady_length_scale_experiment() -> TransportExperiment:
    return TransportExperiment(
        experiment_id="synthetic.length-scale.slab-verification",
        domain=RectangularDomain2D(
            width_micron=WIDTH,
            height_micron=WIDTH,
            slice_thickness_micron=25.0,
        ),
        duration_min=DURATION,
        sample_every_min=DURATION,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=_parameter("transport.diffusion", DIFFUSION, "micron^2/min"),
        decay=_parameter("transport.decay", DECAY, "1/min"),
        initial_concentration=_parameter(
            "initial.concentration", 0.0, "particle_equivalent/micron^3"
        ),
        release_sources=(
            CircularReleaseSource(
                identifier="source.finite-donor",
                x_micron=WIDTH / 2,
                y_micron=WIDTH / 2,
                footprint_radius_micron=DONOR_RADIUS,
                release_rate=_parameter(
                    "source.release", 1000.0, "particle_equivalent/min"
                ),
            ),
        ),
        uptake_sinks=(),
    )


def simulated_cumulative(grid_spacing: float) -> list[tuple[float, float]]:
    experiment = steady_length_scale_experiment()
    result = run_transport(
        experiment,
        BioFVMNumerics(grid_spacing_micron=grid_spacing, time_step_min=0.05),
        Path(RUNNER),
    )
    profile = analyze_donor_boundary_profile(
        experiment,
        result,
        time_min=DURATION,
        edges_micron=fixed_width_distance_edges(
            max_distance_micron=150.0, bin_width_micron=10.0
        ),
    )
    total = (
        sum(item.integrated_field_quantity for item in profile.bins)
        + profile.outside_extent_integrated_quantity
    )
    cumulative = 0.0
    points = []
    for item in profile.bins:
        cumulative += item.integrated_field_quantity
        points.append((item.upper_bound_micron, cumulative / total))
    return points


@unittest.skipUnless(RUNNER, "native BioFVM runner is required")
class SlabLengthScaleVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.coarse = simulated_cumulative(5.0)
        cls.fine = simulated_cumulative(2.5)

    def errors(self, points: list[tuple[float, float]]) -> list[float]:
        return [
            abs(
                fraction
                - cumulative_signal_fraction(
                    ReachGeometry.CIRCULAR_DONOR_2D_SLAB,
                    length_scale_micron=LENGTH_SCALE,
                    distance_micron=distance,
                    donor_radius_micron=DONOR_RADIUS,
                )
            )
            for distance, fraction in points
        ]

    def test_profile_matches_analytical_solution(self) -> None:
        self.assertLess(max(self.errors(self.coarse)), 0.02)
        self.assertLess(max(self.errors(self.fine)), 0.01)

    def test_error_decreases_with_grid_refinement(self) -> None:
        self.assertLess(max(self.errors(self.fine)), max(self.errors(self.coarse)))

    def test_inference_recovers_simulated_length_scale(self) -> None:
        landmarks = tuple(
            RetentionLandmark(distance_micron=d, cumulative_fraction=f)
            for d, f in self.fine
            if d in (20.0, 40.0, 80.0)
        )
        inference = infer_length_scale(
            ReachGeometry.CIRCULAR_DONOR_2D_SLAB,
            landmarks,
            donor_radius_micron=DONOR_RADIUS,
        )
        self.assertAlmostEqual(
            inference.least_squares_length_scale_micron / LENGTH_SCALE,
            1.0,
            delta=0.05,
        )


if __name__ == "__main__":
    unittest.main()
