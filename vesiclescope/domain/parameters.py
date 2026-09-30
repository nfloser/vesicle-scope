"""Validated provenance metadata for scientifically meaningful parameters.

This module intentionally stores units as explicit text rather than performing
unit conversion. Canonicalization belongs at a numerical-engine boundary once
that boundary exists; accepting an unstated unit is never valid.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class EvidenceCategory(str, Enum):
    """How a parameter value entered a VesicleScope experiment."""

    MEASURED_TARGET_CONTEXT = "measured_target_context"
    MEASURED_RELATED_CONTEXT = "measured_related_context"
    LITERATURE_ESTIMATE = "literature_estimate"
    FITTED = "fitted"
    INFERRED = "inferred"
    ASSUMED = "assumed"
    SYNTHETIC_BENCHMARK = "synthetic_benchmark"


_SOURCE_REQUIRED = frozenset(
    {
        EvidenceCategory.MEASURED_TARGET_CONTEXT,
        EvidenceCategory.MEASURED_RELATED_CONTEXT,
        EvidenceCategory.LITERATURE_ESTIMATE,
        EvidenceCategory.FITTED,
        EvidenceCategory.INFERRED,
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


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    """A durable source identifier and optional precise source location."""

    identifier: str
    location: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "identifier", _required_text(self.identifier, "identifier"))
        object.__setattr__(self, "location", _optional_text(self.location, "location"))


@dataclass(frozen=True, slots=True)
class ParameterContext:
    """Biological and experimental context in which evidence was obtained."""

    species: str | None = None
    tissue: str | None = None
    cell_type: str | None = None
    cell_line: str | None = None
    ev_preparation: str | None = None
    measurement_method: str | None = None
    experimental_conditions: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "species",
            "tissue",
            "cell_type",
            "cell_line",
            "ev_preparation",
            "measurement_method",
            "experimental_conditions",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_text(getattr(self, field_name), field_name),
            )


@dataclass(frozen=True, slots=True)
class ScientificParameter:
    """A numerical model input with explicit units and evidence provenance."""

    identifier: str
    scientific_name: str
    value: float
    unit: str
    evidence: EvidenceCategory
    source: EvidenceSource | None = None
    context: ParameterContext | None = None
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "identifier", _required_text(self.identifier, "identifier"))
        object.__setattr__(
            self,
            "scientific_name",
            _required_text(self.scientific_name, "scientific_name"),
        )
        object.__setattr__(self, "unit", _required_text(self.unit, "unit"))

        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise TypeError("value must be a real number")
        numeric_value = float(self.value)
        if not math.isfinite(numeric_value):
            raise ValueError("value must be finite")
        object.__setattr__(self, "value", numeric_value)

        if not isinstance(self.evidence, EvidenceCategory):
            raise TypeError("evidence must be an EvidenceCategory")
        if self.source is not None and not isinstance(self.source, EvidenceSource):
            raise TypeError("source must be an EvidenceSource or None")
        if self.context is not None and not isinstance(self.context, ParameterContext):
            raise TypeError("context must be a ParameterContext or None")
        if self.evidence in _SOURCE_REQUIRED and self.source is None:
            raise ValueError(f"{self.evidence.value} parameters require an evidence source")

        object.__setattr__(
            self,
            "assumptions",
            _text_tuple(self.assumptions, "assumptions"),
        )
        object.__setattr__(
            self,
            "limitations",
            _text_tuple(self.limitations, "limitations"),
        )
