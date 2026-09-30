"""Reusable synthetic recipient-count benchmark scenarios."""

from __future__ import annotations

from vesiclescope.domain import (
    BoundaryCondition,
    CircularUptakeSink,
    EvidenceCategory,
    PointReleaseSource,
    PointUptakeSink,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)


RECIPIENT_RING_POSITIONS = (
    (65.0, 75.0),
    (145.0, 135.0),
    (65.0, 135.0),
    (145.0, 75.0),
    (75.0, 65.0),
    (135.0, 145.0),
    (75.0, 145.0),
    (135.0, 65.0),
)


def _synthetic_parameter(
    identifier: str,
    value: float,
    unit: str,
) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic verification input; not a biological default.",),
    )


def _require_reviewed_count(recipient_count: int) -> None:
    if recipient_count not in (2, 4, 8):
        raise ValueError("synthetic count sweep supports 2, 4 or 8 recipients")


def _count_sweep_experiment(
    *,
    experiment_id: str,
    uptake_sinks: tuple[PointUptakeSink | CircularUptakeSink, ...],
) -> TransportExperiment:
    return TransportExperiment(
        experiment_id=experiment_id,
        domain=RectangularDomain2D(
            width_micron=210.0,
            height_micron=210.0,
            slice_thickness_micron=25.0,
        ),
        duration_min=20.0,
        sample_every_min=5.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=_synthetic_parameter(
            "transport.diffusion",
            100.0,
            "micron^2/min",
        ),
        decay=_synthetic_parameter("transport.decay", 0.0, "1/min"),
        initial_concentration=_synthetic_parameter(
            "initial.concentration",
            0.0,
            "particle_equivalent/micron^3",
        ),
        release_sources=(
            PointReleaseSource(
                identifier="source.center",
                x_micron=105.0,
                y_micron=105.0,
                release_rate=_synthetic_parameter(
                    "source.release",
                    120.0,
                    "particle_equivalent/min",
                ),
            ),
        ),
        uptake_sinks=uptake_sinks,
    )


def recipient_count_sweep_experiment(recipient_count: int) -> TransportExperiment:
    """Build the historical reviewed point-recipient count scenario."""

    _require_reviewed_count(recipient_count)
    recipients = tuple(
        PointUptakeSink(
            identifier=f"sink.{index + 1}",
            x_micron=x_micron,
            y_micron=y_micron,
            effective_volume_micron3=1000.0,
            uptake_rate=_synthetic_parameter(
                f"sink.{index + 1}.uptake",
                0.5,
                "1/min",
            ),
        )
        for index, (x_micron, y_micron) in enumerate(
            RECIPIENT_RING_POSITIONS[:recipient_count]
        )
    )
    return _count_sweep_experiment(
        experiment_id=f"synthetic.recipient-count.{recipient_count}",
        uptake_sinks=recipients,
    )


def finite_recipient_count_sweep_experiment(
    recipient_count: int,
) -> TransportExperiment:
    """Build the reviewed finite-footprint recipient-count scenario."""

    _require_reviewed_count(recipient_count)
    recipients = tuple(
        CircularUptakeSink(
            identifier=f"sink.{index + 1}",
            x_micron=x_micron,
            y_micron=y_micron,
            footprint_radius_micron=15.0,
            effective_volume_micron3=1000.0,
            uptake_rate=_synthetic_parameter(
                f"sink.{index + 1}.uptake",
                0.5,
                "1/min",
            ),
        )
        for index, (x_micron, y_micron) in enumerate(
            RECIPIENT_RING_POSITIONS[:recipient_count]
        )
    )
    return _count_sweep_experiment(
        experiment_id=f"synthetic.finite-recipient-count.{recipient_count}",
        uptake_sinks=recipients,
    )
