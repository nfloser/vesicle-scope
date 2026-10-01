"""Engine-independent radial analysis from a finite circular donor boundary."""

from __future__ import annotations

from dataclasses import dataclass
import math

from vesiclescope.domain import CircularReleaseSource, TransportExperiment
from vesiclescope.engines import BioFVMRunResult


_DISTANCE_TOLERANCE = 1e-9


def _finite(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field_name} must be finite")
    return numeric


def _finite_non_negative(value: float, field_name: str) -> float:
    numeric = _finite(value, field_name)
    if numeric < 0.0:
        raise ValueError(f"{field_name} must be non-negative")
    return numeric


def _positive(value: float, field_name: str) -> float:
    numeric = _finite(value, field_name)
    if numeric <= 0.0:
        raise ValueError(f"{field_name} must be greater than zero")
    return numeric


def _validated_edges(edges_micron: tuple[float, ...]) -> tuple[float, ...]:
    if not isinstance(edges_micron, tuple):
        raise TypeError("edges_micron must be a tuple")
    if len(edges_micron) < 2:
        raise ValueError("at least two donor-boundary distance edges are required")

    edges = tuple(
        _finite_non_negative(value, "donor-boundary distance edge")
        for value in edges_micron
    )
    if not math.isclose(edges[0], 0.0, rel_tol=0.0, abs_tol=_DISTANCE_TOLERANCE):
        raise ValueError("donor-boundary radial bins must start at zero")
    if any(right <= left for left, right in zip(edges, edges[1:])):
        raise ValueError("donor-boundary distance edges must be strictly increasing")
    return edges


def fixed_width_distance_edges(
    *,
    max_distance_micron: float,
    bin_width_micron: float,
) -> tuple[float, ...]:
    """Build exact fixed-width radial edges starting at the donor boundary."""

    maximum = _positive(max_distance_micron, "max_distance_micron")
    width = _positive(bin_width_micron, "bin_width_micron")
    ratio = maximum / width
    count = round(ratio)
    if count <= 0 or not math.isclose(
        ratio,
        count,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError(
            "max_distance_micron must be an integer multiple of bin_width_micron"
        )
    return tuple(index * width for index in range(count + 1))


def distance_from_circular_donor_boundary(
    source: CircularReleaseSource,
    *,
    x_micron: float,
    y_micron: float,
) -> float:
    """Return signed radial distance from a circular donor boundary.

    Negative values are inside the donor footprint, zero is on the declared
    physical boundary, and positive values are extracellular.
    """

    if not isinstance(source, CircularReleaseSource):
        raise TypeError("source must be a CircularReleaseSource")
    x = _finite(x_micron, "x_micron")
    y = _finite(y_micron, "y_micron")
    return math.hypot(x - source.x_micron, y - source.y_micron) - (
        source.footprint_radius_micron
    )


@dataclass(frozen=True, slots=True)
class DonorBoundaryRadialBin:
    """Half-open extracellular field bin measured from the donor boundary."""

    lower_bound_micron: float
    upper_bound_micron: float
    interval_semantics: str
    voxel_count: int
    mean_concentration: float
    integrated_field_quantity: float
    concentration_unit: str
    quantity_unit: str

    def __post_init__(self) -> None:
        lower = _finite_non_negative(self.lower_bound_micron, "lower_bound_micron")
        upper = _positive(self.upper_bound_micron, "upper_bound_micron")
        if upper <= lower:
            raise ValueError("radial-bin upper bound must exceed lower bound")
        object.__setattr__(self, "lower_bound_micron", lower)
        object.__setattr__(self, "upper_bound_micron", upper)

        if self.interval_semantics != "[lower, upper)":
            raise ValueError("radial bins must use [lower, upper) semantics")
        if isinstance(self.voxel_count, bool) or not isinstance(self.voxel_count, int):
            raise TypeError("voxel_count must be an integer")
        if self.voxel_count < 0:
            raise ValueError("voxel_count must be non-negative")

        object.__setattr__(
            self,
            "mean_concentration",
            _finite_non_negative(self.mean_concentration, "mean_concentration"),
        )
        object.__setattr__(
            self,
            "integrated_field_quantity",
            _finite_non_negative(
                self.integrated_field_quantity,
                "integrated_field_quantity",
            ),
        )
        for field_name in ("concentration_unit", "quantity_unit"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be non-blank")
            object.__setattr__(self, field_name, value.strip())


@dataclass(frozen=True, slots=True)
class DonorBoundaryRadialProfile:
    """Radial field summary with explicit donor/interior/outside accounting."""

    time_min: float
    donor_identifier: str
    donor_radius_micron: float
    concentration_unit: str
    quantity_unit: str
    bins: tuple[DonorBoundaryRadialBin, ...]
    analyzed_extracellular_voxel_count: int
    analyzed_extracellular_integrated_quantity: float
    excluded_donor_voxel_count: int
    excluded_donor_integrated_quantity: float
    outside_extent_voxel_count: int
    outside_extent_integrated_quantity: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "time_min", _finite_non_negative(self.time_min, "time_min"))
        if not isinstance(self.donor_identifier, str) or not self.donor_identifier.strip():
            raise ValueError("donor_identifier must be non-blank")
        object.__setattr__(self, "donor_identifier", self.donor_identifier.strip())
        object.__setattr__(
            self,
            "donor_radius_micron",
            _positive(self.donor_radius_micron, "donor_radius_micron"),
        )

        for field_name in ("concentration_unit", "quantity_unit"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be non-blank")
            object.__setattr__(self, field_name, value.strip())

        if not isinstance(self.bins, tuple) or not self.bins:
            raise ValueError("bins must be a non-empty tuple")
        if not all(isinstance(item, DonorBoundaryRadialBin) for item in self.bins):
            raise TypeError("bins must contain DonorBoundaryRadialBin objects")

        for field_name in (
            "analyzed_extracellular_voxel_count",
            "excluded_donor_voxel_count",
            "outside_extent_voxel_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer")
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")

        for field_name in (
            "analyzed_extracellular_integrated_quantity",
            "excluded_donor_integrated_quantity",
            "outside_extent_integrated_quantity",
        ):
            object.__setattr__(
                self,
                field_name,
                _finite_non_negative(getattr(self, field_name), field_name),
            )

        if not math.isclose(
            self.bins[0].lower_bound_micron,
            0.0,
            rel_tol=0.0,
            abs_tol=_DISTANCE_TOLERANCE,
        ):
            raise ValueError("radial profile bins must start at zero")
        for previous, current in zip(self.bins, self.bins[1:]):
            if not math.isclose(
                previous.upper_bound_micron,
                current.lower_bound_micron,
                rel_tol=0.0,
                abs_tol=_DISTANCE_TOLERANCE,
            ):
                raise ValueError("radial profile bins must be contiguous")
        if any(
            item.concentration_unit != self.concentration_unit
            or item.quantity_unit != self.quantity_unit
            for item in self.bins
        ):
            raise ValueError("radial profile bin units must match profile units")
        if sum(item.voxel_count for item in self.bins) != (
            self.analyzed_extracellular_voxel_count
        ):
            raise ValueError("radial profile bin counts must match analyzed voxel count")
        if not math.isclose(
            sum(item.integrated_field_quantity for item in self.bins),
            self.analyzed_extracellular_integrated_quantity,
            rel_tol=1e-12,
            abs_tol=1e-8,
        ):
            raise ValueError(
                "radial profile bin quantities must match analyzed field quantity"
            )


def _matching_index(times: tuple[float, ...], requested: float, label: str) -> int:
    matches = [
        index
        for index, value in enumerate(times)
        if math.isclose(value, requested, rel_tol=0.0, abs_tol=_DISTANCE_TOLERANCE)
    ]
    if len(matches) != 1:
        raise ValueError(f"requested analysis time is not a unique {label}")
    return matches[0]


def analyze_donor_boundary_profile(
    experiment: TransportExperiment,
    result: BioFVMRunResult,
    *,
    time_min: float,
    edges_micron: tuple[float, ...],
) -> DonorBoundaryRadialProfile:
    """Summarize a normalized 2D field by distance from a circular donor boundary."""

    if not isinstance(experiment, TransportExperiment):
        raise TypeError("experiment must be a TransportExperiment")
    if not isinstance(result, BioFVMRunResult):
        raise TypeError("result must be a BioFVMRunResult")
    if result.experiment_id != experiment.experiment_id:
        raise ValueError("result experiment_id does not match experiment")
    if len(experiment.release_sources) != 1:
        raise ValueError("donor-boundary analysis requires exactly one release source")

    source = experiment.release_sources[0]
    if not isinstance(source, CircularReleaseSource):
        raise ValueError(
            "donor-boundary analysis requires a finite CircularReleaseSource"
        )

    edges = _validated_edges(edges_micron)
    requested_time = _finite_non_negative(time_min, "time_min")

    grid = result.grid
    width = grid.nx * grid.grid_spacing_micron
    height = grid.ny * grid.grid_spacing_micron
    if not math.isclose(
        width,
        experiment.domain.width_micron,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("result grid width does not match experiment domain")
    if not math.isclose(
        height,
        experiment.domain.height_micron,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("result grid height does not match experiment domain")
    if not math.isclose(
        grid.slice_thickness_micron,
        experiment.domain.slice_thickness_micron,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("result slice thickness does not match experiment domain")

    sample_index = _matching_index(
        tuple(sample.time_min for sample in result.samples),
        requested_time,
        "transport sample",
    )
    field_index = _matching_index(
        tuple(snapshot.time_min for snapshot in result.field_snapshots),
        requested_time,
        "field snapshot",
    )
    sample = result.samples[sample_index]
    snapshot = result.field_snapshots[field_index]

    if len(snapshot.values) != grid.voxel_count:
        raise ValueError("field snapshot length does not match normalized grid")

    voxel_volume = (
        grid.grid_spacing_micron
        * grid.grid_spacing_micron
        * grid.slice_thickness_micron
    )
    integrated_from_field = sum(snapshot.values) * voxel_volume
    if not math.isclose(
        integrated_from_field,
        sample.integrated_field_quantity,
        rel_tol=1e-10,
        abs_tol=1e-8,
    ):
        raise ValueError(
            "normalized field does not reproduce the transport sample integrated quantity"
        )

    grouped_values: list[list[float]] = [[] for _ in range(len(edges) - 1)]
    grouped_quantities = [0.0 for _ in range(len(edges) - 1)]
    donor_count = 0
    donor_quantity = 0.0
    outside_count = 0
    outside_quantity = 0.0

    for index, concentration in enumerate(snapshot.values):
        y_index, x_index = divmod(index, grid.nx)
        x = (x_index + 0.5) * grid.grid_spacing_micron
        y = (y_index + 0.5) * grid.grid_spacing_micron
        distance = distance_from_circular_donor_boundary(
            source,
            x_micron=x,
            y_micron=y,
        )
        quantity = concentration * voxel_volume

        if distance <= _DISTANCE_TOLERANCE:
            donor_count += 1
            donor_quantity += quantity
            continue

        matched = None
        for bin_index, (lower, upper) in enumerate(zip(edges, edges[1:])):
            if lower <= distance < upper:
                matched = bin_index
                break

        if matched is None:
            outside_count += 1
            outside_quantity += quantity
            continue

        grouped_values[matched].append(concentration)
        grouped_quantities[matched] += quantity

    bins: list[DonorBoundaryRadialBin] = []
    for lower, upper, values, quantity in zip(
        edges,
        edges[1:],
        grouped_values,
        grouped_quantities,
    ):
        bins.append(
            DonorBoundaryRadialBin(
                lower_bound_micron=lower,
                upper_bound_micron=upper,
                interval_semantics="[lower, upper)",
                voxel_count=len(values),
                mean_concentration=sum(values) / len(values) if values else 0.0,
                integrated_field_quantity=quantity,
                concentration_unit=result.concentration_unit,
                quantity_unit=result.integrated_quantity_unit,
            )
        )

    analyzed_count = sum(item.voxel_count for item in bins)
    analyzed_quantity = sum(item.integrated_field_quantity for item in bins)
    accounted_quantity = analyzed_quantity + donor_quantity + outside_quantity
    if not math.isclose(
        accounted_quantity,
        sample.integrated_field_quantity,
        rel_tol=1e-10,
        abs_tol=1e-8,
    ):
        raise RuntimeError("donor-boundary analysis does not conserve normalized field quantity")
    if analyzed_count + donor_count + outside_count != grid.voxel_count:
        raise RuntimeError("donor-boundary analysis does not account for every voxel")

    return DonorBoundaryRadialProfile(
        time_min=sample.time_min,
        donor_identifier=source.identifier,
        donor_radius_micron=source.footprint_radius_micron,
        concentration_unit=result.concentration_unit,
        quantity_unit=result.integrated_quantity_unit,
        bins=tuple(bins),
        analyzed_extracellular_voxel_count=analyzed_count,
        analyzed_extracellular_integrated_quantity=analyzed_quantity,
        excluded_donor_voxel_count=donor_count,
        excluded_donor_integrated_quantity=donor_quantity,
        outside_extent_voxel_count=outside_count,
        outside_extent_integrated_quantity=outside_quantity,
    )
