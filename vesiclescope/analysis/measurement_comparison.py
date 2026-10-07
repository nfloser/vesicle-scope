"""Explicit measured-versus-predicted comparison without hidden calibration.

Measured assay observations remain observations. This adapter only aligns them
with already stored simulation samples at the same declared time point. It does
not interpolate, convert units, fit parameters, or feed measurements back into
the transport solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from vesiclescope.domain import LongitudinalEVDataset
from vesiclescope.engines import BioFVMRunResult, TransportSample


class PredictionObservable(str, Enum):
    """Stored model quantity selected explicitly for measurement comparison."""

    MEAN_CONCENTRATION = "mean_concentration"
    EXTRACELLULAR_QUANTITY = "extracellular_quantity"
    INTERNALIZED_QUANTITY = "internalized_quantity"


@dataclass(frozen=True, slots=True)
class MeasurementPredictionTarget:
    """Explicit mapping from one assay observation identifier to one model output."""

    observation_identifier: str
    observable: PredictionObservable

    def __post_init__(self) -> None:
        if (
            not isinstance(self.observation_identifier, str)
            or not self.observation_identifier.strip()
        ):
            raise ValueError("observation_identifier must be a non-blank string")
        object.__setattr__(
            self,
            "observation_identifier",
            self.observation_identifier.strip(),
        )
        if not isinstance(self.observable, PredictionObservable):
            raise TypeError("observable must be a PredictionObservable")


@dataclass(frozen=True, slots=True)
class MeasurementPredictionMatch:
    """One measured point aligned to an exact stored model sample when available."""

    condition_id: str
    sample_id: str
    time_min: float
    observation_identifier: str
    observable: PredictionObservable
    measured_value: float
    measured_unit: str
    predicted_value: float | None
    predicted_unit: str
    exact_time_match: bool
    unit_compatible: bool
    residual_prediction_minus_measurement: float | None
    reason: str


def _sample_at_time(
    result: BioFVMRunResult,
    time_min: float,
) -> TransportSample | None:
    matches = tuple(
        sample
        for sample in result.samples
        if math.isclose(sample.time_min, time_min, rel_tol=0.0, abs_tol=1e-9)
    )
    if len(matches) > 1:
        raise ValueError("simulation result contains duplicate stored sample times")
    return matches[0] if matches else None


def _prediction(
    result: BioFVMRunResult,
    sample: TransportSample,
    observable: PredictionObservable,
) -> tuple[float, str]:
    if observable is PredictionObservable.MEAN_CONCENTRATION:
        return sample.mean_concentration, result.concentration_unit
    if observable is PredictionObservable.EXTRACELLULAR_QUANTITY:
        return sample.integrated_field_quantity, result.integrated_quantity_unit
    if observable is PredictionObservable.INTERNALIZED_QUANTITY:
        return sample.internalized_field_quantity, result.internalized_quantity_unit
    raise ValueError(f"unsupported prediction observable: {observable!r}")


def compare_measurements_to_prediction(
    dataset: LongitudinalEVDataset,
    condition_id: str,
    result: BioFVMRunResult,
    targets: tuple[MeasurementPredictionTarget, ...],
) -> tuple[MeasurementPredictionMatch, ...]:
    """Align declared observations to exact stored prediction times.

    A residual is reported only when the assay and model units are already
    identical. Unit conversion requires a separate explicit reviewed adapter.
    Missing model times remain missing; no interpolation is performed.
    """

    if not isinstance(dataset, LongitudinalEVDataset):
        raise TypeError("dataset must be a LongitudinalEVDataset")
    if not isinstance(condition_id, str) or not condition_id.strip():
        raise ValueError("condition_id must be a non-blank string")
    condition = condition_id.strip()
    if not isinstance(result, BioFVMRunResult):
        raise TypeError("result must be a BioFVMRunResult")
    if not result.samples:
        raise ValueError("result must contain at least one stored sample")
    if not isinstance(targets, tuple) or not targets:
        raise ValueError("targets must be a non-empty tuple")
    if not all(isinstance(item, MeasurementPredictionTarget) for item in targets):
        raise TypeError("targets must contain MeasurementPredictionTarget objects")
    identifiers = tuple(item.observation_identifier for item in targets)
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("observation targets must be unique")

    target_by_id = {item.observation_identifier: item for item in targets}
    matches: list[MeasurementPredictionMatch] = []

    timepoints = sorted(
        (
            timepoint
            for timepoint in dataset.timepoints
            if timepoint.condition_id == condition
        ),
        key=lambda item: (item.time_min, item.sample_id, item.biological_replicate_id or ""),
    )

    for timepoint in timepoints:
        for observation in timepoint.observations:
            target = target_by_id.get(observation.identifier)
            if target is None:
                continue
            sample = _sample_at_time(result, timepoint.time_min)
            if sample is None:
                _, predicted_unit = _prediction(
                    result,
                    result.samples[0],
                    target.observable,
                )
                matches.append(
                    MeasurementPredictionMatch(
                        condition_id=condition,
                        sample_id=timepoint.sample_id,
                        time_min=timepoint.time_min,
                        observation_identifier=observation.identifier,
                        observable=target.observable,
                        measured_value=observation.value,
                        measured_unit=observation.unit,
                        predicted_value=None,
                        predicted_unit=predicted_unit,
                        exact_time_match=False,
                        unit_compatible=False,
                        residual_prediction_minus_measurement=None,
                        reason=(
                            "no stored prediction exists at this measurement time; "
                            "no interpolation was performed"
                        ),
                    )
                )
                continue

            predicted_value, predicted_unit = _prediction(
                result,
                sample,
                target.observable,
            )
            compatible = observation.unit == predicted_unit
            matches.append(
                MeasurementPredictionMatch(
                    condition_id=condition,
                    sample_id=timepoint.sample_id,
                    time_min=timepoint.time_min,
                    observation_identifier=observation.identifier,
                    observable=target.observable,
                    measured_value=observation.value,
                    measured_unit=observation.unit,
                    predicted_value=predicted_value,
                    predicted_unit=predicted_unit,
                    exact_time_match=True,
                    unit_compatible=compatible,
                    residual_prediction_minus_measurement=(
                        predicted_value - observation.value
                        if compatible
                        else None
                    ),
                    reason=(
                        "exact stored prediction time and identical units"
                        if compatible
                        else (
                            "exact stored prediction time; units differ, so no "
                            "conversion or numerical residual was inferred"
                        )
                    ),
                )
            )

    return tuple(matches)
