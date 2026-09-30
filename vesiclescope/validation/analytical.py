"""Closed-form reference behavior used to verify transport engines."""

from __future__ import annotations

import math


def _non_negative_finite(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    numeric_value = float(value)
    if not math.isfinite(numeric_value) or numeric_value < 0.0:
        raise ValueError(f"{field_name} must be finite and non-negative")
    return numeric_value


def first_order_decay(
    initial_value: float,
    rate_per_min: float,
    time_min: float,
) -> float:
    """Return the exact solution for uniform first-order decay.

    This is a mathematical reference calculation, not a transport solver and
    not a biological model. Inputs must already be expressed in compatible
    units: rate_per_min in 1/min and time_min in min.
    """

    initial = _non_negative_finite(initial_value, "initial_value")
    rate = _non_negative_finite(rate_per_min, "rate_per_min")
    time = _non_negative_finite(time_min, "time_min")
    return initial * math.exp(-rate * time)
