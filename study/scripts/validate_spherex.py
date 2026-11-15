"""
ORBITAL EYE — Milestone 01
Search the public SPHEREx DR1 + QR3 archive at NASA/IPAC IRSA,
download up to N cutouts for one sky position, and create PNG previews.

Example:
python study/scripts/validate_spherex.py --target "WISE 0855" --ra 133.795129 --dec -7.245147 --bandpass SPHEREx-D2 --max-downloads 3
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import requests
from astropy.io import fits
from astropy.visualization import PercentileInterval, AsinhStretch, ImageNormalize
from astropy.utils.data import conf
from astroquery.ipac.irsa import Irsa


PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data"
CUTOUT_DIR = DATA_DIR / "cutouts"
PREVIEW_DIR = DATA_DIR / "previews"
INVENTORY_DIR = DATA_DIR / "inventory"

# IRSA's current public collections. DR1 and QR3 supersede QR2.
COLLECTIONS_NOTE = "spherex_dr1 + spherex_qr3"
IRSA_ROOT = "https://irsa.ipac.caltech.edu/"


def safe_name(value: str) -> str:
    """Return a filesystem-safe name."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_") or "target"


def build_tap_query(ra: float, dec: float, size_deg: float, bandpass: str) -> str:
    """
    Build the TAP query pattern documented by IRSA's official SPHEREx cutout
    tutorial. `a.uri` is the relative product path; `p` supplies plane metadata.
    """
    allowed_bands = {f"SPHEREx-D{i}" for i in range(1, 7)}
    if bandpass not in allowed_bands:
        raise ValueError(f"Unsupported bandpass {bandpass!r}. Choose one of {sorted(allowed_bands)}")

    # The 'd' suffix on the second coordinate is used in IRSA's documented
    # cutout URL syntax to make the coordinate pair unambiguous.
    return f"""
    SELECT
        '{IRSA_ROOT}' || a.uri ||
        '?center={ra:.9f},{dec:.9f}d&size={size_deg:.6f}' AS cutout_url,
        p.time_bounds_lower AS observation_time,
        p.energy_bandpassname AS bandpass
    FROM spherex.artifact AS a
    JOIN spherex.plane AS p ON a.planeid = p.planeid
    WHERE 1 = CONTAINS(
        POINT('ICRS', {ra:.9f}, {dec:.9f}),
        p.poly
    )
    AND p.energy_bandpassname = '{bandpass}'
    ORDER BY p.time_bounds_lower
    """


def download_file(url: str, destination: Path, timeout=(30, 180)) -> None:
    """Download a FITS cutout with basic retry handling."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error = None

    for attempt in range(3):
        try:
            with requests.get(url, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                temp_path = destination.with_suffix(destination.suffix + ".part")
                with open(temp_path, "wb") as out:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            out.write(chunk)
                temp_path.replace(destination)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))

    raise RuntimeError(f"Could not download {url}: {last_error}")


def inspect_and_preview(fits_path: Path, preview_path: Path) -> dict:
    """Inspect a SPHEREx MEF and render its IMAGE extension as a PNG."""
    summary = {
        "fits_file": str(fits_path.relative_to(PROJECT_DIR)),
        "preview_file": str(preview_path.relative_to(PROJECT_DIR)),
        "extensions": [],
    }

    with fits.open(fits_path, memmap=False) as hdul:
        summary["primary_header_VERSION"] = hdul[0].header.get("VERSION", "not present")

        for hdu in hdul:
            extname = hdu.header.get("EXTNAME", "PRIMARY")
            summary["extensions"].append({
                "name": extname,
                "shape": list(hdu.data.shape) if hdu.data is not None and hasattr(hdu.data, "shape") else None,
            })

        image_hdu = next(
            (hdu for hdu in hdul if hdu.header.get("EXTNAME", "").upper() == "IMAGE"),
            None
        )

        if image_hdu is None or image_hdu.data is None:
            raise ValueError(f"No IMAGE extension found in {fits_path.name}")

        image_data = np.asarray(image_hdu.data, dtype=float)
        finite = np.isfinite(image_data)

        if not finite.any():
            raise ValueError(f"IMAGE extension contains no finite pixels: {fits_path.name}")

        image_header = image_hdu.header
        summary.update({
            "image_shape": list(image_data.shape),
            "BUNIT": image_header.get("BUNIT", "not present"),
            "DETECTOR": image_header.get("DETECTOR", "not present"),
            "OBSID": image_header.get("OBSID", "not present"),
            "DATE": image_header.get("DATE", "not present"),
            "PSF_FWHM": image_header.get("PSF_FWHM", "not present"),
            "finite_pixel_fraction": float(finite.mean()),
        })

        # Display-only stretch; the original scientific FITS values are untouched.
        norm = ImageNormalize(
            image_data[finite],
            interval=PercentileInterval(99.5),
            stretch=AsinhStretch()
        )

        fig, ax = plt.subplots(figsize=(8, 7), constrained_layout=True)
        image = ax.imshow(image_data, origin="lower", cmap="inferno", norm=norm)
        ax.set_title(
            f"SPHEREx {summary['DETECTOR']} | {summary['DATE']}\n"
            f"{summary['OBSID']}"
        )
        ax.set_xlabel("Detector pixel")
        ax.set_ylabel("Detector pixel")
        fig.colorbar(image, ax=ax, label=summary["BUNIT"])
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(preview_path, dpi=150)
        plt.close(fig)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and retrieve real SPHEREx cutouts.")
    parser.add_argument("--target", default="WISE 0855", help="Human-readable target name.")
    parser.add_argument("--ra", type=float, default=133.795129, help="ICRS right ascension in degrees.")
    parser.add_argument("--dec", type=float, default=-7.245147, help="ICRS declination in degrees.")
    parser.add_argument("--bandpass", default="SPHEREx-D2", help="One of SPHEREx-D1 ... SPHEREx-D6.")
    parser.add_argument("--size", type=float, default=0.03, help="Cutout width in degrees.")
    parser.add_argument("--max-downloads", type=int, default=3, help="Maximum number of FITS cutouts to download.")
    args = parser.parse_args()

    if not (-90 <= args.dec <= 90):
        parser.error("--dec must be between -90 and +90 degrees.")
    if not (0 <= args.ra < 360):
        parser.error("--ra must be between 0 and 360 degrees.")
    if args.size <= 0:
        parser.error("--size must be positive.")
    if args.max_downloads < 1:
        parser.error("--max-downloads must be at least 1.")

    for folder in (CUTOUT_DIR, PREVIEW_DIR, INVENTORY_DIR):
        folder.mkdir(parents=True, exist_ok=True)

    # IRSA notes that reading SPHEREx FITS can take longer than Astropy's default.
    conf.remote_timeout = 180

    print("\nORBITAL EYE | SPHEREx Milestone 01")
    print(f"Target: {args.target}")
    print(f"ICRS: RA={args.ra:.9f} deg, Dec={args.dec:.9f} deg")
    print(f"Collections: {COLLECTIONS_NOTE}")
    print(f"Bandpass: {args.bandpass}")
    print("\n1/3 Searching NASA/IPAC IRSA TAP...")

    query = build_tap_query(args.ra, args.dec, args.size, args.bandpass)

    try:
        results = Irsa.query_tap(query)
    except Exception as exc:
        print("\nIRSA TAP query failed.")
        print("Check your internet connection and try again.")
        print(f"Details: {type(exc).__name__}: {exc}")
        return 2

    print(f"Rows returned: {len(results)}")

    target_slug = safe_name(args.target)
    inventory_path = INVENTORY_DIR / f"{target_slug}_inventory.csv"
    results.write(inventory_path, format="csv", overwrite=True)
    print(f"Full observation inventory saved: {inventory_path}")

    if len(results) == 0:
        print("\nNo observations overlap this exact coordinate in this bandpass.")
        print("This does NOT prove the target has no SPHEREx observations.")
        print("Next checks: other detector bands, deep-field collections, epoch-propagated")
        print("coordinates for high-proper-motion targets, and archive coverage.")
        return 0

    # Select up to N observations spread across the time-sorted inventory,
    # rather than downloading only the first few adjacent exposures.
    count = min(args.max_downloads, len(results))
    chosen_indices = np.unique(np.linspace(0, len(results) - 1, count, dtype=int))

    print("\n2/3 Downloading selected FITS cutouts...")
    manifest = {
        "target": args.target,
        "coordinates_icrs_deg": {"ra": args.ra, "dec": args.dec},
        "collection_search": COLLECTIONS_NOTE,
        "bandpass": args.bandpass,
        "cutout_size_deg": args.size,
        "inventory_csv": str(inventory_path.relative_to(PROJECT_DIR)),
        "archive_query_method": "IRSA TAP: spherex.artifact JOIN spherex.plane",
        "downloaded_products": [],
    }

    for output_number, row_index in enumerate(chosen_indices, start=1):
        row = results[int(row_index)]
        url = str(row["cutout_url"])
        fits_path = CUTOUT_DIR / f"{target_slug}_{args.bandpass}_epoch_{output_number:02d}.fits"
        preview_path = PREVIEW_DIR / f"{target_slug}_{args.bandpass}_epoch_{output_number:02d}.png"

        print(f"\n[{output_number}/{len(chosen_indices)}] {row['observation_time']}")
        try:
            download_file(url, fits_path)
            summary = inspect_and_preview(fits_path, preview_path)
            summary["observation_time_from_tap"] = str(row["observation_time"])
            summary["bandpass_from_tap"] = str(row["bandpass"])
            summary["source_cutout_url"] = url
            manifest["downloaded_products"].append(summary)

            print(f"  FITS: {fits_path}")
            print(f"  PNG:  {preview_path}")
            print(f"  Extensions: {[item['name'] for item in summary['extensions']]}")
            print(f"  Detector/date: {summary['DETECTOR']} / {summary['DATE']}")
            print(f"  Image shape: {summary['image_shape']} | Units: {summary['BUNIT']}")
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}")

    manifest_path = INVENTORY_DIR / f"{target_slug}_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    print("\n3/3 Complete.")
    print(f"Manifest: {manifest_path}")
    print(f"Successfully downloaded: {len(manifest['downloaded_products'])}/{len(chosen_indices)}")

    if manifest["downloaded_products"]:
        print("\nSUCCESS: at least one real SPHEREx FITS cutout was retrieved and inspected.")
        print("Important: these are observations overlapping the supplied coordinate.")
        print("They are not yet a confirmed detection or a measured proper-motion result.")
        return 0

    print("\nNo cutout was successfully retrieved. Review the errors above before proceeding.")
    return 3


if __name__ == "__main__":
    sys.exit(main())
