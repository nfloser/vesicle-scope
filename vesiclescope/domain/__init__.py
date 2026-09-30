"""Core scientific domain contracts."""

from .parameters import (
    EvidenceCategory,
    EvidenceSource,
    ParameterContext,
    ScientificParameter,
)
from .transport import (
    BoundaryCondition,
    DIFFUSION_UNIT,
    RATE_UNIT,
    RectangularDomain2D,
    TransportExperiment,
)

__all__ = [
    "BoundaryCondition",
    "DIFFUSION_UNIT",
    "EvidenceCategory",
    "EvidenceSource",
    "ParameterContext",
    "RATE_UNIT",
    "RectangularDomain2D",
    "ScientificParameter",
    "TransportExperiment",
]
