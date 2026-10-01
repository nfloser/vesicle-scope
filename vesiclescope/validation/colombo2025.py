"""Reviewed external validation target from Colombo et al. (2025).

The objects in this module describe what the publication measured and what
public material is available. They are validation metadata, not model
parameters and not a fitting objective.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from vesiclescope.domain import EvidenceSource, ParameterContext


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


def _positive_finite(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0.0:
        raise ValueError(f"{field_name} must be finite and greater than zero")
    return numeric


def _positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return value


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    return tuple(_required_text(value, field_name) for value in values)


class RawDataAvailability(str, Enum):
    """Availability state of the primary measurements behind a validation target."""

    PUBLIC = "public"
    ON_REQUEST = "on_request"
    RESTRICTED = "restricted"


@dataclass(frozen=True, slots=True)
class ExternalAnalysisPipeline:
    """Pinned public analysis code associated with an external experiment."""

    repository: str
    commit: str
    path: str
    file_sha: str
    license: str

    def __post_init__(self) -> None:
        for field_name in ("repository", "commit", "path", "file_sha", "license"):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )


@dataclass(frozen=True, slots=True)
class FitDerivedRetentionLandmark:
    """A published cumulative radial summary obtained from a fitted curve."""

    distance_micron: float
    cumulative_fraction: float
    is_fit_derived: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "distance_micron",
            _positive_finite(self.distance_micron, "distance_micron"),
        )
        if isinstance(self.cumulative_fraction, bool) or not isinstance(
            self.cumulative_fraction,
            (int, float),
        ):
            raise TypeError("cumulative_fraction must be a real number")
        fraction = float(self.cumulative_fraction)
        if not math.isfinite(fraction) or not 0.0 < fraction <= 1.0:
            raise ValueError(
                "cumulative_fraction must be finite and in the interval (0, 1]"
            )
        object.__setattr__(self, "cumulative_fraction", fraction)
        if self.is_fit_derived is not True:
            raise ValueError(
                "Colombo retention landmarks are recorded only as fit-derived summaries"
            )


@dataclass(frozen=True, slots=True)
class Colombo2025TumourDistanceTarget:
    """Machine-readable boundary for the first proposed biological validation."""

    identifier: str
    source: EvidenceSource
    pmid: str
    context: ParameterContext
    observable: str
    distance_reference: str
    pixel_size_micron: float
    published_zone_pixels: int
    published_zone_width_micron: float
    public_code_bin_pixels: int
    public_code_bin_width_micron: float
    pipeline: ExternalAnalysisPipeline
    raw_data_availability: RawDataAvailability
    fit_derived_retention_landmarks: tuple[FitDerivedRetentionLandmark, ...]
    additional_fit_summary: str
    comparison_blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identifier",
            _required_text(self.identifier, "identifier"),
        )
        if not isinstance(self.source, EvidenceSource):
            raise TypeError("source must be an EvidenceSource")
        object.__setattr__(self, "pmid", _required_text(self.pmid, "pmid"))
        if not isinstance(self.context, ParameterContext):
            raise TypeError("context must be a ParameterContext")
        object.__setattr__(
            self,
            "observable",
            _required_text(self.observable, "observable"),
        )
        object.__setattr__(
            self,
            "distance_reference",
            _required_text(self.distance_reference, "distance_reference"),
        )

        pixel_size = _positive_finite(self.pixel_size_micron, "pixel_size_micron")
        published_pixels = _positive_int(
            self.published_zone_pixels,
            "published_zone_pixels",
        )
        published_width = _positive_finite(
            self.published_zone_width_micron,
            "published_zone_width_micron",
        )
        code_pixels = _positive_int(
            self.public_code_bin_pixels,
            "public_code_bin_pixels",
        )
        code_width = _positive_finite(
            self.public_code_bin_width_micron,
            "public_code_bin_width_micron",
        )

        object.__setattr__(self, "pixel_size_micron", pixel_size)
        object.__setattr__(self, "published_zone_pixels", published_pixels)
        object.__setattr__(self, "published_zone_width_micron", published_width)
        object.__setattr__(self, "public_code_bin_pixels", code_pixels)
        object.__setattr__(self, "public_code_bin_width_micron", code_width)

        if not math.isclose(
            published_pixels * pixel_size,
            published_width,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "published zone width must match the recorded pixel scale"
            )
        if not math.isclose(
            code_pixels * pixel_size,
            code_width,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "public-code bin width must match the recorded pixel scale"
            )
        if math.isclose(
            published_width,
            code_width,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "the reviewed paper/code binning discrepancy must remain explicit"
            )

        if not isinstance(self.pipeline, ExternalAnalysisPipeline):
            raise TypeError("pipeline must be an ExternalAnalysisPipeline")
        if not isinstance(self.raw_data_availability, RawDataAvailability):
            raise TypeError(
                "raw_data_availability must be a RawDataAvailability value"
            )

        if not isinstance(self.fit_derived_retention_landmarks, tuple):
            raise TypeError("fit_derived_retention_landmarks must be a tuple")
        if not self.fit_derived_retention_landmarks:
            raise ValueError(
                "fit_derived_retention_landmarks must not be empty"
            )
        if not all(
            isinstance(item, FitDerivedRetentionLandmark)
            for item in self.fit_derived_retention_landmarks
        ):
            raise TypeError(
                "fit_derived_retention_landmarks must contain only "
                "FitDerivedRetentionLandmark objects"
            )

        previous_distance = -math.inf
        previous_fraction = -math.inf
        for landmark in self.fit_derived_retention_landmarks:
            if landmark.distance_micron <= previous_distance:
                raise ValueError(
                    "fit-derived landmark distances must be strictly increasing"
                )
            if landmark.cumulative_fraction <= previous_fraction:
                raise ValueError(
                    "fit-derived cumulative fractions must be strictly increasing"
                )
            previous_distance = landmark.distance_micron
            previous_fraction = landmark.cumulative_fraction

        object.__setattr__(
            self,
            "additional_fit_summary",
            _required_text(
                self.additional_fit_summary,
                "additional_fit_summary",
            ),
        )
        blockers = _text_tuple(self.comparison_blockers, "comparison_blockers")
        if not blockers:
            raise ValueError("comparison_blockers must not be empty")
        object.__setattr__(self, "comparison_blockers", blockers)

    @property
    def quantitatively_ready(self) -> bool:
        """Whether this target can currently support a defensible direct fit."""

        return len(self.comparison_blockers) == 0


def colombo_2025_tumour_distance_target() -> Colombo2025TumourDistanceTarget:
    """Return the reviewed tumour-distance validation target.

    The values here describe the publication and its public analysis pipeline.
    They must not be interpreted as VesicleScope transport, release, or uptake
    parameter defaults.
    """

    return Colombo2025TumourDistanceTarget(
        identifier="colombo2025.heLa-tumour.distance-signal",
        source=EvidenceSource(
            identifier="doi:10.1002/jev2.70169",
            location="Methods 2.8; Figure 5m; Supplementary Figure S6",
        ),
        pmid="41167986",
        context=ParameterContext(
            species="human HeLa cells / athymic nude mouse host",
            tissue="subcutaneous tumour xenograft",
            cell_line="HeLa CD9-Halo donor; HeLa Staygold recipient",
            ev_preparation="CD9-Halo-labelled EV-associated signal",
            measurement_method=(
                "confocal microscopy with donor-mask distance segmentation"
            ),
            experimental_conditions=(
                "donor:recipient 1:100 or 1:200; Bafilomycin-A1; "
                "JF635 HaloTag ligand"
            ),
        ),
        observable=(
            "frequency/distribution of thresholded CD9-Halo EV-associated "
            "signal versus distance from donor cells"
        ),
        distance_reference="nearest donor-cell boundary",
        pixel_size_micron=0.2,
        published_zone_pixels=50,
        published_zone_width_micron=10.0,
        public_code_bin_pixels=25,
        public_code_bin_width_micron=5.0,
        pipeline=ExternalAnalysisPipeline(
            repository="CocucciLab/spatial-limits-of-extracellular-vesicles",
            commit="ed9e28173929c9f896d16658781d7a4b9cc2297c",
            path="in vivo/distTraAnalysis.py",
            file_sha="16744cd7d0eb0271ce5a8c3949b84e7cb86d8933",
            license="MIT",
        ),
        raw_data_availability=RawDataAvailability.ON_REQUEST,
        fit_derived_retention_landmarks=(
            FitDerivedRetentionLandmark(
                distance_micron=17.0,
                cumulative_fraction=0.50,
            ),
            FitDerivedRetentionLandmark(
                distance_micron=40.0,
                cumulative_fraction=0.80,
            ),
        ),
        additional_fit_summary="less than 5% beyond 100 micron",
        comparison_blockers=(
            "Raw tumour TIFF/source measurements are not publicly available; "
            "the paper states that data are available from the corresponding "
            "author upon reasonable request.",
            "VesicleScope can reproduce finite circular donor-boundary geometry, "
            "but the current donor radius is synthetic and normalized model "
            "concentration is not yet a validated measurement model for "
            "thresholded CD9-Halo fluorescence.",
            "Published approximately 10 micron segmentation zones and the "
            "current public analysis code's 5 micron histogram bins differ.",
            "Current VesicleScope release, diffusion, and uptake parameters are "
            "synthetic and are not calibrated to this HeLa tumour system.",
        ),
    )
