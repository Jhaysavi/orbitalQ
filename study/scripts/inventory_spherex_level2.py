
import csv
import requests
from pathlib import Path
from xml.etree import ElementTree as ET

BASE = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com"
ROOT = "qr3/level2/"
PROJECT_DIR = Path(__file__).resolve().parents[2]

session = requests.Session()


def xml_text(element, name):
    for child in element:
        if child.tag.endswith(name):
            return child.text or ""
    return ""


def list_subfolders(prefix):
    """Return immediate subfolders under an S3 prefix."""
    folders = []
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

        for item in root:
            if item.tag.endswith("CommonPrefixes"):
                folder = xml_text(item, "Prefix")
                if folder:
                    folders.append(folder)

        truncated = xml_text(root, "IsTruncated").lower() == "true"
        token = xml_text(root, "NextContinuationToken")

        if not truncated or not token:
            break

    return sorted(set(folders))


def count_fits_files(prefix):
    """Count FITS objects using paginated S3 listings."""
    count = 0
    token = None

    while True:
        params = {
            "list-type": "2",
            "prefix": prefix,
            "max-keys": "1000",
        }

        if token:
            params["continuation-token"] = token

        response = session.get(BASE, params=params, timeout=60)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        for item in root:
            if item.tag.endswith("Contents"):
                key = xml_text(item, "Key")
                if key.lower().endswith(".fits"):
                    count += 1

        truncated = xml_text(root, "IsTruncated").lower() == "true"
        token = xml_text(root, "NextContinuationToken")

        if not truncated or not token:
            break

    return count


def main():
    print("Discovering observing weeks...")
    weeks = list_subfolders(ROOT)
    print(f"Observing weeks found: {len(weeks)}")

    inventory = []

    for week_index, week in enumerate(weeks, start=1):
        week_name = week.rstrip("/").split("/")[-1]
        print(f"\n[{week_index}/{len(weeks)}] WEEK {week_name}")

        runs = list_subfolders(week)

        for run in runs:
            run_name = run.rstrip("/").split("/")[-1]

            # Ignore anything that is not a Level 2 processing run.
            if not run_name.startswith("l2b"):
                continue

            detector_folders = list_subfolders(run)

            for detector_folder in detector_folders:
                detector = detector_folder.rstrip("/").split("/")[-1]

                if detector not in {"1", "2", "3", "4", "5", "6"}:
                    continue

                count = count_fits_files(detector_folder)

                inventory.append({
                    "week": week_name,
                    "run": run_name,
                    "detector": detector,
                    "fits_files": count,
                    "prefix": detector_folder,
                })

                print(
                    f"  {run_name} | detector {detector}: "
                    f"{count} FITS files"
                )

    output = PROJECT_DIR / "study" / "results" / "spherex_level2_inventory.csv"

    columns = [
        "week",
        "run",
        "detector",
        "fits_files",
        "prefix",
    ]

    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(inventory)

    total_files = sum(row["fits_files"] for row in inventory)

    print("\nINVENTORY SUMMARY")
    print("-----------------")
    print("Weeks found:", len(weeks))
    print("Run/detector folders:", len(inventory))
    print("Total FITS files:", total_files)
    print("Inventory saved to:", output)


if __name__ == "__main__":
    main()
