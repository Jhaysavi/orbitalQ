
import re
import requests
import pandas as pd
from astropy.io import fits

BUCKET = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com"
INVENTORY = "spherex_dr1_level2_inventory.csv"

# A small controlled sample: one counter, four sequence tokens, six detectors.
PERIOD = "2025W17_4B"
COUNTER = "0001"

session = requests.Session()


def read_fits_header(url, start_offset):
    """Read one FITS header using HTTP Range requests only."""
    raw = b""
    offset = start_offset

    while True:
        end = offset + 2879
        response = session.get(
            url,
            headers={"Range": f"bytes={offset}-{end}"},
            timeout=30,
        )
        response.raise_for_status()

        if response.status_code != 206:
            raise RuntimeError(
                f"Server did not honour byte range: HTTP {response.status_code}"
            )

        block = response.content
        if not block:
            raise RuntimeError("Empty response while reading FITS header")

        raw += block
        offset += len(block)

        cards = [
            raw[i:i + 80]
            for i in range(0, len(raw), 80)
            if len(raw[i:i + 80]) == 80
        ]

        if any(card[:8].strip() == b"END" for card in cards):
            break

    header = fits.Header.fromstring(raw.decode("ascii"), sep="")
    return header, len(raw)


def read_primary_and_image_headers(url):
    primary, primary_size = read_fits_header(url, 0)

    # The next HDU begins immediately after the padded primary header.
    image_offset = primary_size
    image_header, image_size = read_fits_header(url, image_offset)

    return primary, image_header


def value(header, key):
    return header.get(key, "")


df = pd.read_csv(INVENTORY)

sample = df[
    (df["planning_period"] == PERIOD)
    & (df["filename"].str.contains(rf"_{COUNTER}_", regex=True))
].copy()

sample["sequence_token"] = sample["filename"].str.extract(
    rf"_{COUNTER}_(\d+)D"
)[0]

sample["filename_detector"] = sample["filename"].str.extract(
    rf"_{COUNTER}_\d+D([1-6])"
)[0]

sample = sample.sort_values(["sequence_token", "detector"])

print(f"Selected files: {len(sample)}")
print(f"Planning period: {PERIOD}")
print(f"Counter: {COUNTER}")
print()

results = []

for _, row in sample.iterrows():
    url = f"{BUCKET}/{row['s3_key']}"

    try:
        primary, image = read_primary_and_image_headers(url)

        results.append({
            "token": row["sequence_token"],
            "directory_detector": row["detector"],
            "filename_detector": row["filename_detector"],
            "date_obs": value(image, "DATE-OBS"),
            "mjd_obs": value(image, "MJD-OBS"),
            "obsid": value(image, "OBSID"),
            "image_detector": value(image, "DETECTOR"),
            "expid": value(image, "EXPIDN"),
            "ra_center": value(image, "CRVAL1"),
            "dec_center": value(image, "CRVAL2"),
            "naxis1": value(image, "NAXIS1"),
            "naxis2": value(image, "NAXIS2"),
            "status": "OK",
        })

    except Exception as exc:
        results.append({
            "token": row["sequence_token"],
            "directory_detector": row["detector"],
            "filename_detector": row["filename_detector"],
            "status": f"ERROR: {exc}",
        })

result = pd.DataFrame(results)

print("=== HEADER COMPARISON ===")
print(result.to_string(index=False))

result.to_csv("spherex_sequence_header_comparison.csv", index=False)
print("\nSaved: spherex_sequence_header_comparison.csv")

print("\n=== COUNTS BY TOKEN ===")
if "status" in result:
    print(result.groupby(["token", "status"]).size().to_string())
