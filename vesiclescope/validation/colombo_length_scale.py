"""What the public Colombo 2025 landmarks can and cannot constrain.

The published tumour data are summarized only by fit-derived cumulative
retention landmarks. Under steady-state linear reaction-diffusion those
landmarks constrain one quantity: the transport length scale
lambda = sqrt(D / k_eff). They do not separate diffusion from loss, and they do
not constrain release. This module makes that statement executable and keeps
the geometry/measurement assumption explicit.
"""

from __future__ import annotations

from dataclasses import dataclass

from vesiclescope.analysis.reach import (
    LengthScaleInference,
    ReachGeometry,
    RetentionLandmark,
    TailBound,
    implied_loss_rate_per_min,
    infer_length_scale,
)

from .colombo2025 import colombo_2025_tumour_distance_target


# "less than 5% beyond 100 micron" in the publication's fit summary.
COLOMBO_2025_TAIL_BOUND = TailBound(distance_micron=100.0, max_fraction_beyond=0.05)

ASSUMPTIONS = (
    "steady state: tumour growth is slow compared with 1/k_eff",
    "linear release, diffusion and first-order loss (uptake and/or decay)",
    "observed EV-associated signal is proportional to local concentration; "
    "linear uptake gives internalized signal the same spatial shape",
    "isolated donor: neighbouring donors at 1:100-1:200 ratios do not overlap",
    "the published exponential fit describes the measured cumulative curve",
)

NON_CLAIMS = (
    "Landmarks are fit-derived summaries, not raw measurements.",
    "lambda is not a VesicleScope default and is not stored as a biological "
    "parameter.",
    "Diffusion and loss are not separately identifiable from these landmarks.",
    "Release rate is not constrained.",
)


@dataclass(frozen=True, slots=True)
class ColomboLengthScaleSummary:
    """Length-scale inferences across explicit geometry assumptions."""

    inferences: tuple[LengthScaleInference, ...]
    assumptions: tuple[str, ...] = ASSUMPTIONS
    non_claims: tuple[str, ...] = NON_CLAIMS

    @property
    def length_scale_range_micron(self) -> tuple[float, float]:
        values = tuple(
            item.least_squares_length_scale_micron for item in self.inferences
        )
        return (min(values), max(values))

    def loss_timescale_range_min(
        self, diffusion_micron2_per_min: float
    ) -> tuple[float, float]:
        """Range of 1/k_eff implied for one assumed diffusion coefficient."""

        low, high = self.length_scale_range_micron
        return (
            1.0
            / implied_loss_rate_per_min(
                length_scale_micron=low,
                diffusion_micron2_per_min=diffusion_micron2_per_min,
            ),
            1.0
            / implied_loss_rate_per_min(
                length_scale_micron=high,
                diffusion_micron2_per_min=diffusion_micron2_per_min,
            ),
        )


def colombo_2025_landmarks() -> tuple[RetentionLandmark, ...]:
    target = colombo_2025_tumour_distance_target()
    return tuple(
        RetentionLandmark(
            distance_micron=item.distance_micron,
            cumulative_fraction=item.cumulative_fraction,
        )
        for item in target.fit_derived_retention_landmarks
    )


def colombo_2025_length_scale_constraints(
    donor_radii_micron: tuple[float, ...],
) -> ColomboLengthScaleSummary:
    """Infer lambda under planar and 2D-slab assumptions for given donor radii.

    The equatorial section of a spherical donor yields exactly the planar
    cumulative curve and therefore the same lambda; it is not repeated.
    Donor radii are caller-supplied assumptions (the publication reports no
    in-vivo donor radius).
    """

    if not isinstance(donor_radii_micron, tuple) or not donor_radii_micron:
        raise ValueError("donor_radii_micron must be a non-empty tuple")
    landmarks = colombo_2025_landmarks()
    inferences = [
        infer_length_scale(
            ReachGeometry.PLANAR_BOUNDARY,
            landmarks,
            tail_bound=COLOMBO_2025_TAIL_BOUND,
        )
    ]
    for radius in donor_radii_micron:
        inferences.append(
            infer_length_scale(
                ReachGeometry.CIRCULAR_DONOR_2D_SLAB,
                landmarks,
                donor_radius_micron=radius,
                tail_bound=COLOMBO_2025_TAIL_BOUND,
            )
        )
    return ColomboLengthScaleSummary(inferences=tuple(inferences))
