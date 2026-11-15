"""Human-readable provenance and discovery-report helpers."""

from __future__ import annotations


def report_text(target_name: str, ra: float, dec: float, frames) -> str:
    lines = [
        "# orbitalQ Discovery Report",
        "",
        f"Target: {target_name}",
        f"Target coordinates (ICRS input): RA {ra:.7f} deg, Dec {dec:.7f} deg",
        "",
        "This is an exploratory archive-inspection report, not a discovery claim.",
        "Coordinates are not silently propagated; high-proper-motion targets need an astrometric reference epoch.",
        "",
        "## Observations",
        "",
        "| DATE-OBS | MJD-OBS | OBSID | Detector | Wavelength | Release | Processing | Filename | Source |",
        "|---|---:|---|---|---|---|---|---|---|",
    ]
    for frame in frames:
        lines.append(
            f"| {frame.date_obs or 'not in header'} | {frame.mjd_obs} | {frame.obsid or 'not in header'} | "
            f"{frame.detector or 'unknown'} | {frame.wavelength} | {frame.release} | {frame.processing_version} | "
            f"{frame.filename} | {frame.source_url or 'uploaded file'} |"
        )
    lines += [
        "",
        "## Limitations",
        "",
        "Before interpreting image differences, verify WCS registration, FLAGS, VARIANCE, PSF/ePSF, background/calibration, and wavelength compatibility.",
    ]
    return "\n".join(lines)
