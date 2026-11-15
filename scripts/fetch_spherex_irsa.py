#!/usr/bin/env python3
"""
orbitalQ — SPHEREx DR1/QR3 Level 2 Cutout & Provenance Fetcher (NASA/IPAC IRSA)
===============================================================================
Queries the official NASA/IPAC IRSA TAP service (`spherex.artifact` & `spherex.plane`)
for Level 2 Spectral Image Multi-Extension FITS (MEF) cutouts around a target or
ICRS coordinate, extracts IMAGE, FLAGS, VARIANCE, ZODI, and WCS-WAVE metadata,
applies optional Zodiacal-light subtraction, computes SNR & quality bitmasks, and
exports normalized JSON + PNG previews for the orbitalQ web viewer.

Data source: NASA/IPAC Infrared Science Archive (IRSA), Caltech (USA).
Reference: https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/
"""

from __future__ import annotations

import argparse
import concurrent.futures
import http.client
import json
import logging
import urllib.error
from pathlib import Path
from typing import Any

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.utils.data import conf
from astropy.wcs import WCS
from astroquery.ipac.irsa import Irsa

# Increase remote timeout for SPHEREx MEF cutouts
conf.remote_timeout = 120
logging.getLogger("astropy").setLevel(logging.ERROR)

# Official NASA Space Apps 2026 Planet X & SPHEREx test targets
PRESET_TARGETS: dict[str, dict[str, Any]] = {
    "WISE 0855-0714": {"ra": 133.795129, "dec": -7.245147, "type": "Brown Dwarf (High PM)"},
    "Barnard's Star": {"ra": 269.452075, "dec": 4.693391, "type": "Red Dwarf (Highest PM)"},
    "Epsilon Indi B": {"ra": 331.076250, "dec": -56.782500, "type": "Binary Brown Dwarf"},
    "RW Aurigae": {"ra": 76.956500, "dec": 30.401417, "type": "Variable Star (T Tauri)"},
    "R Draconis": {"ra": 248.165000, "dec": 66.755556, "type": "Mira Variable Star"},
}

# Key SPHEREx Level 2 FLAGS bitmask definitions (from IRSA Explanatory Supplement)
CRITICAL_FLAG_BITS: dict[int, str] = {
    0: "TRANSIENT",
    1: "OVERFLOW",
    2: "SUR_ERROR",
    6: "NONFUNC",
    9: "MISSING_DATA",
    10: "HOT",
    11: "COLD",
    15: "NONLINEAR",
    17: "PERSIST",
    19: "OUTLIER",
    22: "GHOST",
    25: "STREAK",
    26: "BLOOM",
    27: "SNOWBALL",
    28: "HALO",
}


def query_spherex_tap(
    coord: SkyCoord,
    size_deg: float = 0.1,
    bandpass: str | None = None,
) -> list[dict[str, Any]]:
    """Query IRSA TAP for SPHEREx DR1/QR3 Level 2 cutouts overlapping `coord`."""
    band_filter = f"AND p.energy_bandpassname = '{bandpass}'" if bandpass else ""
    query = f"""
    SELECT
        'https://irsa.ipac.caltech.edu/' || a.uri || '?center={coord.ra.deg},{coord.dec.deg}d&size={size_deg}' AS uri,
        p.time_bounds_lower,
        p.time_bounds_upper,
        p.energy_bandpassname,
        p.obs_id
    FROM spherex.artifact a
    JOIN spherex.plane p ON a.planeid = p.planeid
    WHERE 1 = CONTAINS(POINT('ICRS', {coord.ra.deg}, {coord.dec.deg}), p.poly)
    {band_filter}
    ORDER BY p.time_bounds_lower ASC
    """
    table = Irsa.query_tap(query).to_table()
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(table, start=1):
        mjd = float(row["time_bounds_lower"])
        iso_date = Time(mjd, format="mjd").iso.split(" ")[0]
        rows.append(
            {
                "index": idx,
                "uri": str(row["uri"]),
                "mjd": mjd,
                "obs_date": iso_date,
                "bandpass": str(row["energy_bandpassname"]),
                "obs_id": str(row["obs_id"]),
            }
        )
    return rows


def decode_flags_summary(flags_arr: np.ndarray) -> dict[str, int]:
    """Count pixels affected by key SPHEREx quality/artifact bitmask flags."""
    summary: dict[str, int] = {}
    for bit, name in CRITICAL_FLAG_BITS.items():
        count = int(np.count_nonzero((flags_arr & (1 << bit)) != 0))
        if count > 0:
            summary[name] = count
    return summary


def process_cutout(
    item: dict[str, Any],
    coord: SkyCoord,
    out_img_dir: Path,
    subtract_zodi: bool = True,
) -> dict[str, Any] | None:
    """Download a single SPHEREx Level 2 MEF cutout and extract science + provenance."""
    try:
        with fits.open(item["uri"], memmap=False, cache=False) as hdul:
            img_hdr = hdul["IMAGE"].header
            img_data = np.array(hdul["IMAGE"].data, dtype=np.float32)
            flags_data = np.array(hdul["FLAGS"].data, dtype=np.int32)
            var_data = np.array(hdul["VARIANCE"].data, dtype=np.float32)
            zodi_data = np.array(hdul["ZODI"].data, dtype=np.float32)

            # Optional Zodiacal-light model subtraction (not pre-subtracted in Level 2)
            sci_data = img_data - zodi_data if subtract_zodi else img_data

            # Spatial WCS -> target pixel position
            spatial_wcs = WCS(img_hdr)
            px, py = spatial_wcs.world_to_pixel(coord)
            cx, cy = int(round(float(px))), int(round(float(py)))

            # Spectral WCS-WAVE -> central wavelength & bandwidth at target pixel
            # SIP optical distortion must be disabled for spectral WCS 'W'
            spectral_wcs = WCS(header=img_hdr, fobj=hdul, key="W")
            spectral_wcs.sip = None
            wl, bw = spectral_wcs.pixel_to_world(px, py)
            wavelength_um = float(wl.to(u.micrometer).value)
            bandwidth_um = float(bw.to(u.micrometer).value)

            # Local aperture photometry estimate (3x3 box around target pixel)
            h, w = sci_data.shape
            x0, x1 = max(0, cx - 1), min(w, cx + 2)
            y0, y1 = max(0, cy - 1), min(h, cy + 2)
            flux_patch = sci_data[y0:y1, x0:x1]
            var_patch = var_data[y0:y1, x0:x1]
            flux_mjy_sr = float(np.nanmean(flux_patch))
            sigma_mjy_sr = float(np.sqrt(np.nanmean(var_patch)))
            snr = float(flux_mjy_sr / sigma_mjy_sr) if sigma_mjy_sr > 0 else 0.0

            # Save quicklook PNG with percentile stretch
            vmin, vmax = np.nanpercentile(sci_data, [5, 99.2])
            png_name = f"cutout_{item['index']:03d}_{item['bandpass']}_{item['obs_date']}.png"
            png_path = out_img_dir / png_name
            fig, ax = plt.subplots(figsize=(4, 4), dpi=140)
            ax.imshow(sci_data, origin="lower", cmap="magma", vmin=vmin, vmax=vmax)
            ax.plot(px, py, marker="+", color="#38bdf8", markersize=12, markeredgewidth=1.5)
            ax.axis("off")
            fig.tight_layout(pad=0)
            fig.savefig(png_path, bbox_inches="tight", pad_inches=0)
            plt.close(fig)

            return {
                "index": item["index"],
                "obs_id": item["obs_id"],
                "obs_date": item["obs_date"],
                "mjd": item["mjd"],
                "bandpass": item["bandpass"],
                "detector": int(img_hdr.get("DETECTOR", 0)),
                "wavelength_um": round(wavelength_um, 4),
                "bandwidth_um": round(bandwidth_um, 4),
                "flux_mjy_sr": round(flux_mjy_sr, 5),
                "uncertainty_mjy_sr": round(sigma_mjy_sr, 5),
                "snr": round(snr, 2),
                "zodi_subtracted": subtract_zodi,
                "processing_version": str(hdul[0].header.get("VERSION", "unknown")),
                "fine_astrometry_flag": int(img_hdr.get("ASTROM_F", 0)),
                "flags_summary": decode_flags_summary(flags_data),
                "image_file": f"images/{png_name}",
                "access_url": item["uri"],
            }
    except (TimeoutError, urllib.error.HTTPError, http.client.IncompleteRead, http.client.RemoteDisconnected, Exception) as exc:
        print(f"[WARN] Skipping cutout {item['index']} ({item['uri']}): {exc}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch SPHEREx DR1/QR3 Level 2 cutouts from NASA/IPAC IRSA.")
    parser.add_argument("--target", type=str, default="WISE 0855-0714", help="Preset target name.")
    parser.add_argument("--ra", type=float, default=None, help="Right Ascension in degrees (ICRS).")
    parser.add_argument("--dec", type=float, default=None, help="Declination in degrees (ICRS).")
    parser.add_argument("--fov", type=float, default=0.0833, help="Cutout size in degrees (default ~5 arcmin).")
    parser.add_argument("--bandpass", type=str, default=None, help="Optional bandpass filter (e.g. SPHEREx-D2).")
    parser.add_argument("--max-cutouts", type=int, default=24, help="Maximum number of epochs/bands to download.")
    parser.add_argument("--no-zodi", action="store_true", help="Disable Zodiacal light model subtraction.")
    parser.add_argument("--out", type=str, default="data/spherex_bundle", help="Output directory.")
    args = parser.parse_args()

    if args.ra is not None and args.dec is not None:
        ra_deg, dec_deg = args.ra, args.dec
        target_label = f"ICRS ({ra_deg:.4f}, {dec_deg:.4f})"
    else:
        preset = PRESET_TARGETS.get(args.target, PRESET_TARGETS["WISE 0855-0714"])
        ra_deg, dec_deg = preset["ra"], preset["dec"]
        target_label = args.target

    coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
    out_dir = Path(args.out)
    out_img_dir = out_dir / "images"
    out_img_dir.mkdir(parents=True, exist_ok=True)

    print(f"Querying NASA/IPAC IRSA TAP for {target_label} (RA={ra_deg:.5f}, Dec={dec_deg:.5f})...")
    candidates = query_spherex_tap(coord, size_deg=args.fov, bandpass=args.bandpass)
    print(f"Found {len(candidates)} overlapping SPHEREx Level 2 exposures.")

    selected = candidates[: args.max_cutouts]
    records: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(process_cutout, item, coord, out_img_dir, not args.no_zodi)
            for item in selected
        ]
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            if res is not None:
                records.append(res)

    records.sort(key=lambda r: (r["mjd"], r["wavelength_um"]))
    bundle = {
        "target": target_label,
        "ra_deg": ra_deg,
        "dec_deg": dec_deg,
        "fov_arcmin": round(args.fov * 60.0, 2),
        "data_source": "NASA/IPAC IRSA SPHEREx Archive (DR1/QR3 Level 2 MEF)",
        "observation_count": len(records),
        "observations": records,
    }

    json_path = out_dir / "observations.json"
    json_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(f"Saved {len(records)} processed observations to {json_path}")


if __name__ == "__main__":
    main()
