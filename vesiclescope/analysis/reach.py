"""Steady-state length-scale analysis for donor-centred EV transport.

For linear release, diffusion and first-order loss (uptake by surrounding
cells and/or decay) the steady extracellular field around a donor has a single
characteristic length

    lambda = sqrt(D / k_eff)

This module infers lambda from published cumulative-retention landmarks under
explicit geometry/measurement assumptions, maps lambda to an effective loss
timescale for a chosen diffusion coefficient, and propagates perturbation
multipliers (for example hormone effects) through the same model class.

Everything here is conditional on that model class. Nothing in this module is
a biological default: callers supply every physical value explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


BOLTZMANN_J_PER_K = 1.380649e-23  # exact SI definition (2019 redefinition)


class ReachGeometry(str, Enum):
    """Geometry/measurement assumption linking lambda to a radial observable.

    PLANAR_BOUNDARY
        Distance measured normal to a locally flat donor boundary. Steady
        concentration ~ exp(-d / lambda); equal measurement area per distance.
    SPHERICAL_DONOR_EQUATORIAL_SECTION
        3D spherical donor of radius R observed in its equatorial plane.
        Concentration ~ R/(R + d) exp(-d / lambda); the in-plane shell
        perimeter grows with (R + d), so the cumulative signal is again
        exactly exponential in d.
    CIRCULAR_DONOR_2D_SLAB
        Circular donor in a thin 2D slab, the geometry VesicleScope simulates.
        Concentration ~ K0((R + d) / lambda); shell perimeter ~ (R + d).
    """

    PLANAR_BOUNDARY = "planar_boundary"
    SPHERICAL_DONOR_EQUATORIAL_SECTION = "spherical_donor_equatorial_section"
    CIRCULAR_DONOR_2D_SLAB = "circular_donor_2d_slab"


def _positive(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{field_name} must be finite and positive")
    return number


def _non_negative(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{field_name} must be finite and non-negative")
    return number


def _fraction(value: float, field_name: str) -> float:
    number = _positive(value, field_name)
    if number >= 1.0:
        raise ValueError(f"{field_name} must lie in the open interval (0, 1)")
    return number


def _scaled_bessel_k(order: int, x: float) -> float:
    """exp(x) * K_order(x) for order 0 or 1 and x > 0.

    Uses exp(x) K_n(x) = integral_0^inf exp(-x (cosh t - 1)) cosh(n t) dt. The
    integrand is smooth and decays doubly exponentially, so the trapezoidal
    rule converges exponentially fast. Scaling keeps ratios finite for large x.
    """

    if order not in (0, 1):
        raise ValueError("only orders 0 and 1 are supported")
    x = _positive(x, "x")
    upper = math.acosh(1.0 + 745.0 / x) + 1.0
    steps = 400
    h = upper / steps
    total = 0.0
    for index in range(steps + 1):
        t = index * h
        weight = 0.5 if index in (0, steps) else 1.0
        exponent = -x * (math.cosh(t) - 1.0)
        if exponent < -745.0:
            continue
        total += weight * math.exp(exponent) * math.cosh(order * t)
    return total * h


def _bessel_k(order: int, x: float) -> float:
    return _scaled_bessel_k(order, x) * math.exp(-_positive(x, "x"))


def bessel_k0(x: float) -> float:
    """Modified Bessel function of the second kind, order 0."""

    return _bessel_k(0, x)


def bessel_k1(x: float) -> float:
    """Modified Bessel function of the second kind, order 1."""

    return _bessel_k(1, x)


def _require_radius(geometry: ReachGeometry, donor_radius_micron: float | None) -> float:
    if geometry is ReachGeometry.PLANAR_BOUNDARY:
        return 0.0
    if donor_radius_micron is None:
        raise ValueError(f"{geometry.value} requires donor_radius_micron")
    return _non_negative(donor_radius_micron, "donor_radius_micron")


def steady_state_profile_shape(
    geometry: ReachGeometry,
    *,
    length_scale_micron: float,
    distance_micron: float,
    donor_radius_micron: float | None = None,
) -> float:
    """Concentration at boundary distance d relative to the boundary value."""

    geometry = ReachGeometry(geometry)
    lam = _positive(length_scale_micron, "length_scale_micron")
    d = _non_negative(distance_micron, "distance_micron")
    radius = _require_radius(geometry, donor_radius_micron)
    if geometry is ReachGeometry.PLANAR_BOUNDARY:
        return math.exp(-d / lam)
    if geometry is ReachGeometry.SPHERICAL_DONOR_EQUATORIAL_SECTION:
        if radius == 0.0:
            raise ValueError("spherical donor requires a positive radius")
        return radius / (radius + d) * math.exp(-d / lam)
    if radius == 0.0:
        raise ValueError("circular 2D donor requires a positive radius")
    a, b = radius / lam, (radius + d) / lam
    return _scaled_bessel_k(0, b) / _scaled_bessel_k(0, a) * math.exp(a - b)


def cumulative_signal_fraction(
    geometry: ReachGeometry,
    *,
    length_scale_micron: float,
    distance_micron: float,
    donor_radius_micron: float | None = None,
) -> float:
    """Fraction of steady extracellular signal within distance d of the boundary.

    Signal is assumed proportional to local concentration (linear uptake makes
    internalized signal share the same spatial shape at steady state).
    """

    geometry = ReachGeometry(geometry)
    lam = _positive(length_scale_micron, "length_scale_micron")
    d = _non_negative(distance_micron, "distance_micron")
    radius = _require_radius(geometry, donor_radius_micron)
    if geometry in (
        ReachGeometry.PLANAR_BOUNDARY,
        ReachGeometry.SPHERICAL_DONOR_EQUATORIAL_SECTION,
    ):
        if geometry is ReachGeometry.SPHERICAL_DONOR_EQUATORIAL_SECTION and radius == 0.0:
            raise ValueError("spherical donor requires a positive radius")
        return -math.expm1(-d / lam)
    if radius == 0.0:
        raise ValueError("circular 2D donor requires a positive radius")
    # integral r K0(r / lam) dr = -lam * r * K1(r / lam)
    a = radius / lam
    b = (radius + d) / lam
    ratio = (b / a) * _scaled_bessel_k(1, b) / _scaled_bessel_k(1, a) * math.exp(a - b)
    return 1.0 - ratio


@dataclass(frozen=True, slots=True)
class RetentionLandmark:
    """A cumulative signal fraction observed within a boundary distance."""

    distance_micron: float
    cumulative_fraction: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "distance_micron",
            _positive(self.distance_micron, "distance_micron"),
        )
        object.__setattr__(
            self,
            "cumulative_fraction",
            _fraction(self.cumulative_fraction, "cumulative_fraction"),
        )


@dataclass(frozen=True, slots=True)
class TailBound:
    """Upper bound on the signal fraction found beyond a distance."""

    distance_micron: float
    max_fraction_beyond: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "distance_micron",
            _positive(self.distance_micron, "distance_micron"),
        )
        object.__setattr__(
            self,
            "max_fraction_beyond",
            _fraction(self.max_fraction_beyond, "max_fraction_beyond"),
        )


def _solve_length_scale(
    geometry: ReachGeometry,
    landmark: RetentionLandmark,
    donor_radius_micron: float | None,
) -> float:
    if geometry is not ReachGeometry.CIRCULAR_DONOR_2D_SLAB:
        return -landmark.distance_micron / math.log1p(-landmark.cumulative_fraction)
    lo, hi = math.log(1e-3), math.log(1e5)
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        fraction = cumulative_signal_fraction(
            geometry,
            length_scale_micron=math.exp(mid),
            distance_micron=landmark.distance_micron,
            donor_radius_micron=donor_radius_micron,
        )
        if fraction > landmark.cumulative_fraction:
            lo = mid  # too concentrated: lambda must grow
        else:
            hi = mid
    return math.exp(0.5 * (lo + hi))


@dataclass(frozen=True, slots=True)
class LengthScaleInference:
    """Length scale implied by retention landmarks under one geometry."""

    geometry: ReachGeometry
    donor_radius_micron: float | None
    per_landmark_length_scale_micron: tuple[float, ...]
    least_squares_length_scale_micron: float
    residuals: tuple[float, ...]
    tail_bound: TailBound | None
    tail_fraction_beyond: float | None

    @property
    def landmark_consistency_ratio(self) -> float:
        """max/min of single-landmark solutions; 1.0 means one lambda fits all."""

        values = self.per_landmark_length_scale_micron
        return max(values) / min(values)

    @property
    def tail_bound_satisfied(self) -> bool | None:
        if self.tail_bound is None or self.tail_fraction_beyond is None:
            return None
        return self.tail_fraction_beyond <= self.tail_bound.max_fraction_beyond


def infer_length_scale(
    geometry: ReachGeometry,
    landmarks: tuple[RetentionLandmark, ...],
    *,
    donor_radius_micron: float | None = None,
    tail_bound: TailBound | None = None,
) -> LengthScaleInference:
    """Infer lambda from cumulative retention landmarks under one geometry."""

    geometry = ReachGeometry(geometry)
    if not isinstance(landmarks, tuple) or not landmarks:
        raise ValueError("landmarks must be a non-empty tuple")
    if not all(isinstance(item, RetentionLandmark) for item in landmarks):
        raise TypeError("landmarks must contain RetentionLandmark values")
    if tail_bound is not None and not isinstance(tail_bound, TailBound):
        raise TypeError("tail_bound must be a TailBound")
    radius = _require_radius(geometry, donor_radius_micron)
    radius_arg = None if geometry is ReachGeometry.PLANAR_BOUNDARY else radius

    singles = tuple(
        _solve_length_scale(geometry, landmark, radius_arg) for landmark in landmarks
    )

    def loss(log_lam: float) -> float:
        lam = math.exp(log_lam)
        return sum(
            (
                cumulative_signal_fraction(
                    geometry,
                    length_scale_micron=lam,
                    distance_micron=item.distance_micron,
                    donor_radius_micron=radius_arg,
                )
                - item.cumulative_fraction
            )
            ** 2
            for item in landmarks
        )

    # Golden-section search bracketed by the single-landmark solutions.
    lo = math.log(min(singles)) - 0.1
    hi = math.log(max(singles)) + 0.1
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    c = hi - ratio * (hi - lo)
    d = lo + ratio * (hi - lo)
    for _ in range(80):
        if loss(c) < loss(d):
            hi = d
        else:
            lo = c
        c = hi - ratio * (hi - lo)
        d = lo + ratio * (hi - lo)
    best = math.exp(0.5 * (lo + hi))

    residuals = tuple(
        cumulative_signal_fraction(
            geometry,
            length_scale_micron=best,
            distance_micron=item.distance_micron,
            donor_radius_micron=radius_arg,
        )
        - item.cumulative_fraction
        for item in landmarks
    )
    tail_fraction = None
    if tail_bound is not None:
        tail_fraction = 1.0 - cumulative_signal_fraction(
            geometry,
            length_scale_micron=best,
            distance_micron=tail_bound.distance_micron,
            donor_radius_micron=radius_arg,
        )
    return LengthScaleInference(
        geometry=geometry,
        donor_radius_micron=radius_arg,
        per_landmark_length_scale_micron=singles,
        least_squares_length_scale_micron=best,
        residuals=residuals,
        tail_bound=tail_bound,
        tail_fraction_beyond=tail_fraction,
    )


def stokes_einstein_diffusion_micron2_per_min(
    *,
    hydrodynamic_diameter_nm: float,
    temperature_kelvin: float,
    viscosity_pa_s: float,
) -> float:
    """Free-solution Stokes–Einstein diffusion coefficient in micron^2/min.

    This is an upper reference for an unhindered sphere, not a tissue value.
    """

    diameter = _positive(hydrodynamic_diameter_nm, "hydrodynamic_diameter_nm")
    temperature = _positive(temperature_kelvin, "temperature_kelvin")
    viscosity = _positive(viscosity_pa_s, "viscosity_pa_s")
    radius_m = diameter * 1e-9 / 2.0
    d_m2_per_s = BOLTZMANN_J_PER_K * temperature / (6.0 * math.pi * viscosity * radius_m)
    return d_m2_per_s * 1e12 * 60.0


def implied_loss_rate_per_min(
    *,
    length_scale_micron: float,
    diffusion_micron2_per_min: float,
) -> float:
    """Effective first-order loss rate k_eff = D / lambda^2."""

    lam = _positive(length_scale_micron, "length_scale_micron")
    diffusion = _positive(diffusion_micron2_per_min, "diffusion_micron2_per_min")
    return diffusion / (lam * lam)


@dataclass(frozen=True, slots=True)
class PerturbedReach:
    """Effect of multiplicative perturbations in the planar steady-state model."""

    release_fold: float
    loss_fold: float
    diffusion_fold: float
    length_scale_fold: float
    boundary_concentration_fold: float
    baseline_threshold_reach_micron: float
    perturbed_threshold_reach_micron: float


def perturbed_reach(
    *,
    length_scale_micron: float,
    boundary_to_threshold_ratio: float,
    release_fold: float,
    loss_fold: float,
    diffusion_fold: float,
) -> PerturbedReach:
    """Propagate release/loss/diffusion multipliers through the planar model.

    Planar steady state with boundary flux J and loss k:
        c(d) = (J / sqrt(D k)) exp(-d / lambda),  lambda = sqrt(D / k)
    Threshold reach is the distance where c falls to a fixed threshold c*:
        d* = lambda * ln(c(0) / c*)   (0 when c(0) <= c*)

    Consequences: release changes reach only logarithmically and never changes
    lambda; loss and diffusion change lambda with a square root.
    """

    lam = _positive(length_scale_micron, "length_scale_micron")
    ratio = _positive(boundary_to_threshold_ratio, "boundary_to_threshold_ratio")
    fr = _positive(release_fold, "release_fold")
    fk = _positive(loss_fold, "loss_fold")
    fd = _positive(diffusion_fold, "diffusion_fold")

    lam_fold = math.sqrt(fd / fk)
    c0_fold = fr / math.sqrt(fd * fk)

    def reach(length: float, boundary_ratio: float) -> float:
        return length * math.log(boundary_ratio) if boundary_ratio > 1.0 else 0.0

    return PerturbedReach(
        release_fold=fr,
        loss_fold=fk,
        diffusion_fold=fd,
        length_scale_fold=lam_fold,
        boundary_concentration_fold=c0_fold,
        baseline_threshold_reach_micron=reach(lam, ratio),
        perturbed_threshold_reach_micron=reach(lam * lam_fold, ratio * c0_fold),
    )
