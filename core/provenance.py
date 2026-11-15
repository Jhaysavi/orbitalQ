"""Human-readable provenance and discovery-report helpers."""

from __future__ import annotations

import math
import numpy as np


def _cell(value) -> str:
    return str(value).replace("|", r"\|").replace("\n", " ")


def _quality_summary(frame) -> tuple[int, int, float | None]:
    image = np.asarray(frame.image)
    finite_pixels = int(np.isfinite(image).sum())
    flagged_pixels = 0
    if frame.flags is not None:
        flags = np.asarray(frame.flags)
        flagged_pixels = int(np.count_nonzero(np.isfinite(flags) & (flags != 0)))
    median_variance = None
    if frame.variance is not None:
        variance = np.asarray(frame.variance)
        finite_variance = variance[np.isfinite(variance)]
        if finite_variance.size:
            median_variance = float(np.median(finite_variance))
    return finite_pixels, flagged_pixels, median_variance


def report_text(
    target_name: str,
    ra: float,
    dec: float,
    frames,
    selected_index: int | None = None,
    comparison_index: int | None = None,
    comparison_warning: str | None = None,
) -> str:
    lines = [
        "# orbitalQ Discovery Report",
        "",
        f"Target: {_cell(target_name)}",
        f"Target coordinates (ICRS input): RA {ra:.7f} deg, Dec {dec:.7f} deg",
        "",
        "This is an exploratory archive-inspection report, not a discovery claim.",
        "Coordinates are not silently propagated; high-proper-motion targets need an astrometric reference epoch.",
        "",
        "## Observations",
        "",
        "| DATE-OBS | MJD-OBS | OBSID | Detector | Wavelength | Release | Release source | Processing | Units | Reference epoch | Pixel scale (arcsec/pixel) | Cutout FOV (arcsec) | Filename | Source | Finite pixels | Nonzero FLAGS | Median VARIANCE |",
        "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---:|---:|---:|",
    ]
    for frame in frames:
        finite_pixels, flagged_pixels, median_variance = _quality_summary(frame)
        variance_text = (
            f"{median_variance:.8g}" if median_variance is not None else "unavailable"
        )
        scale_x = getattr(frame, "pixel_scale_x_arcsec", float("nan"))
        scale_y = getattr(frame, "pixel_scale_y_arcsec", float("nan"))
        scale_text = f"{scale_x:.8g} × {scale_y:.8g}" if math.isfinite(scale_x) and math.isfinite(scale_y) else "unavailable"
        image = np.asarray(frame.image)
        fov_text = (
            f"{image.shape[1] * scale_x:.8g} × {image.shape[0] * scale_y:.8g}"
            if math.isfinite(scale_x) and math.isfinite(scale_y)
            else "unavailable"
        )
        lines.append(
            f"| {_cell(frame.date_obs or 'not in header')} | "
            f"{_cell(frame.mjd_obs if math.isfinite(frame.mjd_obs) else 'not in header')} | "
            f"{_cell(frame.obsid or 'not in header')} | {_cell(frame.detector or 'unknown')} | "
            f"{_cell(frame.wavelength)} | {_cell(frame.release)} | "
            f"{_cell(frame.release_source)} | {_cell(frame.processing_version)} | "
            f"{_cell(frame.bunit)} | "
            f"{_cell(frame.reference_epoch)} | {_cell(scale_text)} | {_cell(fov_text)} | "
            f"{_cell(frame.filename)} | {_cell(frame.source_url or 'uploaded file')} | "
            f"{finite_pixels}/{np.asarray(frame.image).size} | {flagged_pixels} | {variance_text} |"
        )
    lines += ["", "## Comparison", ""]
    if selected_index is None or comparison_index is None:
        lines.append("No frame pair was selected for comparison.")
    elif not (0 <= selected_index < len(frames) and 0 <= comparison_index < len(frames)):
        lines.append("Comparison details are unavailable because the selected frame index is invalid.")
    else:
        selected = frames[selected_index]
        compared = frames[comparison_index]
        lines.append(
            f"Selected: {_cell(selected.filename)} ({_cell(selected.date_obs or 'date unavailable')}, "
            f"OBSID {_cell(selected.obsid or 'not in header')})."
        )
        lines.append(
            f"Compared with: {_cell(compared.filename)} ({_cell(compared.date_obs or 'date unavailable')}, "
            f"OBSID {_cell(compared.obsid or 'not in header')})."
        )
        lines.append(
            "Compatibility: "
            + (
                f"not comparable — {_cell(comparison_warning)}."
                if comparison_warning
                else "metadata compatible for visual inspection; WCS registration, quality masking, uncertainty, PSF and background matching are still required."
            )
        )
    lines += [
        "",
        "## Data quality and provenance",
        "",
        "Finite IMAGE pixels, nonzero FLAGS pixels and finite VARIANCE summaries are reported per observation. "
        "FLAGS are not automatically treated as a bad-pixel mask.",
        "",
        "Each source is the original public archive URL or an upload label. "
        "Release metadata comes from the FITS header when available, otherwise from a recognized DR1/QR3 archive URL path. "
        "A local file is not presented as an archive observation unless its header provenance says so.",
        "",
        "## Limitations",
        "",
        "Before interpreting image differences, verify WCS registration, FLAGS, VARIANCE, PSF/ePSF, background/calibration, and wavelength compatibility.",
    ]
    return "\n".join(lines)
