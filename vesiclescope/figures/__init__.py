"""Reproducible scientific figures derived from normalized results."""

from .population import (
    RecipientCountFigureData,
    prepare_recipient_count_figure_data,
    render_recipient_count_figure,
)

__all__ = [
    "RecipientCountFigureData",
    "prepare_recipient_count_figure_data",
    "render_recipient_count_figure",
]
