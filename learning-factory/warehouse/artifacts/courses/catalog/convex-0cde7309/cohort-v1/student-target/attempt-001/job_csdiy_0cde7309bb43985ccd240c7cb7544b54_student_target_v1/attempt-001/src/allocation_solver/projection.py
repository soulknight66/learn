"""Deterministic Euclidean projection onto a nonnegative budget simplex."""

from __future__ import annotations

import math
from typing import Sequence

from .model import NumericalFailure


def project_simplex(values: Sequence[float], budget: float) -> tuple[float, ...]:
    """Project ``values`` while returning components in their original order."""

    if not values:
        raise ValueError("projection requires at least one component")
    if budget < 0:
        raise ValueError("budget must be nonnegative")
    if not math.isfinite(budget) or not all(math.isfinite(value) for value in values):
        raise NumericalFailure("numerical result is not finite")
    if budget == 0:
        return tuple(0.0 for _ in values)

    ordered = sorted(values, reverse=True)
    prefix = 0.0
    rho = 0
    rho_prefix = 0.0
    try:
        for index, value in enumerate(ordered, start=1):
            prefix += value
            threshold = (prefix - budget) / index
            if not math.isfinite(prefix) or not math.isfinite(threshold):
                raise NumericalFailure("numerical result is not finite")
            if value - threshold > 0:
                rho = index
                rho_prefix = prefix
    except OverflowError:
        raise NumericalFailure("numerical result is not finite") from None

    if rho == 0:
        # With exact arithmetic and a positive finite budget this is impossible.
        raise NumericalFailure("numerical result is not finite")

    theta = (rho_prefix - budget) / rho
    projected = tuple(
        component if component > 0.0 else 0.0
        for component in (value - theta for value in values)
    )
    if not math.isfinite(theta) or not all(math.isfinite(value) for value in projected):
        raise NumericalFailure("numerical result is not finite")
    return projected
