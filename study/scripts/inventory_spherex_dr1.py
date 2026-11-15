
import csv
import requests
import xml.etree.ElementTree as ET

from pathlib import Path


BUCKET_URL = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_FILE = PROJECT_DIR / "study" / "results" / "spherex_dr1_level2_inventory.csv"

session = requests.Session()
session.headers.update({
    "User-Agent": "orbitalQ-SPHEREx-Research/1.0"
})


def list_s3(prefix, delimiter=None):
    """
    List S3 objects or directory prefixes.
    Handles pagination automatically.
    """

    continuation_token = None

    while True:

        params = {
            "list-type": "2",
            "prefix": prefix,
        }

        if delimiter:
            params["delimiter"] = delimiter

        if continuation_token:
            params["continuation-token"] = continuation_token

        response = session.get(
            BUCKET_URL,
            params=params,
            timeout=60,
        )

        response.raise_for_status()

        root = ET.fromstring(response.content)

        # Return directory names when delimiter is supplied
        if delimiter:

            for element in root.findall(
                ".//{*}CommonPrefixes/{*}Prefix"
            ):
                yield {
                    "type": "prefix",
                    "prefix": element.text,
                }

        # Return actual files
        else:

            for element in root.findall(
                ".//{*}Contents"
            ):

                key = element.findtext("{*}Key")

                if not key or not key.lower().endswith(".fits"):
                    continue

                yield {
                    "type": "file",
                    "key": key,
                    "size": element.findtext("{*}Size"),
                    "last_modified": element.findtext(
                        "{*}LastModified"
                    ),
                }

        truncated = (
            root.findtext("{*}IsTruncated") == "true"
        )

        if not truncated:
            break

        continuation_token = root.findtext(
            "{*}NextContinuationToken"
        )

        if not continuation_token:
            raise RuntimeError(
                "S3 returned a truncated listing without "
                "a continuation token."
            )


def get_directories(prefix):

    return [
        item["prefix"]
        for item in list_s3(prefix, delimiter="/")
        if item["type"] == "prefix"
    ]


def main():

    total_files = 0

    output_path = Path(OUTPUT_FILE)

    print("SPHEREx DR1 LEVEL 2 INVENTORY")
    print("=" * 65)

    print("Connecting to the public SPHEREx archive...")
    print("No FITS image data will be downloaded.")
    print()

    planning_periods = get_directories("dr1/level2/")

    print(
        f"Planning periods discovered: "
        f"{len(planning_periods)}"
    )

    fieldnames = [
        "planning_period",
        "processing_run",
        "detector",
        "filename",
        "s3_key",
        "size_bytes",
        "last_modified",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csvfile:

        writer = csv.DictWriter(
            csvfile,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for planning_prefix in planning_periods:

            planning_period = (
                planning_prefix.rstrip("/").split("/")[-1]
            )

            print(f"\nPlanning period: {planning_period}")

            processing_runs = get_directories(
                planning_prefix
            )

            for run_prefix in processing_runs:

                processing_run = (
                    run_prefix.rstrip("/").split("/")[-1]
                )

                detector_prefixes = get_directories(
                    run_prefix
                )

                for detector_prefix in detector_prefixes:

                    detector = (
                        detector_prefix.rstrip("/").split("/")[-1]
                    )

                    detector_count = 0

                    for item in list_s3(detector_prefix):

                        key = item["key"]
                        filename = key.split("/")[-1]

                        writer.writerow({
                            "planning_period": planning_period,
                            "processing_run": processing_run,
                            "detector": detector,
                            "filename": filename,
                            "s3_key": key,
                            "size_bytes": item["size"],
                            "last_modified": item["last_modified"],
                        })

                        detector_count += 1
                        total_files += 1

                    csvfile.flush()

                    print(
                        f"  Run {processing_run} | "
                        f"Detector {detector}: "
                        f"{detector_count} FITS files"
                    )

    print("\n" + "=" * 65)
    print("INVENTORY COMPLETE")
    print(f"Total FITS files: {total_files:,}")
    print(f"Saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
