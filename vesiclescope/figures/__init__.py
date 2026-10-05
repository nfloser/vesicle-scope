"""Reproducible scientific figures derived from normalized results."""

from .diffusion_uptake import (
    DiffusionUptakeFigureData,
    prepare_diffusion_uptake_figure_data,
    render_diffusion_uptake_figure,
)
from .donor_boundary import (
    DonorBoundaryFigureData,
    prepare_donor_boundary_figure_data,
    render_donor_boundary_figure,
)
from .population import (
    RecipientCountFigureData,
    prepare_recipient_count_figure_data,
    render_recipient_count_figure,
)

__all__ = [
    "DiffusionUptakeFigureData",
    "prepare_diffusion_uptake_figure_data",
    "render_diffusion_uptake_figure",
    "DonorBoundaryFigureData",
    "prepare_donor_boundary_figure_data",
    "render_donor_boundary_figure",
    "RecipientCountFigureData",
    "prepare_recipient_count_figure_data",
    "render_recipient_count_figure",
]
