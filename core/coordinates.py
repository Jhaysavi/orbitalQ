"""Coordinate and pixel helpers with explicit NumPy/Astropy scalar handling."""

from __future__ import annotations

from typing import Any

import numpy as np


def one_float(value: Any, name: str) -> float:
    """Return one finite Python float, rejecting ambiguous WCS results."""
    values = np.asarray(value)
    if values.size != 1:
        raise ValueError(f"{name} must contain exactly one coordinate value; got {values.shape}")
    scalar = values.reshape(-1)[0]
    result = float(scalar)
    if not np.isfinite(result):
        raise ValueError(f"{name} is not finite: {result!r}")
    return result


def world_to_pixel_one(wcs: Any, target: Any) -> tuple[float, float]:
    """Project one sky coordinate and return ordinary Python scalars."""
    x, y = wcs.world_to_pixel(target)
    return one_float(x, "WCS pixel X"), one_float(y, "WCS pixel Y")


def cutout_bounds(x: Any, y: Any, width: int, height: int, size: int) -> tuple[int, int, int, int]:
    """Calculate bounded integer cutout limits from one WCS pixel position."""
    x_value = one_float(x, "pixel X")
    y_value = one_float(y, "pixel Y")
    if width <= 0 or height <= 0 or size <= 0:
        raise ValueError("image dimensions and cutout size must be positive")

    half = size // 2
    x0 = max(0, int(round(x_value)) - half)
    y0 = max(0, int(round(y_value)) - half)
    x1 = min(width, x0 + size)
    y1 = min(height, y0 + size)
    x0 = max(0, x1 - size)
    y0 = max(0, y1 - size)
    return x0, x1, y0, y1


def is_inside_image(x: Any, y: Any, width: int, height: int) -> bool:
    """Return whether a zero-based pixel coordinate is inside an image."""
    x_value = one_float(x, "pixel X")
    y_value = one_float(y, "pixel Y")
    return 0 <= x_value < width and 0 <= y_value < height
