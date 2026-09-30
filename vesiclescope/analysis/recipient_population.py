"""Engine-independent recipient-population analysis."""

from __future__ import annotations

from dataclasses import dataclass
import math

from vesiclescope.domain import TransportExperiment
from vesiclescope.engines import BioFVMRunResult


PLANAR_DENSITY_UNIT = "recipient/mm^2"
_DISTANCE_TOLERANCE = 1e-9


def _finite_non_negative(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise ValueError(f"{field_name} must be finite and non-negative")
    return numeric


@dataclass(frozen=True, slots=True)
class RecipientUptakeObservation:
    """One recipient's cumulative uptake and donor distance at a sample time."""

    identifier: str
    x_micron: float
    y_micron: float
    donor_distance_micron: float
    internalized_quantity: float

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, str) or not self.identifier.strip():
            raise ValueError("recipient identifier must be non-blank")
        object.__setattr__(self, "identifier", self.identifier.strip())

        for field_name in (
            "x_micron",
            "y_micron",
            "donor_distance_micron",
            "internalized_quantity",
        ):
            object.__setattr__(
                self,
                field_name,
                _finite_non_negative(getattr(self, field_name), field_name),
            )


@dataclass(frozen=True, slots=True)
class RecipientPopulationSummary:
    """Derived recipient-population observables at one normalized sample time."""

    time_min: float
    recipient_count: int
    planar_density: float
    planar_density_unit: str
    quantity_unit: str
    total_internalized_quantity: float
    mean_internalized_quantity: float
    recipients: tuple[RecipientUptakeObservation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "time_min",
            _finite_non_negative(self.time_min, "time_min"),
        )
        if isinstance(self.recipient_count, bool) or not isinstance(
            self.recipient_count,
            int,
        ):
            raise TypeError("recipient_count must be an integer")
        if self.recipient_count < 0:
            raise ValueError("recipient_count must be non-negative")
        if self.recipient_count != len(self.recipients):
            raise ValueError("recipient_count must match recipients")
        if self.planar_density_unit != PLANAR_DENSITY_UNIT:
            raise ValueError(
                f"planar_density_unit must be {PLANAR_DENSITY_UNIT!r}"
            )
        if not isinstance(self.quantity_unit, str) or not self.quantity_unit.strip():
            raise ValueError("quantity_unit must be non-blank")
        object.__setattr__(
            self,
            "planar_density",
            _finite_non_negative(self.planar_density, "planar_density"),
        )
        object.__setattr__(
            self,
            "total_internalized_quantity",
            _finite_non_negative(
                self.total_internalized_quantity,
                "total_internalized_quantity",
            ),
        )
        object.__setattr__(
            self,
            "mean_internalized_quantity",
            _finite_non_negative(
                self.mean_internalized_quantity,
                "mean_internalized_quantity",
            ),
        )
        if not isinstance(self.recipients, tuple):
            raise TypeError("recipients must be a tuple")


@dataclass(frozen=True, slots=True)
class DistanceBinSummary:
    """Half-open [lower, upper) recipient-uptake distance bin."""

    lower_bound_micron: float
    upper_bound_micron: float
    interval_semantics: str
    recipient_count: int
    total_internalized_quantity: float
    mean_internalized_quantity: float
    quantity_unit: str

    def __post_init__(self) -> None:
        lower = _finite_non_negative(
            self.lower_bound_micron,
            "lower_bound_micron",
        )
        upper = _finite_non_negative(
            self.upper_bound_micron,
            "upper_bound_micron",
        )
        if upper <= lower:
            raise ValueError("distance-bin upper bound must exceed lower bound")
        object.__setattr__(self, "lower_bound_micron", lower)
        object.__setattr__(self, "upper_bound_micron", upper)
        if self.interval_semantics != "[lower, upper)":
            raise ValueError("distance bins must use [lower, upper) semantics")
        if isinstance(self.recipient_count, bool) or not isinstance(
            self.recipient_count,
            int,
        ):
            raise TypeError("recipient_count must be an integer")
        if self.recipient_count < 0:
            raise ValueError("recipient_count must be non-negative")
        object.__setattr__(
            self,
            "total_internalized_quantity",
            _finite_non_negative(
                self.total_internalized_quantity,
                "total_internalized_quantity",
            ),
        )
        object.__setattr__(
            self,
            "mean_internalized_quantity",
            _finite_non_negative(
                self.mean_internalized_quantity,
                "mean_internalized_quantity",
            ),
        )
        if not isinstance(self.quantity_unit, str) or not self.quantity_unit.strip():
            raise ValueError("quantity_unit must be non-blank")


def _sample_index(result: BioFVMRunResult, time_min: float) -> int:
    requested = _finite_non_negative(time_min, "time_min")
    matches = [
        index
        for index, sample in enumerate(result.samples)
        if math.isclose(
            sample.time_min,
            requested,
            rel_tol=0.0,
            abs_tol=_DISTANCE_TOLERANCE,
        )
    ]
    if len(matches) != 1:
        raise ValueError(
            f"requested analysis time {requested:g} min is not a unique result sample"
        )
    return matches[0]


def analyze_recipient_population(
    experiment: TransportExperiment,
    result: BioFVMRunResult,
    *,
    time_min: float,
) -> RecipientPopulationSummary:
    """Derive planar density, donor distance and uptake from normalized results."""

    if not isinstance(experiment, TransportExperiment):
        raise TypeError("experiment must be a TransportExperiment")
    if not isinstance(result, BioFVMRunResult):
        raise TypeError("result must be a BioFVMRunResult")
    if result.experiment_id != experiment.experiment_id:
        raise ValueError("result experiment_id does not match experiment")
    if len(experiment.release_sources) != 1:
        raise ValueError(
            "recipient donor-distance analysis requires exactly one release source"
        )

    expected_ids = tuple(sink.identifier for sink in experiment.uptake_sinks)
    observed_ids = tuple(series.identifier for series in result.recipient_uptake_series)
    if observed_ids != expected_ids:
        raise ValueError(
            "result recipient identifiers do not match experiment uptake sinks"
        )

    sample_index = _sample_index(result, time_min)
    source = experiment.release_sources[0]
    observations: list[RecipientUptakeObservation] = []

    for sink, series in zip(
        experiment.uptake_sinks,
        result.recipient_uptake_series,
    ):
        for observed_value, expected_value, field_name in (
            (series.x_micron, sink.x_micron, "x_micron"),
            (series.y_micron, sink.y_micron, "y_micron"),
            (
                series.effective_volume_micron3,
                sink.effective_volume_micron3,
                "effective_volume_micron3",
            ),
            (
                series.uptake_rate_per_min,
                sink.uptake_rate.value,
                "uptake_rate_per_min",
            ),
        ):
            if not math.isclose(
                observed_value,
                expected_value,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    f"result recipient {sink.identifier!r} {field_name} "
                    "does not match experiment"
                )

        if len(series.samples) != len(result.samples):
            raise ValueError(
                f"recipient {sink.identifier!r} sample count does not match result"
            )
        uptake_sample = series.samples[sample_index]
        if not math.isclose(
            uptake_sample.time_min,
            result.samples[sample_index].time_min,
            rel_tol=0.0,
            abs_tol=_DISTANCE_TOLERANCE,
        ):
            raise ValueError(
                f"recipient {sink.identifier!r} sample time does not match result"
            )

        observations.append(
            RecipientUptakeObservation(
                identifier=sink.identifier,
                x_micron=sink.x_micron,
                y_micron=sink.y_micron,
                donor_distance_micron=math.hypot(
                    sink.x_micron - source.x_micron,
                    sink.y_micron - source.y_micron,
                ),
                internalized_quantity=uptake_sample.internalized_field_quantity,
            )
        )

    total_internalized = sum(
        observation.internalized_quantity for observation in observations
    )
    aggregate = result.samples[sample_index].internalized_field_quantity
    if not math.isclose(
        total_internalized,
        aggregate,
        rel_tol=1e-12,
        abs_tol=1e-8,
    ):
        raise ValueError(
            "analysis recipient total does not match normalized aggregate uptake"
        )

    recipient_count = len(observations)
    area_micron2 = experiment.domain.width_micron * experiment.domain.height_micron
    planar_density = recipient_count * 1_000_000.0 / area_micron2
    mean_internalized = (
        total_internalized / recipient_count if recipient_count else 0.0
    )

    return RecipientPopulationSummary(
        time_min=result.samples[sample_index].time_min,
        recipient_count=recipient_count,
        planar_density=planar_density,
        planar_density_unit=PLANAR_DENSITY_UNIT,
        quantity_unit=result.internalized_quantity_unit,
        total_internalized_quantity=total_internalized,
        mean_internalized_quantity=mean_internalized,
        recipients=tuple(observations),
    )


def bin_recipient_uptake_by_distance(
    recipients: tuple[RecipientUptakeObservation, ...],
    *,
    edges_micron: tuple[float, ...],
    quantity_unit: str,
) -> tuple[DistanceBinSummary, ...]:
    """Aggregate recipients into exhaustive half-open donor-distance bins."""

    if not isinstance(recipients, tuple):
        raise TypeError("recipients must be a tuple")
    if not all(isinstance(item, RecipientUptakeObservation) for item in recipients):
        raise TypeError("recipients must contain RecipientUptakeObservation objects")
    if not isinstance(edges_micron, tuple):
        raise TypeError("edges_micron must be a tuple")
    if len(edges_micron) < 2:
        raise ValueError("at least two distance-bin edges are required")
    if not isinstance(quantity_unit, str) or not quantity_unit.strip():
        raise ValueError("quantity_unit must be non-blank")

    edges = tuple(
        _finite_non_negative(value, "distance-bin edge")
        for value in edges_micron
    )
    if any(right <= left for left, right in zip(edges, edges[1:])):
        raise ValueError("distance-bin edges must be strictly increasing")

    grouped: list[list[RecipientUptakeObservation]] = [
        [] for _ in range(len(edges) - 1)
    ]

    for recipient in recipients:
        matched_index = None
        for index, (lower, upper) in enumerate(zip(edges, edges[1:])):
            if lower <= recipient.donor_distance_micron < upper:
                matched_index = index
                break
        if matched_index is None:
            raise ValueError(
                f"recipient {recipient.identifier!r} at "
                f"{recipient.donor_distance_micron:g} micron falls outside bins"
            )
        grouped[matched_index].append(recipient)

    summaries: list[DistanceBinSummary] = []
    for lower, upper, members in zip(edges, edges[1:], grouped):
        total = sum(member.internalized_quantity for member in members)
        count = len(members)
        summaries.append(
            DistanceBinSummary(
                lower_bound_micron=lower,
                upper_bound_micron=upper,
                interval_semantics="[lower, upper)",
                recipient_count=count,
                total_internalized_quantity=total,
                mean_internalized_quantity=total / count if count else 0.0,
                quantity_unit=quantity_unit.strip(),
            )
        )

    if sum(summary.recipient_count for summary in summaries) != len(recipients):
        raise RuntimeError("distance binning dropped recipient observations")

    return tuple(summaries)
