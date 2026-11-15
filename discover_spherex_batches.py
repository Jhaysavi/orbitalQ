
import requests
import xml.etree.ElementTree as ET

BASE = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com"
ROOT = "qr3/level2/"

session = requests.Session()


def list_prefixes(prefix):
    """List immediate subdirectories in the public S3 bucket."""
    prefixes = []
    token = None

    while True:
        params = {
            "list-type": "2",
            "prefix": prefix,
            "delimiter": "/",
            "max-keys": "1000",
        }

        if token:
            params["continuation-token"] = token

        response = session.get(BASE, params=params, timeout=60)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        for element in root.iter():
            if element.tag.endswith("Prefix"):
                if element.text:
                    prefixes.append(element.text)

        truncated = any(
            e.tag.endswith("IsTruncated") and e.text == "true"
            for e in root
        )

        token = next(
            (
                e.text for e in root
                if e.tag.endswith("NextContinuationToken")
            ),
            None,
        )

        if not truncated or not token:
            break

    return sorted(set(prefixes))


def main():
    print("Discovering SPHEREx observing batches...\n")

    weeks = list_prefixes(ROOT)

    print(f"Weekly folders found: {len(weeks)}")

    for week in weeks:
        print(f"\nWEEK: {week}")

        runs = list_prefixes(week)

        for run in runs:
            print(f"  RUN: {run}")

            detectors = list_prefixes(run)

            for detector in detectors:
                print(f"    {detector}")


if __name__ == "__main__":
    main()
