"""UI services for the evidence registry and exposure scenarios."""

from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
from typing import Any

from vesiclescope.domain import (
    BiologicalExposure,
    EvidenceCategory,
    ExposureTarget,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.dose_response import (
    DoseResponseTarget,
    EffectCompartmentDoseResponse,
    effect_concentration,
)
from vesiclescope.engines.biofvm import BioFVMNumerics
from vesiclescope.evidence import EvidenceDatabase, EvidenceRecord, load_evidence
from vesiclescope.evidence.synthesis import synthesize
from vesiclescope.workflows.dose_response import run_dose_response_comparison


EVIDENCE_GAPS = (
    "No measured EV diffusion coefficient in living tissue (hydrogel mechanics, binding and mucus MSD only).",
    "No cell-intrinsic uptake rate constant; culture uptake fractions depend on dose and well geometry.",
    "Human blood half-life only for transfused platelet microparticles (hours), not for small EVs.",
    "Hormone effects are directions in cell lines or associations in humans; no dose-response magnitude for any hormone.",
)

_SCENARIO_LIMITATION = ("User-entered scenario value; not evidence-backed.",)
_MAX_SCENARIO_DURATION_MIN = 24 * 60.0


def _doi_url(record: EvidenceRecord) -> str | None:
    source = record.source
    if source.doi:
        return f"https://doi.org/{source.doi}"
    if source.pmcid:
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{source.pmcid}/"
    if source.pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{source.pmid}/"
    return source.url


def _record_summary(record: EvidenceRecord) -> dict[str, Any]:
    context = {
        name: getattr(record.context, name)
        for name in (
            "species", "tissue", "cell_type", "cell_line", "ev_preparation",
            "measurement_method", "experimental_conditions",
        )
        if getattr(record.context, name)
    }
    payload: dict[str, Any] = {
        "id": record.id,
        "kind": record.kind,
        "evidence": record.evidence.value,
        "statement": record.statement,
        "context": context,
        "limitations": list(record.limitations),
        "tags": list(record.tags),
        "locator": record.locator,
        "verification": record.verification,
        "source": {
            "id": record.source.id,
            "title": record.source.title,
            "authors": record.source.authors,
            "journal": record.source.journal,
            "year": record.source.year,
            "identifier": record.source.identifier,
            "url": _doi_url(record),
            "peer_reviewed": record.source.peer_reviewed,
        },
    }
    if record.kind == "quantity":
        value = record.value
        payload.update(
            quantity=record.quantity,
            unit=record.unit,
            value={"central": value.central, "sd": value.sd, "low": value.low, "high": value.high},
        )
    else:
        payload.update(
            stimulus=record.stimulus,
            outcome=record.outcome.value,
            direction=record.direction.value,
            magnitude=record.magnitude,
            time_course=record.time_course,
        )
    for key in ("mechanism", "markers", "also_changes", "observable"):
        if key in record.extra:
            payload[key] = record.extra[key]
    return payload


def evidence_payload(database: EvidenceDatabase | None = None) -> dict[str, Any]:
    database = database or load_evidence()
    return {
        "checked_on": database.checked_on,
        "source_count": len(database.sources),
        "records": [_record_summary(record) for record in database.records],
        "gaps": list(EVIDENCE_GAPS),
    }


def synthesis_payload(database: EvidenceDatabase | None = None) -> dict[str, Any]:
    result = synthesize(database)
    return {
        "lines": list(result.summary_lines()),
        "record_ids": list(result.record_ids),
        "length_scale_micron": list(result.length_scale_micron),
        "free_diffusion_micron2_per_min": list(result.free_diffusion_micron2_per_min),
        "required_loss_rate_per_min": list(result.required_loss_rate_per_min),
        "required_loss_vs_mouse_clearance": list(result.required_loss_vs_blood_clearance),
        "required_loss_vs_human_pmp_clearance": list(result.required_loss_vs_human_pmp_clearance),
        "peclet_at_free_diffusion": list(result.peclet_at_free_diffusion),
        "ev_exceeds_brain_ecs_width": result.ev_exceeds_brain_ecs_width,
    }


def _number(payload: dict[str, Any], key: str, *, positive: bool = False, minimum: float | None = None) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{key} must be a finite number")
    if positive and value <= 0:
        raise ValueError(f"{key} must be positive")
    if minimum is not None and value < minimum:
        raise ValueError(f"{key} must be at least {minimum:g}")
    return float(value)


def _assumed(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.ASSUMED,
        limitations=_SCENARIO_LIMITATION,
    )


def run_exposure_scenario(
    *,
    experiment: TransportExperiment,
    payload: dict[str, Any],
    runner: Path,
) -> dict[str, Any]:
    """Run baseline vs exposure-driven schedule for a stored experiment."""

    duration = _number(payload, "duration_min", positive=True)
    sample_every = _number(payload, "sample_every_min", positive=True)
    segment = _number(payload, "segment_min", positive=True)
    if duration > _MAX_SCENARIO_DURATION_MIN:
        raise ValueError("scenario duration is limited to 24 h in the local UI")
    unit = payload.get("concentration_unit")
    compound = payload.get("compound")
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("concentration_unit must be a non-blank string")
    if not isinstance(compound, str) or not compound.strip():
        raise ValueError("compound must be a non-blank string")
    try:
        target = DoseResponseTarget(payload.get("target"))
    except ValueError as exc:
        raise ValueError("target must be release_rate or uptake_rate") from exc
    delay = _number(payload, "delay_min", positive=True)
    numerics = BioFVMNumerics(
        grid_spacing_micron=_number(payload, "grid_spacing_micron", positive=True),
        time_step_min=_number(payload, "time_step_min", positive=True),
    )
    scenario_experiment = replace(
        experiment,
        experiment_id=f"{experiment.experiment_id}.scenario",
        duration_min=duration,
        sample_every_min=sample_every,
        release_schedule=None,
        uptake_schedule=None,
    )
    exposure = BiologicalExposure(
        identifier="ui-scenario-exposure",
        compound_name=compound.strip(),
        concentration=_assumed("scenario.exposure", _number(payload, "concentration", minimum=0.0), unit.strip()),
        target=ExposureTarget.DONOR_CELL_POPULATION
        if target is DoseResponseTarget.RELEASE_RATE
        else ExposureTarget.RECIPIENT_CELL_POPULATION,
        start_min=_number(payload, "start_min", minimum=0.0),
        end_min=_number(payload, "end_min", positive=True),
        evidence=EvidenceCategory.ASSUMED,
        limitations=_SCENARIO_LIMITATION,
    )
    response = EffectCompartmentDoseResponse(
        target=target,
        ke0=_assumed("scenario.ke0", 1.0 / delay, "1/min"),
        emax=_assumed("scenario.emax", _number(payload, "emax"), "1"),
        ec50=_assumed("scenario.ec50", _number(payload, "ec50", positive=True), unit.strip()),
        hill=_assumed("scenario.hill", _number(payload, "hill", positive=True), "1"),
        baseline_concentration=_assumed(
            "scenario.baseline", _number(payload, "baseline_concentration", minimum=0.0), unit.strip()
        ),
    )
    comparison = run_dose_response_comparison(
        experiment=scenario_experiment,
        exposure=exposure,
        responses=(("scenario", response),),
        numerics=numerics,
        runner=runner,
        segment_min=segment,
    )
    condition = comparison.conditions[0]
    times = [duration * index / 240 for index in range(241)]
    baseline = comparison.baseline_result.samples
    perturbed = condition.result.samples
    return {
        "derivation": condition.schedule.derivation,
        "evidence": condition.schedule.evidence.value,
        "target": target.value,
        "exposure": {
            "times": times,
            "added": [
                exposure.concentration.value if exposure.start_min <= t < exposure.end_min else 0.0
                for t in times
            ],
            "effect": [
                effect_concentration(response, exposure, t, duration_min=duration)
                - response.baseline_concentration.value
                for t in times
            ],
            "unit": unit.strip(),
        },
        "schedule": [
            {"start_min": s.start_min, "end_min": s.end_min, "multiplier": s.multiplier}
            for s in condition.schedule.segments
        ],
        "samples": {
            "times": [s.time_min for s in baseline],
            "baseline_internalized": [s.internalized_field_quantity for s in baseline],
            "scenario_internalized": [s.internalized_field_quantity for s in perturbed],
            "baseline_extracellular": [s.integrated_field_quantity for s in baseline],
            "scenario_extracellular": [s.integrated_field_quantity for s in perturbed],
            "unit": comparison.baseline_result.integrated_quantity_unit,
        },
        "internalization_rate_ratio": [
            {"time_min": t, "ratio": r} for t, r in comparison.internalization_rate_ratio(condition)
        ],
    }
