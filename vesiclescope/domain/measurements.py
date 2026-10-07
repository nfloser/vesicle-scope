"""Blood/plasma EV pre-analytics and longitudinal measurement contracts.

These types describe measured assay inputs. They are deliberately separate from
transport parameters so an observed particle count or marker signal cannot
silently become a simulation parameter.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class SpecimenKind(str, Enum):
    """Biological matrix represented by one EV measurement dataset."""

    WHOLE_BLOOD = "whole_blood"
    PLASMA = "plasma"
    SERUM = "serum"


class MeasurementKind(str, Enum):
    """Semantics of an observed EV-related assay quantity."""

    PARTICLE_CONCENTRATION = "particle_concentration"
    PARTICLE_SIZE = "particle_size"
    EV_ASSOCIATED_EVENT_CONCENTRATION = "ev_associated_event_concentration"
    MARKER_POSITIVE_EVENT_CONCENTRATION = "marker_positive_event_concentration"
    MARKER_SIGNAL = "marker_signal"
    CARGO_CONCENTRATION = "cargo_concentration"
    CARGO_SIGNAL = "cargo_signal"


_MARKER_KINDS = frozenset(
    {
        MeasurementKind.MARKER_POSITIVE_EVENT_CONCENTRATION,
        MeasurementKind.MARKER_SIGNAL,
    }
)


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple of strings")
    return tuple(_required_text(value, field_name) for value in values)


def _real(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def _non_negative(value: float, field_name: str) -> float:
    result = _real(value, field_name)
    if result < 0.0:
        raise ValueError(f"{field_name} must be non-negative")
    return result


def _positive(value: float, field_name: str) -> float:
    result = _real(value, field_name)
    if result <= 0.0:
        raise ValueError(f"{field_name} must be greater than zero")
    return result


@dataclass(frozen=True, slots=True)
class CentrifugationStep:
    """One explicitly recorded centrifugation step in sample preparation."""

    relative_centrifugal_force_g: float
    duration_min: float
    retained_fraction: str
    temperature_c: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "relative_centrifugal_force_g",
            _positive(
                self.relative_centrifugal_force_g,
                "relative_centrifugal_force_g",
            ),
        )
        object.__setattr__(
            self,
            "duration_min",
            _positive(self.duration_min, "duration_min"),
        )
        object.__setattr__(
            self,
            "retained_fraction",
            _required_text(self.retained_fraction, "retained_fraction"),
        )
        if self.temperature_c is not None:
            object.__setattr__(
                self,
                "temperature_c",
                _real(self.temperature_c, "temperature_c"),
            )


@dataclass(frozen=True, slots=True)
class BloodEVPreanalytics:
    """Pre-analytical context that can materially affect blood-derived EV data."""

    sample_id: str
    specimen: SpecimenKind
    anticoagulant: str | None
    collection_to_processing_min: float
    centrifugation_steps: tuple[CentrifugationStep, ...] = ()
    residual_platelet_count_per_ul: float | None = None
    hemolysis_assessment: str | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "sample_id", _required_text(self.sample_id, "sample_id"))
        if not isinstance(self.specimen, SpecimenKind):
            raise TypeError("specimen must be a SpecimenKind")
        object.__setattr__(
            self,
            "anticoagulant",
            _optional_text(self.anticoagulant, "anticoagulant"),
        )
        if self.specimen is SpecimenKind.PLASMA and self.anticoagulant is None:
            raise ValueError("plasma pre-analytics require the anticoagulant to be recorded")
        object.__setattr__(
            self,
            "collection_to_processing_min",
            _non_negative(
                self.collection_to_processing_min,
                "collection_to_processing_min",
            ),
        )
        if not isinstance(self.centrifugation_steps, tuple) or not all(
            isinstance(item, CentrifugationStep)
            for item in self.centrifugation_steps
        ):
            raise TypeError(
                "centrifugation_steps must be a tuple of CentrifugationStep objects"
            )
        if self.residual_platelet_count_per_ul is not None:
            object.__setattr__(
                self,
                "residual_platelet_count_per_ul",
                _non_negative(
                    self.residual_platelet_count_per_ul,
                    "residual_platelet_count_per_ul",
                ),
            )
        object.__setattr__(
            self,
            "hemolysis_assessment",
            _optional_text(self.hemolysis_assessment, "hemolysis_assessment"),
        )
        object.__setattr__(
            self,
            "limitations",
            _text_tuple(self.limitations, "limitations"),
        )


@dataclass(frozen=True, slots=True)
class AssayObservation:
    """One measured quantity with explicit assay and detection semantics."""

    identifier: str
    scientific_name: str
    kind: MeasurementKind
    value: float
    unit: str
    method: str
    detection_semantics: str
    markers: tuple[str, ...] = ()
    technical_replicates: int | None = None
    standard_deviation: float | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identifier",
            _required_text(self.identifier, "identifier"),
        )
        object.__setattr__(
            self,
            "scientific_name",
            _required_text(self.scientific_name, "scientific_name"),
        )
        if not isinstance(self.kind, MeasurementKind):
            raise TypeError("kind must be a MeasurementKind")
        object.__setattr__(self, "value", _non_negative(self.value, "value"))
        object.__setattr__(self, "unit", _required_text(self.unit, "unit"))
        object.__setattr__(self, "method", _required_text(self.method, "method"))
        object.__setattr__(
            self,
            "detection_semantics",
            _required_text(self.detection_semantics, "detection_semantics"),
        )
        markers = _text_tuple(self.markers, "markers")
        if len(set(markers)) != len(markers):
            raise ValueError("markers must not contain duplicates")
        if self.kind in _MARKER_KINDS and not markers:
            raise ValueError(f"{self.kind.value} observations require at least one marker")
        object.__setattr__(self, "markers", markers)

        if self.technical_replicates is not None:
            if (
                isinstance(self.technical_replicates, bool)
                or not isinstance(self.technical_replicates, int)
                or self.technical_replicates <= 0
            ):
                raise ValueError("technical_replicates must be a positive integer")
        if self.standard_deviation is not None:
            object.__setattr__(
                self,
                "standard_deviation",
                _non_negative(self.standard_deviation, "standard_deviation"),
            )
        object.__setattr__(self, "notes", _text_tuple(self.notes, "notes"))


@dataclass(frozen=True, slots=True)
class MeasurementTimepoint:
    """A set of observations from one declared sample at one relative time."""

    sample_id: str
    condition_id: str
    time_min: float
    observations: tuple[AssayObservation, ...]
    biological_replicate_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "sample_id",
            _required_text(self.sample_id, "sample_id"),
        )
        object.__setattr__(
            self,
            "condition_id",
            _required_text(self.condition_id, "condition_id"),
        )
        object.__setattr__(self, "time_min", _real(self.time_min, "time_min"))
        object.__setattr__(
            self,
            "biological_replicate_id",
            _optional_text(self.biological_replicate_id, "biological_replicate_id"),
        )
        if not isinstance(self.observations, tuple) or not self.observations:
            raise ValueError("observations must be a non-empty tuple")
        if not all(isinstance(item, AssayObservation) for item in self.observations):
            raise TypeError("observations must contain AssayObservation objects")
        identifiers = tuple(item.identifier for item in self.observations)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("observation identifiers must be unique within one timepoint")


@dataclass(frozen=True, slots=True)
class LongitudinalEVDataset:
    """Longitudinal measured EV-related data kept separate from model parameters."""

    dataset_id: str
    samples: tuple[BloodEVPreanalytics, ...]
    timepoints: tuple[MeasurementTimepoint, ...]
    reference_time_description: str = "Minutes from the declared experimental reference."
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dataset_id",
            _required_text(self.dataset_id, "dataset_id"),
        )
        if not isinstance(self.samples, tuple) or not self.samples:
            raise ValueError("samples must be a non-empty tuple")
        if not all(isinstance(item, BloodEVPreanalytics) for item in self.samples):
            raise TypeError("samples must contain BloodEVPreanalytics objects")
        sample_ids = tuple(item.sample_id for item in self.samples)
        if len(set(sample_ids)) != len(sample_ids):
            raise ValueError("sample identifiers must be unique")
        if not isinstance(self.timepoints, tuple) or not self.timepoints:
            raise ValueError("timepoints must be a non-empty tuple")
        if not all(isinstance(item, MeasurementTimepoint) for item in self.timepoints):
            raise TypeError("timepoints must contain MeasurementTimepoint objects")
        unknown_sample_ids = sorted(
            {item.sample_id for item in self.timepoints} - set(sample_ids)
        )
        if unknown_sample_ids:
            raise ValueError(
                "timepoints reference unknown sample identifiers: "
                + ", ".join(unknown_sample_ids)
            )
        keys = tuple(
            (
                item.condition_id,
                item.time_min,
                item.biological_replicate_id,
            )
            for item in self.timepoints
        )
        if len(set(keys)) != len(keys):
            raise ValueError(
                "condition, time and biological replicate must uniquely identify a timepoint"
            )
        object.__setattr__(
            self,
            "reference_time_description",
            _required_text(
                self.reference_time_description,
                "reference_time_description",
            ),
        )
        object.__setattr__(
            self,
            "limitations",
            _text_tuple(self.limitations, "limitations"),
        )
