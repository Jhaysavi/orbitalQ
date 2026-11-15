
import csv
import warnings

from collections import defaultdict
from pathlib import Path

import astropy.units as u

from astropy.coordinates import SkyCoord, get_sun
from astropy.io import fits
from astropy.time import Time
from erfa import ErfaWarning


INPUT_FILE = "spherex_dr1_level2_inventory.csv"
OUTPUT_FILE = "spherex_dr1_period_dates.csv"

BUCKET_URL = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
)

# Published WISE 0855 reference astrometry
reference_position = SkyCoord(
    ra=133.795224 * u.deg,
    dec=-7.245138 * u.deg,
    pm_ra_cosdec=-8.06 * u.arcsec / u.yr,
    pm_dec=0.70 * u.arcsec / u.yr,
    obstime=Time(55320.4, format="mjd"),
    frame="icrs",
)


def read_inventory():

    periods = defaultdict(list)

    with open(
        INPUT_FILE,
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            periods[row["planning_period"]].append(row)

    return periods


def choose_representative_file(rows):

    # Prefer the main processing run and detector 1.
    # This is only for sampling the period's observation date.
    main_rows = [
        row for row in rows
        if "retry" not in row["processing_run"].lower()
        and row["detector"] == "1"
    ]

    candidates = main_rows if main_rows else rows

    candidates.sort(key=lambda row: row["filename"])

    return candidates[0]


def inspect_observation_date(row):

    url = BUCKET_URL + row["s3_key"]

    with fits.open(
        url,
        mode="readonly",
        use_fsspec=True,
        fsspec_kwargs={
            "block_size": 65536,
        },
    ) as hdul:

        header = hdul["IMAGE"].header

        date_obs = header.get("DATE-OBS")
        mjd_obs = header.get("MJD-OBS")

        if mjd_obs is None and date_obs is not None:
            mjd_obs = Time(date_obs).mjd

        if mjd_obs is None:
            raise ValueError(
                "Neither DATE-OBS nor MJD-OBS found"
            )

        return date_obs, float(mjd_obs)


def main():

    print("SPHEREx DR1 — OBSERVATION DATE SAMPLING")
    print("=" * 70)

    periods = read_inventory()

    print(f"Planning periods: {len(periods)}")
    print("Reading one representative FITS header per period.")
    print("No image arrays are being downloaded.")
    print()

    results = []

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ErfaWarning)

        for index, (period, rows) in enumerate(
            sorted(periods.items()), start=1
        ):

            row = choose_representative_file(rows)

            try:
                date_obs, mjd_obs = inspect_observation_date(row)

                observation_time = Time(
                    mjd_obs,
                    format="mjd",
                )

                target = reference_position.apply_space_motion(
                    new_obstime=observation_time
                )

                sun = get_sun(observation_time).icrs

                elongation = target.separation(sun).deg

                result = {
                    "planning_period": period,
                    "date_obs": date_obs,
                    "mjd_obs": mjd_obs,
                    "solar_elongation_deg": elongation,
                    "difference_from_90_deg": abs(
                        elongation - 90.0
                    ),
                    "files_in_period": len(rows),
                    "sample_filename": row["filename"],
                    "sample_s3_key": row["s3_key"],
                    "status": "OK",
                }

                results.append(result)

                print(
                    f"[{index:03}/{len(periods):03}] "
                    f"{period} | "
                    f"{date_obs} | "
                    f"Elongation {elongation:.2f} deg"
                )

            except Exception as error:

                print(
                    f"[{index:03}/{len(periods):03}] "
                    f"{period} | ERROR: {error}"
                )

                results.append({
                    "planning_period": period,
                    "files_in_period": len(rows),
                    "sample_filename": row["filename"],
                    "sample_s3_key": row["s3_key"],
                    "status": f"ERROR: {error}",
                })

    fieldnames = [
        "planning_period",
        "date_obs",
        "mjd_obs",
        "solar_elongation_deg",
        "difference_from_90_deg",
        "files_in_period",
        "sample_filename",
        "sample_s3_key",
        "status",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(results)

    successful = sum(
        row["status"] == "OK"
        for row in results
    )

    print("\n" + "=" * 70)
    print("DATE SAMPLING COMPLETE")
    print(f"Successful headers: {successful}")
    print(f"Failed headers: {len(results) - successful}")
    print(f"Saved to: {Path(OUTPUT_FILE).resolve()}")


if __name__ == "__main__":
    main()
