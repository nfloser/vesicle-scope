"""Reusable synthetic finite-donor scenario for boundary-profile figures."""

from vesiclescope.domain import (
    BoundaryCondition,
    CircularReleaseSource,
    EvidenceCategory,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
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


def finite_donor_boundary_figure_experiment() -> TransportExperiment:
    """Build the reviewed finite-donor source-only visualization scenario."""

    return TransportExperiment(
        experiment_id="synthetic.finite-donor-boundary.figure",
        domain=RectangularDomain2D(
            width_micron=240.0,
            height_micron=240.0,
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
        decay=_synthetic_parameter(
            "transport.decay",
            0.0,
            "1/min",
        ),
        initial_concentration=_synthetic_parameter(
            "initial.concentration",
            0.0,
            "particle_equivalent/micron^3",
        ),
        release_sources=(
            CircularReleaseSource(
                identifier="source.finite-donor",
                x_micron=120.0,
                y_micron=120.0,
                footprint_radius_micron=15.0,
                release_rate=_synthetic_parameter(
                    "source.release",
                    120.0,
                    "particle_equivalent/min",
                ),
            ),
        ),
    )
