import csv
import math
import warnings
import requests
import numpy as np
from pathlib import Path

from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u

BASE = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com"

PREFIX = (
    "qr3/level2/2026W20_2A/"
    "l2b-v27-2026-267/"
)

TARGET = SkyCoord(
    ra=133.795129 * u.deg,
    dec=-7.245147 * u.deg,
    frame="icrs",
)

MAX_FILES = 100
HEADER_START = 2880
HEADER_END = 65535

session = requests.Session()
RESULTS_DIR = Path(__file__).resolve().parents[2] / "study" / "results"


def list_files(prefix, limit):
    """List up to limit FITS objects under an S3 prefix."""
    files = []
    token = None

    while len(files) < limit:
        params = {
            "list-type": "2",
            "prefix": prefix,
            "max-keys": str(min(1000, limit - len(files))),
        }

        if token:
            params["continuation-token"] = token

        response = session.get(
            BASE,
            params=params,
            timeout=60,
        )
        response.raise_for_status()

        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.content)

        def get(element, name):
            for child in element:
                if child.tag.endswith(name):
                    return child.text or ""
            return ""

        for item in root:
            if item.tag.endswith("Contents"):
                key = get(item, "Key")
                if key.lower().endswith(".fits"):
                    files.append(key)

        truncated = get(root, "IsTruncated").lower() == "true"
        token = get(root, "NextContinuationToken")

        if not truncated or not token:
            break

    return files[:limit]



def read_image_header(key):
    """Read only the IMAGE extension header, stopping at END."""
    url = f"{BASE}/{key}"

    start = HEADER_START
    chunk_size = 2880
    max_header_bytes = 1024 * 1024

    data = bytearray()

    while len(data) < max_header_bytes:
        end = start + chunk_size - 1

        response = session.get(
            url,
            headers={"Range": f"bytes={start}-{end}"},
            timeout=(15, 90),
        )

        if response.status_code != 206:
            raise RuntimeError(
                f"Expected HTTP 206, received {response.status_code}"
            )

        data.extend(response.content)
        response.close()

        # FITS headers consist of 80-byte cards.
        for offset in range(0, len(data) - 79, 80):
            card = bytes(data[offset:offset + 80])

            if card[:8].decode("ascii", errors="replace").strip() == "END":
                header_bytes = (
                    math.ceil((offset + 80) / 2880) * 2880
                )

                header_data = bytes(data[:header_bytes])

                return fits.Header.fromstring(
                    header_data.decode("ascii"),
                    sep="",
                )

        start = end + 1
        chunk_size *= 2

    raise RuntimeError("FITS header exceeded maximum allowed size")



def check_footprint(header):
    """Conservative footprint screening followed by pixel test."""
    wcs = WCS(header).celestial

    width = int(header["NAXIS1"])
    height = int(header["NAXIS2"])

    n = 30
    x = np.linspace(0, width - 1, n)
    y = np.linspace(0, height - 1, n)

    px = np.concatenate([
        x, x,
        np.zeros(n),
        np.full(n, width - 1),
    ])

    py = np.concatenate([
        np.zeros(n),
        np.full(n, height - 1),
        y, y,
    ])

    boundary = wcs.pixel_to_world(px, py)
    center = wcs.pixel_to_world(
        (width - 1) / 2,
        (height - 1) / 2,
    )

    radius = center.separation(boundary).max()
    separation = center.separation(TARGET)

    margin = max(1 * u.arcmin, radius * 0.05)

    if separation > radius + margin:
        return False, float("nan"), float("nan"), separation.deg

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pixel_x, pixel_y = wcs.world_to_pixel(TARGET)

    inside = (
        np.isfinite(pixel_x)
        and np.isfinite(pixel_y)
        and 0 <= pixel_x < width
        and 0 <= pixel_y < height
    )

    return inside, pixel_x, pixel_y, separation.deg



def main():
    print("Listing FITS files across all six detectors...")

    files = []

    for detector_id in range(1, 7):
        detector_prefix = f"{PREFIX}{detector_id}/"

        detector_files = list_files(
            detector_prefix,
            MAX_FILES,
        )

        print(
            f"Detector {detector_id}: "
            f"{len(detector_files)} files"
        )

        files.extend(detector_files)

    print(f"\nTotal files selected: {len(files)}")
    print("Scanning headers only...\n")

    results = []
    matches = []
    errors = []

    for index, key in enumerate(files, start=1):
        row = {
            "filename": key,
            "date_obs": "",
            "obsid": "",
            "detector": "",
            "pixel_x": float("nan"),
            "pixel_y": float("nan"),
            "center_separation_deg": float("nan"),
            "status": "",
            "error": "",
        }

        try:
            header = read_image_header(key)

            inside, px, py, separation = check_footprint(header)

            row.update({
                "date_obs": header.get("DATE-OBS", ""),
                "obsid": header.get("OBSID", ""),
                "detector": header.get("DETECTOR", ""),
                "pixel_x": px,
                "pixel_y": py,
                "center_separation_deg": separation,
                "status": "MATCH" if inside else "outside",
            })

            if inside:
                matches.append(row.copy())

            print(
                f"[{index:03d}/{len(files):03d}] "
                f"{row['status']:7s} "
                f"D{row['detector']} | "
                f"{row['date_obs']} | {row['obsid']}"
            )

        except Exception as exc:
            row["status"] = "ERROR"
            row["error"] = str(exc)
            errors.append(row.copy())

            print(
                f"[{index:03d}/{len(files):03d}] "
                f"ERROR: {exc}"
            )

        results.append(row)

    columns = [
        "filename",
        "date_obs",
        "obsid",
        "detector",
        "pixel_x",
        "pixel_y",
        "center_separation_deg",
        "status",
        "error",
    ]

    output = RESULTS_DIR / "wise0855_qr3_all_detectors.csv"

    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)

    match_output = RESULTS_DIR / "wise0855_qr3_matches.csv"

    with open(match_output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(matches)

    print("\nSCAN SUMMARY")
    print("------------")
    print("Files scanned:", len(files))
    print("Footprint matches:", len(matches))
    print(
        "Outside footprints:",
        sum(r["status"] == "outside" for r in results)
    )
    print("Errors:", len(errors))
    print("Full scan saved to:", output)
    print("Matches saved to:", match_output)


if __name__ == "__main__":
    main()

