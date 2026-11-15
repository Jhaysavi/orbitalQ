"""Ordering and conservative comparison checks for Level 2 observations."""

from __future__ import annotations

import math


def chronological(frames):
    return sorted(frames, key=lambda frame: frame.mjd_obs if math.isfinite(frame.mjd_obs) else math.inf)


def comparison_warning(first, second) -> str | None:
    """Return a reason to avoid scientific differencing, if metadata disagrees."""
    if first.detector != second.detector:
        return f"detectors differ ({first.detector or 'unknown'} vs {second.detector or 'unknown'})"
    if first.bunit != second.bunit:
        return f"FITS units differ ({first.bunit} vs {second.bunit})"
    unknown = {"", "unknown", "not in header", "WCS-WAVE table present (inspect per pixel)"}
    if first.wavelength in unknown or second.wavelength in unknown:
        return "wavelength metadata is incomplete; inspect WCS-WAVE/bandpass before comparison"
    if first.wavelength != second.wavelength:
        return f"wavelength metadata differs ({first.wavelength} vs {second.wavelength})"
    return None
