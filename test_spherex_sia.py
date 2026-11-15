
import requests
from astropy.table import Table
from io import BytesIO

RA = 133.795129
DEC = -7.245147

# A 0.1-degree search radius is an initial candidate search,
# not a substitute for propagating the target's position.
RADIUS_DEG = 0.1

COLLECTIONS = [
    "spherex_dr1",
    "spherex_dr1_deep",
    "spherex_qr3",
    "spherex_qr3_deep",
]

URL = "https://irsa.ipac.caltech.edu/SIA"

for collection in COLLECTIONS:
    print(f"\nSearching {collection}...")

    params = {
        "COLLECTION": collection,
        "POS": f"circle {RA} {DEC} {RADIUS_DEG}",
    }

    try:
        response = requests.get(
            URL,
            params=params,
            timeout=90,
        )

        print("HTTP status:", response.status_code)
        print("Content type:", response.headers.get("Content-Type"))

        response.raise_for_status()

        table = Table.read(
            BytesIO(response.content),
            format="votable",
        )

        print("Matching image rows:", len(table))
        print("Available columns:", table.colnames)

        if len(table):
            output = f"{collection}_wise0855_candidates.csv"
            table.write(output, format="csv", overwrite=True)
            print("Saved:", output)

    except Exception as error:
        print("SEARCH FAILED:", repr(error))
