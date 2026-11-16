"""Ordering and conservative comparison checks for Level 2 observations."""

from __future__ import annotations

import math


def chronological(frames):
    return sorted(frames, key=lambda frame: frame.mjd_obs if math.isfinite(frame.mjd_obs) else math.inf)


def comparison_warning(first, second) -> str | None:
    """Return a reason to avoid scientific differencing, if metadata disagrees."""
    unknown_metadata = {"", "unknown", "not in header", "none"}
    for field in ("detector", "bunit", "release", "processing_version"):
        if any(str(getattr(frame, field, "")).strip().lower() in unknown_metadata
               for frame in (first, second)):
            return f"{field} metadata is incomplete; compatibility cannot be established"
    if not all(math.isfinite(frame.mjd_obs) for frame in (first, second)):
        return "observation time is missing or invalid"
    if first.mjd_obs == second.mjd_obs:
        return "observations have the same timestamp; this is not a temporal comparison"
    if first.image.shape != second.image.shape:
        return f"cutout dimensions differ ({first.image.shape} vs {second.image.shape})"
    if first.detector != second.detector:
        return f"detectors differ ({first.detector or 'unknown'} vs {second.detector or 'unknown'})"
    if first.bunit != second.bunit:
        return f"FITS units differ ({first.bunit} vs {second.bunit})"
    if first.release != second.release:
        return f"data releases differ ({first.release} vs {second.release})"
    if first.processing_version != second.processing_version:
        return (
            "processing versions differ "
            f"({first.processing_version} vs {second.processing_version})"
        )
    unknown = {"", "unknown", "not in header", "WCS-WAVE table present (inspect per pixel)", "header wavelength range present"}
    if first.wavelength in unknown or second.wavelength in unknown:
        return "wavelength metadata is incomplete; inspect WCS-WAVE/bandpass before comparison"
    if first.wavelength != second.wavelength:
        return f"wavelength metadata differs ({first.wavelength} vs {second.wavelength})"
    first_scale = (
        getattr(first, "pixel_scale_x_arcsec", None),
        getattr(first, "pixel_scale_y_arcsec", None),
    )
    second_scale = (
        getattr(second, "pixel_scale_x_arcsec", None),
        getattr(second, "pixel_scale_y_arcsec", None),
    )
    for left, right in zip(first_scale, second_scale):
        if left is not None and right is not None and not math.isclose(
            left, right, rel_tol=1e-4, abs_tol=1e-6
        ):
            return f"pixel scales differ ({first_scale} vs {second_scale} arcsec/pixel)"
    return None
