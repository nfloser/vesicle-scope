"""Engine-neutral inputs for the first verified transport benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .parameters import ScientificParameter


DIFFUSION_UNIT = "micron^2/min"
RATE_UNIT = "1/min"
RELEASE_RATE_UNIT = "particle_equivalent/min"


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


def _non_negative_finite(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    numeric_value = float(value)
    if not math.isfinite(numeric_value) or numeric_value < 0.0:
        raise ValueError(f"{field_name} must be finite and non-negative")
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

    @property
    def volume_micron3(self) -> float:
        """Physical volume represented by the 2D slice."""

        return self.width_micron * self.height_micron * self.slice_thickness_micron


@dataclass(frozen=True, slots=True)
class PointReleaseSource:
    """A localized synthetic amount-per-time source in the 2D slice."""

    identifier: str
    x_micron: float
    y_micron: float
    release_rate: ScientificParameter

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identifier",
            _required_text(self.identifier, "identifier"),
        )
        object.__setattr__(
            self,
            "x_micron",
            _non_negative_finite(self.x_micron, "x_micron"),
        )
        object.__setattr__(
            self,
            "y_micron",
            _non_negative_finite(self.y_micron, "y_micron"),
        )

        release_rate = _require_parameter(self.release_rate, "release_rate")
        _require_unit(release_rate, RELEASE_RATE_UNIT, "release_rate")
        if release_rate.value < 0.0:
            raise ValueError("release_rate must be non-negative")


@dataclass(frozen=True, slots=True)
class CircularReleaseSource:
    """A finite circular amount-per-time source footprint in the 2D slice."""

    identifier: str
    x_micron: float
    y_micron: float
    footprint_radius_micron: float
    release_rate: ScientificParameter

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identifier",
            _required_text(self.identifier, "identifier"),
        )
        object.__setattr__(
            self,
            "x_micron",
            _non_negative_finite(self.x_micron, "x_micron"),
        )
        object.__setattr__(
            self,
            "y_micron",
            _non_negative_finite(self.y_micron, "y_micron"),
        )
        object.__setattr__(
            self,
            "footprint_radius_micron",
            _positive_finite(
                self.footprint_radius_micron,
                "footprint_radius_micron",
            ),
        )

        release_rate = _require_parameter(self.release_rate, "release_rate")
        _require_unit(release_rate, RELEASE_RATE_UNIT, "release_rate")
        if release_rate.value < 0.0:
            raise ValueError("release_rate must be non-negative")


ReleaseSource = PointReleaseSource | CircularReleaseSource


@dataclass(frozen=True, slots=True)
class PointUptakeSink:
    """A localized synthetic first-order uptake sink with explicit volume."""

    identifier: str
    x_micron: float
    y_micron: float
    effective_volume_micron3: float
    uptake_rate: ScientificParameter

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identifier",
            _required_text(self.identifier, "identifier"),
        )
        object.__setattr__(
            self,
            "x_micron",
            _non_negative_finite(self.x_micron, "x_micron"),
        )
        object.__setattr__(
            self,
            "y_micron",
            _non_negative_finite(self.y_micron, "y_micron"),
        )
        object.__setattr__(
            self,
            "effective_volume_micron3",
            _positive_finite(
                self.effective_volume_micron3,
                "effective_volume_micron3",
            ),
        )

        uptake_rate = _require_parameter(self.uptake_rate, "uptake_rate")
        _require_unit(uptake_rate, RATE_UNIT, "uptake_rate")
        if uptake_rate.value < 0.0:
            raise ValueError("uptake_rate must be non-negative")


@dataclass(frozen=True, slots=True)
class CircularUptakeSink:
    """A finite circular uptake footprint with independent effective volume."""

    identifier: str
    x_micron: float
    y_micron: float
    footprint_radius_micron: float
    effective_volume_micron3: float
    uptake_rate: ScientificParameter

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identifier",
            _required_text(self.identifier, "identifier"),
        )
        object.__setattr__(
            self,
            "x_micron",
            _non_negative_finite(self.x_micron, "x_micron"),
        )
        object.__setattr__(
            self,
            "y_micron",
            _non_negative_finite(self.y_micron, "y_micron"),
        )
        object.__setattr__(
            self,
            "footprint_radius_micron",
            _positive_finite(
                self.footprint_radius_micron,
                "footprint_radius_micron",
            ),
        )
        object.__setattr__(
            self,
            "effective_volume_micron3",
            _positive_finite(
                self.effective_volume_micron3,
                "effective_volume_micron3",
            ),
        )

        uptake_rate = _require_parameter(self.uptake_rate, "uptake_rate")
        _require_unit(uptake_rate, RATE_UNIT, "uptake_rate")
        if uptake_rate.value < 0.0:
            raise ValueError("uptake_rate must be non-negative")


UptakeSink = PointUptakeSink | CircularUptakeSink


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
    release_sources: tuple[ReleaseSource, ...] = ()
    uptake_sinks: tuple[UptakeSink, ...] = ()

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

        if not isinstance(self.release_sources, tuple):
            raise TypeError("release_sources must be a tuple of supported release sources")

        seen_source_ids: set[str] = set()
        for source in self.release_sources:
            if not isinstance(source, (PointReleaseSource, CircularReleaseSource)):
                raise TypeError(
                    "release_sources must contain only supported release source objects"
                )
            if source.identifier in seen_source_ids:
                raise ValueError(f"duplicate release source identifier: {source.identifier!r}")
            seen_source_ids.add(source.identifier)
            if source.x_micron >= self.domain.width_micron:
                raise ValueError(
                    f"release source {source.identifier!r} lies outside domain width"
                )
            if source.y_micron >= self.domain.height_micron:
                raise ValueError(
                    f"release source {source.identifier!r} lies outside domain height"
                )
            if isinstance(source, CircularReleaseSource):
                radius = source.footprint_radius_micron
                if (
                    source.x_micron - radius < 0.0
                    or source.x_micron + radius > self.domain.width_micron
                    or source.y_micron - radius < 0.0
                    or source.y_micron + radius > self.domain.height_micron
                ):
                    raise ValueError(
                        f"circular release source {source.identifier!r} must lie fully "
                        "inside the rectangular domain"
                    )

        if not isinstance(self.uptake_sinks, tuple):
            raise TypeError("uptake_sinks must be a tuple of supported uptake sinks")

        seen_sink_ids: set[str] = set()
        for sink in self.uptake_sinks:
            if not isinstance(sink, (PointUptakeSink, CircularUptakeSink)):
                raise TypeError(
                    "uptake_sinks must contain only supported uptake sink objects"
                )
            if sink.identifier in seen_sink_ids:
                raise ValueError(f"duplicate uptake sink identifier: {sink.identifier!r}")
            seen_sink_ids.add(sink.identifier)
            if sink.x_micron >= self.domain.width_micron:
                raise ValueError(
                    f"uptake sink {sink.identifier!r} lies outside domain width"
                )
            if sink.y_micron >= self.domain.height_micron:
                raise ValueError(
                    f"uptake sink {sink.identifier!r} lies outside domain height"
                )
            if isinstance(sink, CircularUptakeSink):
                radius = sink.footprint_radius_micron
                if (
                    sink.x_micron - radius < 0.0
                    or sink.x_micron + radius > self.domain.width_micron
                    or sink.y_micron - radius < 0.0
                    or sink.y_micron + radius > self.domain.height_micron
                ):
                    raise ValueError(
                        f"circular uptake sink {sink.identifier!r} must lie fully "
                        "inside the rectangular domain"
                    )

        circular_sinks = tuple(
            sink
            for sink in self.uptake_sinks
            if isinstance(sink, CircularUptakeSink)
        )
        for index, left in enumerate(circular_sinks):
            for right in circular_sinks[index + 1 :]:
                center_distance = math.hypot(
                    left.x_micron - right.x_micron,
                    left.y_micron - right.y_micron,
                )
                if center_distance < (
                    left.footprint_radius_micron
                    + right.footprint_radius_micron
                ):
                    raise ValueError(
                        "circular uptake sink footprints must not overlap; "
                        f"{left.identifier!r} overlaps {right.identifier!r}"
                    )
