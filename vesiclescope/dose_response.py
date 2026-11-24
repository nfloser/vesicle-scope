"""Time-resolved exposure → rate multiplier mapping (effect-compartment model).

A declared exposure (for example a hormone pulse) changes EV release or
uptake with a delay. VesicleScope represents that with the standard
pharmacokinetic/pharmacodynamic effect-compartment link (Sheiner et al.,
Clin Pharmacol Ther 1979;25:358-371, doi:10.1002/cpt1979253358):

    dCe/dt = ke0 (C(t) - Ce)
    H(Ce)  = Ce^n / (EC50^n + Ce^n)
    m(t)   = (1 + Emax H(Ce(t))) / (1 + Emax H(C_baseline))

C(t) is piecewise constant (baseline outside the exposure window, baseline +
exposure inside), so Ce(t) is solved exactly. The multiplier is normalized to
1 at the baseline steady state and is averaged over each schedule segment.

Every parameter is a provenance-bearing ScientificParameter. Nothing here
supplies a biological default.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from vesiclescope.domain import (
    BiologicalExposure,
    EvidenceCategory,
    RateSchedule,
    RateScheduleSegment,
    ScientificParameter,
)


# Weakest evidence first: a schedule inherits the weakest input category.
_EVIDENCE_STRENGTH = (
    EvidenceCategory.SYNTHETIC_BENCHMARK,
    EvidenceCategory.ASSUMED,
    EvidenceCategory.INFERRED,
    EvidenceCategory.LITERATURE_ESTIMATE,
    EvidenceCategory.FITTED,
    EvidenceCategory.MEASURED_RELATED_CONTEXT,
    EvidenceCategory.MEASURED_TARGET_CONTEXT,
)

_SUBSTEPS_PER_SEGMENT = 64


class DoseResponseTarget(str, Enum):
    """Transport rate that a dose-response mapping scales."""

    RELEASE_RATE = "release_rate"
    UPTAKE_RATE = "uptake_rate"


def _require(parameter: ScientificParameter, name: str, unit: str | None) -> float:
    if not isinstance(parameter, ScientificParameter):
        raise TypeError(f"{name} must be a ScientificParameter")
    if unit is not None and parameter.unit != unit:
        raise ValueError(f"{name} must use unit {unit!r}, got {parameter.unit!r}")
    return parameter.value


@dataclass(frozen=True, slots=True)
class EffectCompartmentDoseResponse:
    """Delayed sigmoidal effect of an exposure on one transport rate.

    ke0: effect-compartment rate constant [1/min]; 1/ke0 is the delay scale.
    emax: maximal fractional change [1]; > 0 stimulates, -1 < emax < 0 inhibits.
    ec50: concentration of half-maximal effect, same unit as the exposure.
    hill: Hill coefficient [1].
    baseline_concentration: concentration present without the exposure, same
        unit; for endogenous hormones this is not zero and must be declared.
    """

    target: DoseResponseTarget
    ke0: ScientificParameter
    emax: ScientificParameter
    ec50: ScientificParameter
    hill: ScientificParameter
    baseline_concentration: ScientificParameter

    def __post_init__(self) -> None:
        if not isinstance(self.target, DoseResponseTarget):
            raise TypeError("target must be a DoseResponseTarget")
        if _require(self.ke0, "ke0", "1/min") <= 0.0:
            raise ValueError("ke0 must be positive")
        if _require(self.emax, "emax", "1") <= -1.0:
            raise ValueError("emax must exceed -1 so rates stay non-negative")
        if _require(self.ec50, "ec50", None) <= 0.0:
            raise ValueError("ec50 must be positive")
        if _require(self.hill, "hill", "1") <= 0.0:
            raise ValueError("hill must be positive")
        if self.baseline_concentration.unit != self.ec50.unit:
            raise ValueError("baseline_concentration and ec50 must share a unit")
        if _require(self.baseline_concentration, "baseline_concentration", None) < 0.0:
            raise ValueError("baseline_concentration must be non-negative")

    @property
    def parameters(self) -> tuple[ScientificParameter, ...]:
        return (self.ke0, self.emax, self.ec50, self.hill, self.baseline_concentration)

    def occupancy(self, concentration: float) -> float:
        if concentration <= 0.0:
            return 0.0
        n = self.hill.value
        ratio = (concentration / self.ec50.value) ** n
        return ratio / (1.0 + ratio)

    def multiplier_from_effect_concentration(self, concentration: float) -> float:
        emax = self.emax.value
        baseline = 1.0 + emax * self.occupancy(self.baseline_concentration.value)
        return (1.0 + emax * self.occupancy(concentration)) / baseline


@dataclass(frozen=True, slots=True)
class _Piece:
    start: float
    end: float
    concentration: float


def _input_pieces(
    response: EffectCompartmentDoseResponse,
    exposure: BiologicalExposure,
    duration_min: float,
) -> tuple[_Piece, ...]:
    if exposure.concentration.unit != response.ec50.unit:
        raise ValueError("exposure concentration and ec50 must share a unit")
    baseline = response.baseline_concentration.value
    active = baseline + exposure.concentration.value
    start = max(0.0, exposure.start_min)
    end = min(duration_min, exposure.end_min)
    edges = sorted({0.0, duration_min, *(t for t in (start, end) if 0.0 < t < duration_min)})
    pieces = []
    for left, right in zip(edges, edges[1:]):
        inside = start <= left and right <= end and start < end
        pieces.append(_Piece(left, right, active if inside else baseline))
    return tuple(pieces)


def effect_concentration(
    response: EffectCompartmentDoseResponse,
    exposure: BiologicalExposure,
    time_min: float,
    *,
    duration_min: float,
) -> float:
    """Exact effect-compartment concentration Ce(t), starting at baseline steady state.

    An exposure that started before t = 0 is treated as starting at t = 0.
    """

    if not 0.0 <= time_min <= duration_min:
        raise ValueError("time_min must lie within [0, duration_min]")
    ke0 = response.ke0.value
    ce = response.baseline_concentration.value
    for piece in _input_pieces(response, exposure, duration_min):
        if time_min <= piece.start:
            break
        span = min(time_min, piece.end) - piece.start
        ce = piece.concentration + (ce - piece.concentration) * math.exp(-ke0 * span)
    return ce


def rate_multiplier(
    response: EffectCompartmentDoseResponse,
    exposure: BiologicalExposure,
    time_min: float,
    *,
    duration_min: float,
) -> float:
    return response.multiplier_from_effect_concentration(
        effect_concentration(response, exposure, time_min, duration_min=duration_min)
    )


def weakest_evidence(categories: tuple[EvidenceCategory, ...]) -> EvidenceCategory:
    return min(categories, key=_EVIDENCE_STRENGTH.index)


def dose_response_rate_schedule(
    response: EffectCompartmentDoseResponse,
    exposure: BiologicalExposure,
    *,
    duration_min: float,
    segment_min: float,
) -> RateSchedule:
    """Segment-averaged multiplier schedule for a transport experiment.

    Each segment carries the time average of m(t) over the segment (composite
    Simpson rule), so the time integral of the multiplier is preserved to the
    quadrature accuracy within every segment.
    """

    if not isinstance(exposure, BiologicalExposure):
        raise TypeError("exposure must be a BiologicalExposure")
    if not (math.isfinite(duration_min) and duration_min > 0.0):
        raise ValueError("duration_min must be positive")
    if not (math.isfinite(segment_min) and segment_min > 0.0):
        raise ValueError("segment_min must be positive")
    count = round(duration_min / segment_min)
    if count < 1 or abs(count * segment_min - duration_min) > 1e-9 * duration_min:
        raise ValueError("segment_min must tile duration_min exactly")

    segments = []
    for index in range(count):
        start = index * segment_min
        end = duration_min if index == count - 1 else (index + 1) * segment_min
        n = _SUBSTEPS_PER_SEGMENT
        h = (end - start) / n
        total = 0.0
        for k in range(n + 1):
            weight = 1.0 if k in (0, n) else (4.0 if k % 2 else 2.0)
            total += weight * rate_multiplier(
                response, exposure, start + k * h, duration_min=duration_min
            )
        segments.append(RateScheduleSegment(start, end, total * h / 3.0 / (end - start)))

    evidence = weakest_evidence(
        tuple(p.evidence for p in response.parameters)
        + (exposure.evidence, exposure.concentration.evidence)
    )
    derivation = (
        f"effect-compartment dose-response of exposure {exposure.identifier!r} "
        f"({exposure.compound_name}, {exposure.concentration.value:g} "
        f"{exposure.concentration.unit}, {exposure.start_min:g}-{exposure.end_min:g} min) "
        f"on {response.target.value}: ke0={response.ke0.value:g} 1/min, "
        f"Emax={response.emax.value:g}, EC50={response.ec50.value:g} "
        f"{response.ec50.unit}, n={response.hill.value:g}, baseline="
        f"{response.baseline_concentration.value:g} "
        f"{response.baseline_concentration.unit}; segment mean over "
        f"{segment_min:g} min"
    )
    return RateSchedule(segments=tuple(segments), evidence=evidence, derivation=derivation)
