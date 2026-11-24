"""Synthetic demonstration scenario for exposure-driven rate schedules.

All values are synthetic benchmark inputs chosen to exercise the workflow;
none is a hormone calibration.
"""

from __future__ import annotations

from dataclasses import replace

from vesiclescope.domain import (
    BiologicalExposure,
    EvidenceCategory,
    ExposureTarget,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.dose_response import DoseResponseTarget, EffectCompartmentDoseResponse

from .diffusion_uptake import diffusion_uptake_factor_conditions


_LIMITATION = ("Synthetic verification input; not a biological default.",)


def _p(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=_LIMITATION,
    )


def synthetic_dose_response_experiment() -> TransportExperiment:
    """Reviewed 1x/1x diffusion-uptake geometry, run for 4 h with clearance."""

    base = next(
        condition.experiment
        for condition in diffusion_uptake_factor_conditions()
        if condition.diffusion_factor == 1.0 and condition.uptake_factor == 1.0
    )
    return replace(
        base,
        experiment_id="synthetic.dose-response.baseline",
        duration_min=240.0,
        sample_every_min=5.0,
        decay=_p("transport.decay", 0.05, "1/min"),
    )


def synthetic_hormone_pulse() -> BiologicalExposure:
    return BiologicalExposure(
        identifier="synthetic-hormone-pulse",
        compound_name="synthetic hormone",
        concentration=_p("exposure.concentration", 100.0, "nM"),
        target=ExposureTarget.DONOR_CELL_POPULATION,
        start_min=30.0,
        end_min=150.0,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic 2 h pulse used only to exercise the workflow.",),
    )


def _response(target: DoseResponseTarget, emax: float) -> EffectCompartmentDoseResponse:
    return EffectCompartmentDoseResponse(
        target=target,
        ke0=_p("dose-response.ke0", 1.0 / 30.0, "1/min"),
        emax=_p("dose-response.emax", emax, "1"),
        ec50=_p("dose-response.ec50", 50.0, "nM"),
        hill=_p("dose-response.hill", 1.0, "1"),
        baseline_concentration=_p("dose-response.baseline", 0.0, "nM"),
    )


def synthetic_dose_responses() -> tuple[tuple[str, EffectCompartmentDoseResponse], ...]:
    return (
        ("release, Emax = +1", _response(DoseResponseTarget.RELEASE_RATE, 1.0)),
        ("uptake, Emax = -0.5", _response(DoseResponseTarget.UPTAKE_RATE, -0.5)),
    )
