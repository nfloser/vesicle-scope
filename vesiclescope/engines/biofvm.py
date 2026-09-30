"""Minimal headless adapter for the pinned BioFVM transport runner."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import subprocess

from vesiclescope.domain import (
    BoundaryCondition,
    CircularReleaseSource,
    CircularUptakeSink,
    PointReleaseSource,
    PointUptakeSink,
    TransportExperiment,
)


_PIN_FILE = Path(__file__).with_name("physicell.env")
_PIN_KEYS = frozenset({"PHYSICELL_RELEASE", "PHYSICELL_COMMIT", "BIOFVM_VERSION"})
_RESULT_HEADER = "VESICLESCOPE_BIOFVM_RESULT\t5"
_PARTICLE_CONCENTRATION_UNIT = "particle_equivalent/micron^3"
_FIELD_ORDERING = "x_fastest_then_y"


class BioFVMRunError(RuntimeError):
    """Raised when the native BioFVM runner cannot complete successfully."""


def _positive_finite(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0.0:
        raise ValueError(f"{field_name} must be finite and greater than zero")
    return numeric


def _finite(value: str, field_name: str) -> float:
    try:
        numeric = float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not math.isfinite(numeric):
        raise ValueError(f"{field_name} must be finite")
    return numeric


def _positive_int_text(value: str, field_name: str) -> int:
    try:
        numeric = int(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if numeric <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return numeric


def _format_number(value: float) -> str:
    numeric = float(value)
    if numeric == 0.0:
        return "0"
    text_value = repr(numeric)
    return text_value[:-2] if text_value.endswith(".0") else text_value


def _is_integer_multiple(total: float, step: float) -> bool:
    ratio = total / step
    return math.isclose(ratio, round(ratio), rel_tol=0.0, abs_tol=1e-9)


def _integrated_quantity_unit(concentration_unit: str) -> str:
    if concentration_unit == _PARTICLE_CONCENTRATION_UNIT:
        return "particle_equivalent"
    return f"{concentration_unit}*micron^3"


def _expected_sample_times(experiment: TransportExperiment) -> tuple[float, ...]:
    count = int(math.floor(experiment.duration_min / experiment.sample_every_min))
    times = [0.0]
    for index in range(1, count + 1):
        time = index * experiment.sample_every_min
        if time < experiment.duration_min and not math.isclose(
            time,
            experiment.duration_min,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            times.append(time)
    if not math.isclose(times[-1], experiment.duration_min, rel_tol=0.0, abs_tol=1e-9):
        times.append(experiment.duration_min)
    return tuple(times)


@dataclass(frozen=True, slots=True)
class BioFVMEngineMetadata:
    """Exact upstream engine identity attached to normalized run results."""

    engine: str
    physicell_release: str
    physicell_commit: str
    biofvm_version: str


def pinned_engine_metadata() -> BioFVMEngineMetadata:
    """Load the single reviewed PhysiCell/BioFVM pin used by build and runtime."""

    values: dict[str, str] = {}
    try:
        lines = _PIN_FILE.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError(f"cannot read BioFVM pin metadata: {_PIN_FILE}") from exc

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise RuntimeError(f"invalid BioFVM pin line: {line!r}")
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in values or not key or not value:
            raise RuntimeError("BioFVM pin metadata contains a duplicate or blank entry")
        values[key] = value

    if set(values) != _PIN_KEYS:
        missing = sorted(_PIN_KEYS - set(values))
        extra = sorted(set(values) - _PIN_KEYS)
        raise RuntimeError(
            f"BioFVM pin metadata keys do not match contract; missing={missing}, extra={extra}"
        )

    return BioFVMEngineMetadata(
        engine="BioFVM",
        physicell_release=values["PHYSICELL_RELEASE"],
        physicell_commit=values["PHYSICELL_COMMIT"],
        biofvm_version=values["BIOFVM_VERSION"],
    )


@dataclass(frozen=True, slots=True)
class BioFVMNumerics:
    """Numerical settings that are solver configuration, not biological inputs."""

    grid_spacing_micron: float
    time_step_min: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "grid_spacing_micron",
            _positive_finite(self.grid_spacing_micron, "grid_spacing_micron"),
        )
        object.__setattr__(
            self,
            "time_step_min",
            _positive_finite(self.time_step_min, "time_step_min"),
        )


@dataclass(frozen=True, slots=True)
class BioFVMReleaseComponent:
    """One native net-export agent component after donor rasterization."""

    x_micron: float
    y_micron: float
    release_rate_per_min: float

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.x_micron, "x_micron"),
            (self.y_micron, "y_micron"),
            (self.release_rate_per_min, "release_rate_per_min"),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be a real number")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric < 0.0:
                raise ValueError(f"{field_name} must be finite and non-negative")
            object.__setattr__(self, field_name, numeric)


@dataclass(frozen=True, slots=True)
class DiscretizedReleaseSource:
    """One scientific release source mapped to one or more BioFVM components."""

    identifier: str
    geometry_kind: str
    x_micron: float
    y_micron: float
    footprint_radius_micron: float
    release_rate_per_min: float
    components: tuple[BioFVMReleaseComponent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, str) or not self.identifier.strip():
            raise ValueError("source identifier must be non-blank")
        object.__setattr__(self, "identifier", self.identifier.strip())
        if self.geometry_kind not in {"point", "circle"}:
            raise ValueError("geometry_kind must be 'point' or 'circle'")
        for value, field_name in (
            (self.x_micron, "x_micron"),
            (self.y_micron, "y_micron"),
            (self.footprint_radius_micron, "footprint_radius_micron"),
            (self.release_rate_per_min, "release_rate_per_min"),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be a real number")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric < 0.0:
                raise ValueError(f"{field_name} must be finite and non-negative")
            object.__setattr__(self, field_name, numeric)
        if self.geometry_kind == "point" and self.footprint_radius_micron != 0.0:
            raise ValueError("point release source must have zero footprint radius")
        if self.geometry_kind == "circle" and self.footprint_radius_micron <= 0.0:
            raise ValueError("circular release source must have positive radius")
        if not isinstance(self.components, tuple) or not self.components:
            raise ValueError("release source must contain at least one component")
        if not all(
            isinstance(item, BioFVMReleaseComponent)
            for item in self.components
        ):
            raise TypeError(
                "components must contain BioFVMReleaseComponent objects"
            )


def _discretize_release_sources_for_grid(
    experiment: TransportExperiment,
    grid_spacing_micron: float,
) -> tuple[DiscretizedReleaseSource, ...]:
    """Rasterize finite donor footprints while preserving aggregate release."""

    if not isinstance(experiment, TransportExperiment):
        raise TypeError("experiment must be a TransportExperiment")

    grid = _positive_finite(grid_spacing_micron, "grid_spacing_micron")
    if not _is_integer_multiple(experiment.domain.width_micron, grid):
        raise ValueError("grid spacing must tile domain width exactly")
    if not _is_integer_multiple(experiment.domain.height_micron, grid):
        raise ValueError("grid spacing must tile domain height exactly")

    nx = round(experiment.domain.width_micron / grid)
    ny = round(experiment.domain.height_micron / grid)
    sources: list[DiscretizedReleaseSource] = []

    for source in experiment.release_sources:
        if isinstance(source, PointReleaseSource):
            component_positions = ((source.x_micron, source.y_micron),)
            geometry_kind = "point"
            radius = 0.0
        elif isinstance(source, CircularReleaseSource):
            selected: list[tuple[float, float]] = []
            radius = source.footprint_radius_micron
            tolerance = max(1e-12, radius * 1e-12)
            for y_index in range(ny):
                y = (y_index + 0.5) * grid
                for x_index in range(nx):
                    x = (x_index + 0.5) * grid
                    if math.hypot(x - source.x_micron, y - source.y_micron) <= (
                        radius + tolerance
                    ):
                        selected.append((x, y))
            if not selected:
                raise ValueError(
                    f"circular release source {source.identifier!r} does not cover "
                    "any voxel centers at the selected grid spacing"
                )
            component_positions = tuple(selected)
            geometry_kind = "circle"
        else:
            raise TypeError("unsupported release source type")

        component_count = len(component_positions)
        rate_share = source.release_rate.value / component_count
        components: list[BioFVMReleaseComponent] = []
        occupied_voxels: set[tuple[int, int]] = set()

        for component_index, (x, y) in enumerate(component_positions):
            voxel = (math.floor(x / grid), math.floor(y / grid))
            if voxel in occupied_voxels:
                raise ValueError(
                    f"release source {source.identifier!r} maps multiple "
                    f"components to numerical voxel {voxel}"
                )
            occupied_voxels.add(voxel)

            component_rate = (
                source.release_rate.value
                - rate_share * (component_count - 1)
                if component_index == component_count - 1
                else rate_share
            )
            components.append(
                BioFVMReleaseComponent(
                    x_micron=x,
                    y_micron=y,
                    release_rate_per_min=component_rate,
                )
            )

        sources.append(
            DiscretizedReleaseSource(
                identifier=source.identifier,
                geometry_kind=geometry_kind,
                x_micron=source.x_micron,
                y_micron=source.y_micron,
                footprint_radius_micron=radius,
                release_rate_per_min=source.release_rate.value,
                components=tuple(components),
            )
        )

    return tuple(sources)


def discretize_release_sources(
    experiment: TransportExperiment,
    numerics: BioFVMNumerics,
) -> tuple[DiscretizedReleaseSource, ...]:
    """Rasterize release sources for one explicit BioFVM grid."""

    if not isinstance(numerics, BioFVMNumerics):
        raise TypeError("numerics must be BioFVMNumerics")
    return _discretize_release_sources_for_grid(
        experiment,
        numerics.grid_spacing_micron,
    )


@dataclass(frozen=True, slots=True)
class BioFVMUptakeComponent:
    """One native uptake agent component after recipient rasterization."""

    x_micron: float
    y_micron: float
    effective_volume_micron3: float

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.x_micron, "x_micron"),
            (self.y_micron, "y_micron"),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be a real number")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric < 0.0:
                raise ValueError(f"{field_name} must be finite and non-negative")
            object.__setattr__(self, field_name, numeric)
        object.__setattr__(
            self,
            "effective_volume_micron3",
            _positive_finite(
                self.effective_volume_micron3,
                "effective_volume_micron3",
            ),
        )


@dataclass(frozen=True, slots=True)
class DiscretizedUptakeRecipient:
    """One engine-neutral recipient mapped to one or more native components."""

    identifier: str
    geometry_kind: str
    x_micron: float
    y_micron: float
    footprint_radius_micron: float
    effective_volume_micron3: float
    uptake_rate_per_min: float
    components: tuple[BioFVMUptakeComponent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, str) or not self.identifier.strip():
            raise ValueError("recipient identifier must be non-blank")
        object.__setattr__(self, "identifier", self.identifier.strip())
        if self.geometry_kind not in {"point", "circle"}:
            raise ValueError("geometry_kind must be 'point' or 'circle'")
        if not isinstance(self.components, tuple) or not self.components:
            raise ValueError("recipient must contain at least one uptake component")
        if not all(isinstance(item, BioFVMUptakeComponent) for item in self.components):
            raise TypeError("components must contain BioFVMUptakeComponent objects")


def _discretize_uptake_sinks_for_grid(
    experiment: TransportExperiment,
    grid_spacing_micron: float,
) -> tuple[DiscretizedUptakeRecipient, ...]:
    """Rasterize finite recipient footprints for one explicit x/y grid."""

    if not isinstance(experiment, TransportExperiment):
        raise TypeError("experiment must be a TransportExperiment")

    grid = _positive_finite(grid_spacing_micron, "grid_spacing_micron")
    if not _is_integer_multiple(experiment.domain.width_micron, grid):
        raise ValueError("grid spacing must tile domain width exactly")
    if not _is_integer_multiple(experiment.domain.height_micron, grid):
        raise ValueError("grid spacing must tile domain height exactly")

    nx = round(experiment.domain.width_micron / grid)
    ny = round(experiment.domain.height_micron / grid)
    occupied: dict[tuple[int, int], str] = {}
    recipients: list[DiscretizedUptakeRecipient] = []

    for sink in experiment.uptake_sinks:
        if isinstance(sink, PointUptakeSink):
            component_positions = ((sink.x_micron, sink.y_micron),)
            geometry_kind = "point"
            radius = 0.0
        elif isinstance(sink, CircularUptakeSink):
            selected: list[tuple[float, float]] = []
            radius = sink.footprint_radius_micron
            tolerance = max(1e-12, radius * 1e-12)
            for y_index in range(ny):
                y = (y_index + 0.5) * grid
                for x_index in range(nx):
                    x = (x_index + 0.5) * grid
                    if math.hypot(x - sink.x_micron, y - sink.y_micron) <= (
                        radius + tolerance
                    ):
                        selected.append((x, y))
            if not selected:
                raise ValueError(
                    f"circular uptake sink {sink.identifier!r} does not cover "
                    "any voxel centers at the selected grid spacing"
                )
            component_positions = tuple(selected)
            geometry_kind = "circle"
        else:
            raise TypeError("unsupported uptake sink type")

        component_count = len(component_positions)
        volume_share = sink.effective_volume_micron3 / component_count
        components: list[BioFVMUptakeComponent] = []

        for component_index, (x, y) in enumerate(component_positions):
            voxel = (math.floor(x / grid), math.floor(y / grid))
            previous = occupied.get(voxel)
            if previous is not None and previous != sink.identifier:
                raise ValueError(
                    "uptake recipients must not share numerical voxels; "
                    f"{previous!r} and {sink.identifier!r} collide at {voxel}"
                )
            if previous == sink.identifier:
                raise ValueError(
                    f"recipient {sink.identifier!r} maps multiple components "
                    f"to numerical voxel {voxel}"
                )
            occupied[voxel] = sink.identifier

            component_volume = (
                sink.effective_volume_micron3
                - volume_share * (component_count - 1)
                if component_index == component_count - 1
                else volume_share
            )
            components.append(
                BioFVMUptakeComponent(
                    x_micron=x,
                    y_micron=y,
                    effective_volume_micron3=component_volume,
                )
            )

        recipients.append(
            DiscretizedUptakeRecipient(
                identifier=sink.identifier,
                geometry_kind=geometry_kind,
                x_micron=sink.x_micron,
                y_micron=sink.y_micron,
                footprint_radius_micron=radius,
                effective_volume_micron3=sink.effective_volume_micron3,
                uptake_rate_per_min=sink.uptake_rate.value,
                components=tuple(components),
            )
        )

    return tuple(recipients)


def discretize_uptake_sinks(
    experiment: TransportExperiment,
    numerics: BioFVMNumerics,
) -> tuple[DiscretizedUptakeRecipient, ...]:
    """Rasterize finite recipient footprints without changing declared total volume."""

    if not isinstance(numerics, BioFVMNumerics):
        raise TypeError("numerics must be BioFVMNumerics")
    return _discretize_uptake_sinks_for_grid(
        experiment,
        numerics.grid_spacing_micron,
    )


@dataclass(frozen=True, slots=True)
class BioFVMGrid2D:
    """Explicit rectangular mesh descriptor for normalized 2D field snapshots."""

    nx: int
    ny: int
    grid_spacing_micron: float
    slice_thickness_micron: float
    ordering: str = _FIELD_ORDERING

    def __post_init__(self) -> None:
        for value, field_name in ((self.nx, "nx"), (self.ny, "ny")):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be greater than zero")

        object.__setattr__(
            self,
            "grid_spacing_micron",
            _positive_finite(self.grid_spacing_micron, "grid_spacing_micron"),
        )
        object.__setattr__(
            self,
            "slice_thickness_micron",
            _positive_finite(
                self.slice_thickness_micron,
                "slice_thickness_micron",
            ),
        )
        if self.ordering != _FIELD_ORDERING:
            raise ValueError(
                f"unsupported BioFVM field ordering: {self.ordering!r}"
            )

    @property
    def voxel_count(self) -> int:
        return self.nx * self.ny


@dataclass(frozen=True, slots=True)
class SpatialFieldSnapshot2D:
    """Immutable row-major extracellular concentration field at one sample time."""

    time_min: float
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if isinstance(self.time_min, bool) or not isinstance(
            self.time_min,
            (int, float),
        ):
            raise TypeError("field snapshot time must be a real number")
        time_min = float(self.time_min)
        if not math.isfinite(time_min) or time_min < 0.0:
            raise ValueError("field snapshot time must be finite and non-negative")
        if not isinstance(self.values, tuple):
            raise TypeError("field snapshot values must be a tuple")

        normalized: list[float] = []
        for value in self.values:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("field snapshot values must be real numbers")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric < 0.0:
                raise ValueError(
                    "field snapshot values must be finite and non-negative"
                )
            normalized.append(numeric)

        object.__setattr__(self, "time_min", time_min)
        object.__setattr__(self, "values", tuple(normalized))


@dataclass(frozen=True, slots=True)
class RecipientUptakeSample:
    """Cumulative internalized field quantity for one recipient at one time."""

    time_min: float
    internalized_field_quantity: float

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.time_min, "time_min"),
            (self.internalized_field_quantity, "internalized_field_quantity"),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be a real number")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric < 0.0:
                raise ValueError(f"{field_name} must be finite and non-negative")
            object.__setattr__(self, field_name, numeric)


@dataclass(frozen=True, slots=True)
class RecipientUptakeSeries:
    """Identifier-stable uptake time series for one configured recipient sink."""

    identifier: str
    x_micron: float
    y_micron: float
    effective_volume_micron3: float
    uptake_rate_per_min: float
    samples: tuple[RecipientUptakeSample, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, str) or not self.identifier.strip():
            raise ValueError("recipient identifier must be non-blank")
        object.__setattr__(self, "identifier", self.identifier.strip())

        for value, field_name, allow_zero in (
            (self.x_micron, "x_micron", True),
            (self.y_micron, "y_micron", True),
            (self.effective_volume_micron3, "effective_volume_micron3", False),
            (self.uptake_rate_per_min, "uptake_rate_per_min", True),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be a real number")
            numeric = float(value)
            valid = numeric >= 0.0 if allow_zero else numeric > 0.0
            if not math.isfinite(numeric) or not valid:
                qualifier = "non-negative" if allow_zero else "greater than zero"
                raise ValueError(f"{field_name} must be finite and {qualifier}")
            object.__setattr__(self, field_name, numeric)

        if not isinstance(self.samples, tuple):
            raise TypeError("recipient samples must be a tuple")
        if not all(isinstance(sample, RecipientUptakeSample) for sample in self.samples):
            raise TypeError("recipient samples must contain RecipientUptakeSample objects")


@dataclass(frozen=True, slots=True)
class TransportSample:
    """Normalized spatial summary at one requested simulation time."""

    time_min: float
    mean_concentration: float
    min_concentration: float
    max_concentration: float
    integrated_field_quantity: float
    internalized_field_quantity: float

    def __post_init__(self) -> None:
        values = (
            self.time_min,
            self.mean_concentration,
            self.min_concentration,
            self.max_concentration,
            self.integrated_field_quantity,
            self.internalized_field_quantity,
        )
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            raise TypeError("transport sample values must be real numbers")
        numeric = tuple(float(value) for value in values)
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("transport sample values must be finite")
        if numeric[0] < 0.0:
            raise ValueError("sample time must be non-negative")

        mean = numeric[1]
        minimum = numeric[2]
        maximum = numeric[3]
        if minimum > maximum:
            raise ValueError("sample minimum cannot exceed maximum")
        if mean < minimum:
            if not math.isclose(mean, minimum, rel_tol=1e-12, abs_tol=1e-15):
                raise ValueError("sample minimum, mean and maximum are inconsistent")
            mean = minimum
        elif mean > maximum:
            if not math.isclose(mean, maximum, rel_tol=1e-12, abs_tol=1e-15):
                raise ValueError("sample minimum, mean and maximum are inconsistent")
            mean = maximum

        object.__setattr__(self, "time_min", numeric[0])
        object.__setattr__(self, "mean_concentration", mean)
        object.__setattr__(self, "min_concentration", minimum)
        object.__setattr__(self, "max_concentration", maximum)
        if numeric[4] < 0.0:
            raise ValueError("sample integrated field quantity must be non-negative")
        if numeric[5] < 0.0:
            raise ValueError("sample internalized field quantity must be non-negative")
        object.__setattr__(self, "integrated_field_quantity", numeric[4])
        object.__setattr__(self, "internalized_field_quantity", numeric[5])


@dataclass(frozen=True, slots=True)
class BioFVMRunResult:
    """Engine-neutral identity plus normalized summary and spatial samples."""

    experiment_id: str
    concentration_unit: str
    integrated_quantity_unit: str
    internalized_quantity_unit: str
    engine: BioFVMEngineMetadata
    grid: BioFVMGrid2D
    samples: tuple[TransportSample, ...]
    field_snapshots: tuple[SpatialFieldSnapshot2D, ...]
    recipient_uptake_series: tuple[RecipientUptakeSeries, ...]


def _validate_mapping(
    experiment: TransportExperiment,
    numerics: BioFVMNumerics,
) -> None:
    if not isinstance(experiment, TransportExperiment):
        raise TypeError("experiment must be a TransportExperiment")
    if not isinstance(numerics, BioFVMNumerics):
        raise TypeError("numerics must be BioFVMNumerics")
    if experiment.boundary is not BoundaryCondition.NO_FLUX:
        raise ValueError(f"unsupported BioFVM boundary: {experiment.boundary!r}")

    if len(experiment.release_sources) > 1:
        raise ValueError("the v0.1 BioFVM adapter supports at most one release source")
    if experiment.release_sources and (
        experiment.initial_concentration.unit != _PARTICLE_CONCENTRATION_UNIT
    ):
        raise ValueError(
            "localized particle-equivalent release requires concentration unit "
            f"{_PARTICLE_CONCENTRATION_UNIT!r}"
        )

    grid = numerics.grid_spacing_micron
    if not _is_integer_multiple(experiment.domain.width_micron, grid):
        raise ValueError("grid spacing must tile domain width exactly")
    if not _is_integer_multiple(experiment.domain.height_micron, grid):
        raise ValueError("grid spacing must tile domain height exactly")

    discretize_release_sources(experiment, numerics)
    discretize_uptake_sinks(experiment, numerics)

    dt = numerics.time_step_min
    if not _is_integer_multiple(experiment.duration_min, dt):
        raise ValueError("time step must tile experiment duration exactly")
    if not _is_integer_multiple(experiment.sample_every_min, dt):
        raise ValueError("time step must tile sample interval exactly")


def build_command(
    experiment: TransportExperiment,
    numerics: BioFVMNumerics,
    executable: Path,
) -> tuple[str, ...]:
    """Map a validated transport contract to the native runner command."""

    _validate_mapping(experiment, numerics)
    executable_path = Path(executable)
    if not str(executable_path):
        raise ValueError("executable path must not be blank")

    command = [
        str(executable_path),
        "--width-micron",
        _format_number(experiment.domain.width_micron),
        "--height-micron",
        _format_number(experiment.domain.height_micron),
        "--slice-thickness-micron",
        _format_number(experiment.domain.slice_thickness_micron),
        "--duration-min",
        _format_number(experiment.duration_min),
        "--sample-every-min",
        _format_number(experiment.sample_every_min),
        "--boundary",
        experiment.boundary.value,
        "--diffusion-micron2-per-min",
        _format_number(experiment.diffusion.value),
        "--decay-per-min",
        _format_number(experiment.decay.value),
        "--initial-concentration",
        _format_number(experiment.initial_concentration.value),
        "--concentration-unit",
        experiment.initial_concentration.unit,
        "--grid-spacing-micron",
        _format_number(numerics.grid_spacing_micron),
        "--time-step-min",
        _format_number(numerics.time_step_min),
    ]

    sources = discretize_release_sources(experiment, numerics)
    if sources:
        source = sources[0]
        command.extend(
            (
                "--source-kind",
                source.geometry_kind,
                "--source-x-micron",
                _format_number(source.x_micron),
                "--source-y-micron",
                _format_number(source.y_micron),
                "--source-radius-micron",
                _format_number(source.footprint_radius_micron),
                "--source-rate-particle-equivalent-per-min",
                _format_number(source.release_rate_per_min),
                "--source-component-count",
                str(len(source.components)),
            )
        )
        for component_index, component in enumerate(source.components):
            component_prefix = f"--source-component-{component_index}"
            command.extend(
                (
                    f"{component_prefix}-x-micron",
                    _format_number(component.x_micron),
                    f"{component_prefix}-y-micron",
                    _format_number(component.y_micron),
                    f"{component_prefix}-rate-particle-equivalent-per-min",
                    _format_number(component.release_rate_per_min),
                )
            )

    recipients = discretize_uptake_sinks(experiment, numerics)
    command.extend(("--uptake-count", str(len(recipients))))
    for index, recipient in enumerate(recipients):
        prefix = f"--uptake-{index}"
        command.extend(
            (
                f"{prefix}-kind",
                recipient.geometry_kind,
                f"{prefix}-x-micron",
                _format_number(recipient.x_micron),
                f"{prefix}-y-micron",
                _format_number(recipient.y_micron),
                f"{prefix}-radius-micron",
                _format_number(recipient.footprint_radius_micron),
                f"{prefix}-volume-micron3",
                _format_number(recipient.effective_volume_micron3),
                f"{prefix}-rate-per-min",
                _format_number(recipient.uptake_rate_per_min),
                f"{prefix}-component-count",
                str(len(recipient.components)),
            )
        )
        for component_index, component in enumerate(recipient.components):
            component_prefix = f"{prefix}-component-{component_index}"
            command.extend(
                (
                    f"{component_prefix}-x-micron",
                    _format_number(component.x_micron),
                    f"{component_prefix}-y-micron",
                    _format_number(component.y_micron),
                    f"{component_prefix}-volume-micron3",
                    _format_number(component.effective_volume_micron3),
                )
            )

    return tuple(command)



def parse_result(
    experiment: TransportExperiment,
    stdout: str,
) -> BioFVMRunResult:
    """Parse and cross-check the native runner's TSV v5 result contract."""

    if not isinstance(experiment, TransportExperiment):
        raise TypeError("experiment must be a TransportExperiment")
    if not isinstance(stdout, str):
        raise TypeError("stdout must be text")

    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines or lines[0] != _RESULT_HEADER:
        raise ValueError("BioFVM result header is missing or unsupported")

    metadata: dict[str, str] = {}
    grid: BioFVMGrid2D | None = None
    samples: list[TransportSample] = []
    field_snapshots: list[SpatialFieldSnapshot2D] = []
    recipient_metadata: dict[
        int,
        tuple[str, float, float, float, float, float, int],
    ] = {}
    recipient_samples: dict[int, list[RecipientUptakeSample]] = {}

    for line in lines[1:]:
        fields = line.split("\t")

        if fields[0] == "grid":
            if grid is not None:
                raise ValueError("BioFVM result contains duplicate grid metadata")
            if len(fields) != 6:
                raise ValueError(f"invalid BioFVM grid line: {line!r}")
            grid = BioFVMGrid2D(
                nx=_positive_int_text(fields[1], "grid nx"),
                ny=_positive_int_text(fields[2], "grid ny"),
                grid_spacing_micron=_finite(fields[3], "grid spacing"),
                slice_thickness_micron=_finite(fields[4], "grid slice thickness"),
                ordering=fields[5],
            )
            continue

        if fields[0] == "recipient":
            if len(fields) != 9:
                raise ValueError(f"invalid BioFVM recipient line: {line!r}")
            try:
                index = int(fields[1])
            except ValueError as exc:
                raise ValueError("recipient index must be an integer") from exc
            if index < 0:
                raise ValueError("recipient index must be non-negative")
            if index in recipient_metadata:
                raise ValueError(f"duplicate BioFVM recipient index: {index}")
            geometry_kind = fields[2]
            if geometry_kind not in {"point", "circle"}:
                raise ValueError(
                    f"unsupported BioFVM recipient geometry: {geometry_kind!r}"
                )
            component_count = _positive_int_text(
                fields[8],
                "recipient component count",
            )
            recipient_metadata[index] = (
                geometry_kind,
                _finite(fields[3], "recipient x"),
                _finite(fields[4], "recipient y"),
                _finite(fields[5], "recipient footprint radius"),
                _finite(fields[6], "recipient effective volume"),
                _finite(fields[7], "recipient uptake rate"),
                component_count,
            )
            recipient_samples[index] = []
            continue

        if fields[0] == "sample":
            if len(fields) != 6:
                raise ValueError(f"invalid BioFVM sample line: {line!r}")
            samples.append(
                TransportSample(
                    time_min=_finite(fields[1], "sample time"),
                    mean_concentration=_finite(fields[2], "sample mean"),
                    min_concentration=_finite(fields[3], "sample minimum"),
                    max_concentration=_finite(fields[4], "sample maximum"),
                    integrated_field_quantity=(
                        _finite(fields[2], "sample mean")
                        * experiment.domain.volume_micron3
                    ),
                    internalized_field_quantity=_finite(
                        fields[5],
                        "sample internalized field quantity",
                    ),
                )
            )
            continue

        if fields[0] == "field":
            if len(fields) < 3:
                raise ValueError(f"invalid BioFVM field line: {line!r}")
            field_snapshots.append(
                SpatialFieldSnapshot2D(
                    time_min=_finite(fields[1], "field time"),
                    values=tuple(
                        _finite(value, "field concentration")
                        for value in fields[2:]
                    ),
                )
            )
            continue

        if fields[0] == "recipient_uptake":
            if len(fields) != 4:
                raise ValueError(f"invalid BioFVM recipient uptake line: {line!r}")
            try:
                index = int(fields[2])
            except ValueError as exc:
                raise ValueError("recipient uptake index must be an integer") from exc
            if index not in recipient_samples:
                raise ValueError(f"unknown BioFVM recipient uptake index: {index}")
            recipient_samples[index].append(
                RecipientUptakeSample(
                    time_min=_finite(fields[1], "recipient uptake time"),
                    internalized_field_quantity=_finite(
                        fields[3],
                        "recipient internalized quantity",
                    ),
                )
            )
            continue

        if len(fields) != 2 or fields[0] not in {
            "engine",
            "physicell_release",
            "physicell_commit",
            "biofvm_version",
        }:
            raise ValueError(f"invalid BioFVM metadata line: {line!r}")
        if fields[0] in metadata:
            raise ValueError(f"duplicate BioFVM metadata field: {fields[0]}")
        metadata[fields[0]] = fields[1]

    expected = pinned_engine_metadata()
    observed = BioFVMEngineMetadata(
        engine=metadata.get("engine", ""),
        physicell_release=metadata.get("physicell_release", ""),
        physicell_commit=metadata.get("physicell_commit", ""),
        biofvm_version=metadata.get("biofvm_version", ""),
    )
    if observed != expected:
        raise ValueError(
            f"BioFVM engine metadata does not match the reviewed pin: {observed!r}"
        )

    if grid is None:
        raise ValueError("BioFVM result contains no grid metadata")
    if not math.isclose(
        grid.nx * grid.grid_spacing_micron,
        experiment.domain.width_micron,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("BioFVM grid width does not match experiment domain")
    if not math.isclose(
        grid.ny * grid.grid_spacing_micron,
        experiment.domain.height_micron,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("BioFVM grid height does not match experiment domain")
    if not math.isclose(
        grid.slice_thickness_micron,
        experiment.domain.slice_thickness_micron,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("BioFVM grid slice thickness does not match experiment")

    if not samples:
        raise ValueError("BioFVM result contains no samples")
    if len(field_snapshots) != len(samples):
        raise ValueError(
            "BioFVM result must contain exactly one field snapshot per sample"
        )

    expected_recipient_indexes = set(range(len(experiment.uptake_sinks)))
    if set(recipient_metadata) != expected_recipient_indexes:
        raise ValueError(
            "BioFVM recipient metadata does not match configured uptake sinks"
        )

    expected_discretized = _discretize_uptake_sinks_for_grid(
        experiment,
        grid.grid_spacing_micron,
    )

    recipient_series: list[RecipientUptakeSeries] = []
    for index, sink in enumerate(experiment.uptake_sinks):
        observed_recipient = recipient_metadata[index]
        expected_recipient = expected_discretized[index]

        if observed_recipient[0] != expected_recipient.geometry_kind:
            raise ValueError(
                f"BioFVM recipient geometry does not match sink {sink.identifier!r}"
            )
        expected_values = (
            expected_recipient.x_micron,
            expected_recipient.y_micron,
            expected_recipient.footprint_radius_micron,
            expected_recipient.effective_volume_micron3,
            expected_recipient.uptake_rate_per_min,
        )
        if any(
            not math.isclose(observed_value, expected_value, rel_tol=0.0, abs_tol=1e-12)
            for observed_value, expected_value in zip(
                observed_recipient[1:6],
                expected_values,
            )
        ):
            raise ValueError(
                f"BioFVM recipient metadata does not match sink {sink.identifier!r}"
            )
        if observed_recipient[6] != len(expected_recipient.components):
            raise ValueError(
                f"BioFVM recipient component count does not match sink {sink.identifier!r}"
            )

        series_samples = tuple(recipient_samples[index])
        if len(series_samples) != len(samples):
            raise ValueError(
                f"BioFVM recipient {sink.identifier!r} must have one uptake value per sample"
            )
        for previous, current in zip(series_samples, series_samples[1:]):
            if current.time_min <= previous.time_min:
                raise ValueError(
                    f"recipient {sink.identifier!r} uptake times must be strictly increasing"
                )
            if current.internalized_field_quantity + 1e-12 < previous.internalized_field_quantity:
                raise ValueError(
                    f"recipient {sink.identifier!r} internalized quantity must not decrease"
                )

        recipient_series.append(
            RecipientUptakeSeries(
                identifier=sink.identifier,
                x_micron=sink.x_micron,
                y_micron=sink.y_micron,
                effective_volume_micron3=sink.effective_volume_micron3,
                uptake_rate_per_min=sink.uptake_rate.value,
                samples=series_samples,
            )
        )

    if not experiment.uptake_sinks:
        if any(
            not math.isclose(
                sample.internalized_field_quantity,
                0.0,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            for sample in samples
        ):
            raise ValueError(
                "BioFVM result reports internalized quantity without an uptake sink"
            )
    elif not math.isclose(
        samples[0].internalized_field_quantity,
        0.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("BioFVM uptake result must start with zero internalized quantity")

    for previous, current in zip(samples, samples[1:]):
        if current.time_min <= previous.time_min:
            raise ValueError("BioFVM sample times must be strictly increasing")
        if (
            experiment.uptake_sinks
            and current.internalized_field_quantity + 1e-12
            < previous.internalized_field_quantity
        ):
            raise ValueError(
                "BioFVM internalized field quantity must not decrease when uptake is active"
            )

    expected_times = _expected_sample_times(experiment)
    observed_times = tuple(sample.time_min for sample in samples)
    if len(observed_times) != len(expected_times) or any(
        not math.isclose(observed_time, expected_time, rel_tol=0.0, abs_tol=1e-9)
        for observed_time, expected_time in zip(observed_times, expected_times)
    ):
        raise ValueError(
            f"BioFVM sample times do not match requested output: "
            f"expected={expected_times}, observed={observed_times}"
        )

    field_times = tuple(snapshot.time_min for snapshot in field_snapshots)
    if any(
        not math.isclose(field_time, sample_time, rel_tol=0.0, abs_tol=1e-9)
        for field_time, sample_time in zip(field_times, observed_times)
    ):
        raise ValueError("BioFVM field times must match summary sample times exactly")

    for series in recipient_series:
        recipient_times = tuple(sample.time_min for sample in series.samples)
        if any(
            not math.isclose(recipient_time, sample_time, rel_tol=0.0, abs_tol=1e-9)
            for recipient_time, sample_time in zip(recipient_times, observed_times)
        ):
            raise ValueError(
                f"recipient {series.identifier!r} uptake times must match summary samples"
            )
        if not math.isclose(
            series.samples[0].internalized_field_quantity,
            0.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(f"recipient {series.identifier!r} uptake must start at zero")

    for sample_index, (sample, snapshot) in enumerate(zip(samples, field_snapshots)):
        if len(snapshot.values) != grid.voxel_count:
            raise ValueError(
                "BioFVM field value count does not match grid dimensions"
            )
        field_mean = sum(snapshot.values) / float(grid.voxel_count)
        field_min = min(snapshot.values)
        field_max = max(snapshot.values)
        field_integrated = field_mean * experiment.domain.volume_micron3

        for observed_value, derived_value, label in (
            (sample.mean_concentration, field_mean, "mean"),
            (sample.min_concentration, field_min, "minimum"),
            (sample.max_concentration, field_max, "maximum"),
        ):
            if not math.isclose(
                observed_value,
                derived_value,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    f"BioFVM field-derived {label} does not match sample summary"
                )
        if not math.isclose(
            sample.integrated_field_quantity,
            field_integrated,
            rel_tol=1e-12,
            abs_tol=1e-8,
        ):
            raise ValueError(
                "BioFVM field-derived integrated quantity does not match sample summary"
            )

        recipient_total = sum(
            series.samples[sample_index].internalized_field_quantity
            for series in recipient_series
        )
        if not math.isclose(
            sample.internalized_field_quantity,
            recipient_total,
            rel_tol=1e-12,
            abs_tol=1e-8,
        ):
            raise ValueError(
                "BioFVM aggregate internalized quantity does not match recipient sum"
            )

    return BioFVMRunResult(
        experiment_id=experiment.experiment_id,
        concentration_unit=experiment.initial_concentration.unit,
        integrated_quantity_unit=_integrated_quantity_unit(
            experiment.initial_concentration.unit
        ),
        internalized_quantity_unit=_integrated_quantity_unit(
            experiment.initial_concentration.unit
        ),
        engine=observed,
        grid=grid,
        samples=tuple(samples),
        field_snapshots=tuple(field_snapshots),
        recipient_uptake_series=tuple(recipient_series),
    )


def run_transport(
    experiment: TransportExperiment,
    numerics: BioFVMNumerics,
    executable: Path,
) -> BioFVMRunResult:
    """Run the pinned native BioFVM executable without invoking a shell."""

    command = build_command(experiment, numerics, executable)
    try:
        completed = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", None)
        detail = str(stderr).strip() if stderr else str(exc)
        raise BioFVMRunError(f"BioFVM transport run failed: {detail}") from exc

    result = parse_result(experiment, completed.stdout)
    if not math.isclose(
        result.grid.grid_spacing_micron,
        numerics.grid_spacing_micron,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError(
            "BioFVM result grid spacing does not match requested numerical configuration"
        )
    return result
