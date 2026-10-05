"""Controlled synthetic diffusion × uptake factor scenarios."""

from __future__ import annotations

from dataclasses import dataclass

from vesiclescope.domain import (
    BoundaryCondition,
    CircularReleaseSource,
    CircularUptakeSink,
    EvidenceCategory,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from .recipient_count import FINITE_RECIPIENT_RING_POSITIONS


DIFFUSION_FACTORS = (0.5, 1.0, 2.0)
UPTAKE_FACTORS = (0.5, 1.0, 2.0)
DIFFUSION_BASELINE = 100.0
UPTAKE_BASELINE = 0.5


@dataclass(frozen=True, slots=True)
class DiffusionUptakeCondition:
    """One condition in the small deterministic full-factorial experiment."""

    diffusion_factor: float
    uptake_factor: float
    experiment: TransportExperiment


def _synthetic_parameter(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic verification input; not a biological default.",),
    )


def _condition(diffusion_factor: float, uptake_factor: float) -> DiffusionUptakeCondition:
    recipients = tuple(
        CircularUptakeSink(
            identifier=f"sink.{index + 1}",
            x_micron=x_micron,
            y_micron=y_micron,
            footprint_radius_micron=15.0,
            effective_volume_micron3=1000.0,
            uptake_rate=_synthetic_parameter(
                f"sink.{index + 1}.uptake",
                UPTAKE_BASELINE * uptake_factor,
                "1/min",
            ),
        )
        for index, (x_micron, y_micron) in enumerate(FINITE_RECIPIENT_RING_POSITIONS)
    )
    experiment = TransportExperiment(
        experiment_id=(
            "synthetic.diffusion-uptake."
            f"d{diffusion_factor:g}.u{uptake_factor:g}"
        ),
        domain=RectangularDomain2D(210.0, 210.0, 25.0),
        duration_min=20.0,
        sample_every_min=5.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=_synthetic_parameter(
            "transport.diffusion",
            DIFFUSION_BASELINE * diffusion_factor,
            "micron^2/min",
        ),
        decay=_synthetic_parameter("transport.decay", 0.0, "1/min"),
        initial_concentration=_synthetic_parameter(
            "initial.concentration", 0.0, "particle_equivalent/micron^3"
        ),
        release_sources=(
            CircularReleaseSource(
                identifier="source.finite-donor",
                x_micron=105.0,
                y_micron=105.0,
                footprint_radius_micron=15.0,
                release_rate=_synthetic_parameter(
                    "source.release", 120.0, "particle_equivalent/min"
                ),
            ),
        ),
        uptake_sinks=recipients,
    )
    return DiffusionUptakeCondition(diffusion_factor, uptake_factor, experiment)


def diffusion_uptake_factor_conditions() -> tuple[DiffusionUptakeCondition, ...]:
    """Return the nine reviewed conditions in stable uptake-major matrix order."""

    return tuple(
        _condition(diffusion_factor, uptake_factor)
        for uptake_factor in UPTAKE_FACTORS
        for diffusion_factor in DIFFUSION_FACTORS
    )
