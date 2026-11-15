
import requests
from pathlib import Path

OUTPUT_FILE = Path(__file__).resolve().parents[2] / "study" / "results" / "spherex_explorer_response.html"

URL = "https://irsa.ipac.caltech.edu/applications/spherex/"

params = {
    "api": "spectral-images",
    "ra": "133.795129",
    "dec": "-7.245147",
    "sr": "30m",
    "spatialRegionOperation": "intersects",
    "execute": "true",
}

print("Testing SPHEREx Data Explorer...")
print("Target: RA 133.795129, Dec -7.245147")

try:
    response = requests.get(
        URL,
        params=params,
        timeout=90,
        headers={"User-Agent": "orbitalQ/0.1"},
    )

    print("\nHTTP status:", response.status_code)
    print("Final URL:", response.url)
    print("Content type:", response.headers.get("Content-Type"))
    print("Response size:", len(response.content), "bytes")

    response.raise_for_status()

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"\nResponse saved to {OUTPUT_FILE}")
    print("Open that file in your browser to inspect the response.")

except Exception as error:
    print("\nREQUEST FAILED")
    print(repr(error))
