"""Coordinate and pixel helpers with explicit NumPy/Astropy scalar handling."""

from __future__ import annotations

from typing import Any

import numpy as np
import astropy.units as u
from astropy.wcs.utils import proj_plane_pixel_scales


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
    """Return whether a pixel coordinate lies inside the image footprint."""
    x_value = one_float(x, "pixel X")
    y_value = one_float(y, "pixel Y")
    return -0.5 <= x_value < width - 0.5 and -0.5 <= y_value < height - 0.5


def pixel_scale_arcsec(wcs: Any) -> tuple[float, float]:
    """Return absolute celestial pixel scales in arcseconds per pixel."""
    scales = proj_plane_pixel_scales(wcs)
    units = wcs.wcs.cunit
    converted = []
    for index, value in enumerate(scales[:2]):
        unit = units[index] or u.deg
        scale = abs(float((value * u.Unit(unit)).to_value(u.arcsec)))
        if not np.isfinite(scale) or scale == 0:
            raise ValueError(f"WCS pixel scale {index + 1} is not finite and positive")
        converted.append(scale)
    if len(converted) != 2:
        raise ValueError("celestial WCS must have two pixel scales")
    return converted[0], converted[1]
