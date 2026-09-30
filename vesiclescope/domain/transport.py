"""Engine-neutral inputs for the first verified transport benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .parameters import ScientificParameter


DIFFUSION_UNIT = "micron^2/min"
RATE_UNIT = "1/min"


class BoundaryCondition(str, Enum):
    """Boundary conditions currently supported by the v0.1 contract."""

    NO_FLUX = "no_flux"


def _positive_finite(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    numeric_value = float(value)
    if not math.isfinite(numeric_value) or numeric_value <= 0.0:
        raise ValueError(f"{field_name} must be finite and greater than zero")
    return numeric_value


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


def _require_parameter(
    parameter: ScientificParameter,
    field_name: str,
) -> ScientificParameter:
    if not isinstance(parameter, ScientificParameter):
        raise TypeError(f"{field_name} must be a ScientificParameter")
    return parameter


def _require_unit(
    parameter: ScientificParameter,
    expected_unit: str,
    field_name: str,
) -> None:
    if parameter.unit != expected_unit:
        raise ValueError(
            f"{field_name} must use {expected_unit!r}; received {parameter.unit!r}"
        )


@dataclass(frozen=True, slots=True)
class RectangularDomain2D:
    """A bounded two-dimensional domain with explicit physical slice thickness."""

    width_micron: float
    height_micron: float
    slice_thickness_micron: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "width_micron",
            _positive_finite(self.width_micron, "width_micron"),
        )
        object.__setattr__(
            self,
            "height_micron",
            _positive_finite(self.height_micron, "height_micron"),
        )
        object.__setattr__(
            self,
            "slice_thickness_micron",
            _positive_finite(
                self.slice_thickness_micron,
                "slice_thickness_micron",
            ),
        )


@dataclass(frozen=True, slots=True)
class TransportExperiment:
    """Synthetic transport inputs shared by validation code and engine adapters.

    The contract deliberately carries provenance-bearing parameters rather than
    bare diffusion/decay values. No biological defaults are supplied here.
    """

    experiment_id: str
    domain: RectangularDomain2D
    duration_min: float
    sample_every_min: float
    boundary: BoundaryCondition
    diffusion: ScientificParameter
    decay: ScientificParameter
    initial_concentration: ScientificParameter

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "experiment_id",
            _required_text(self.experiment_id, "experiment_id"),
        )

        if not isinstance(self.domain, RectangularDomain2D):
            raise TypeError("domain must be a RectangularDomain2D")

        duration_min = _positive_finite(self.duration_min, "duration_min")
        sample_every_min = _positive_finite(
            self.sample_every_min,
            "sample_every_min",
        )
        if sample_every_min > duration_min:
            raise ValueError("sample_every_min cannot exceed duration_min")
        object.__setattr__(self, "duration_min", duration_min)
        object.__setattr__(self, "sample_every_min", sample_every_min)

        if not isinstance(self.boundary, BoundaryCondition):
            raise TypeError("boundary must be a BoundaryCondition")

        diffusion = _require_parameter(self.diffusion, "diffusion")
        decay = _require_parameter(self.decay, "decay")
        initial_concentration = _require_parameter(
            self.initial_concentration,
            "initial_concentration",
        )

        _require_unit(diffusion, DIFFUSION_UNIT, "diffusion")
        _require_unit(decay, RATE_UNIT, "decay")

        if diffusion.value < 0.0:
            raise ValueError("diffusion must be non-negative")
        if decay.value < 0.0:
            raise ValueError("decay must be non-negative")
        if initial_concentration.value < 0.0:
            raise ValueError("initial_concentration must be non-negative")
