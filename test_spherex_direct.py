
from pathlib import Path
from io import StringIO

import pandas as pd
import requests

# Official IRSA SIA2 endpoint
SIA_URL = "https://irsa.ipac.caltech.edu/SIA"

# Use the same test coordinates as the successful curl test.
RA = 127.69444
DEC = -39.17760
RADIUS_DEG = 0.01

COLLECTION = "spherex_qr3"

OUTPUT_DIR = Path("data/inventory")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "spherex_qr3_direct_test.csv"

params = {
    "COLLECTION": COLLECTION,
    "POS": f"CIRCLE {RA} {DEC} {RADIUS_DEG}",
    "RESPONSEFORMAT": "CSV",
}

print("=" * 55)
print("orbitalQ - Direct SPHEREx SIA2 test")
print("=" * 55)
print(f"Endpoint: {SIA_URL}")
print(f"Collection: {COLLECTION}")
print(f"Coordinates: RA={RA}, Dec={DEC}")
print("Sending request...")

try:
    response = requests.get(
        SIA_URL,
        params=params,
        timeout=(15, 90),
    )

    print(f"\nHTTP status: {response.status_code}")
    print(f"Response type: {response.headers.get('Content-Type')}")
    print(f"Response size: {len(response.content)} bytes")
    print(f"Final URL: {response.url}")

    response.raise_for_status()

    content = response.text.lstrip("\ufeff").strip()

    if not content:
        raise RuntimeError("IRSA returned an empty response.")

    # IRSA can return HTML tables as well as CSV.
    if content.lower().startswith(("<!doctype html", "<html")):
        tables = pd.read_html(StringIO(content))
        if not tables:
            raise RuntimeError("HTML response contained no readable tables.")

        results = None
        for table in tables:
            table.columns = [
                str(column).strip().lower()
                for column in table.columns
            ]
            if "access_url" in table.columns:
                results = table
                break

        if results is None:
            raise RuntimeError(
                "HTML response did not contain an access_url column."
            )
    else:
        results = pd.read_csv(StringIO(content))
        results.columns = [
            str(column).strip().lower()
            for column in results.columns
        ]

    if "access_url" not in results.columns:
        raise RuntimeError(
            "No access_url column found. Response preview:\n"
            + content[:1500]
        )

    results.to_csv(OUTPUT_FILE, index=False)

    print(f"\nObservations returned: {len(results)}")
    print(f"Inventory saved: {OUTPUT_FILE}")

    if len(results) == 0:
        print("\nThe query worked, but returned zero observations.")
    else:
        print("\nFirst observations:")
        useful_columns = [
            column
            for column in [
                "obs_id",
                "obs_collection",
                "energy_bandpassname",
                "t_min",
                "access_url",
            ]
            if column in results.columns
        ]

        print(results[useful_columns].head(3).to_string(index=False))
        print("\nSUCCESS: Direct SIA2 query returned image records.")

except Exception as error:
    print("\nDIRECT SIA2 TEST FAILED")
    print(f"{type(error).__name__}: {error}")
    raise
