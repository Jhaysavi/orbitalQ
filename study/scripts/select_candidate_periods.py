
import csv
import re
import warnings
from pathlib import Path

from collections import Counter
from datetime import datetime, timedelta

import astropy.units as u

from astropy.coordinates import SkyCoord, get_sun
from astropy.time import Time
from erfa import ErfaWarning


PROJECT_DIR = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_DIR / "study" / "results" / "spherex_dr1_level2_inventory.csv"

# Published WISE 0855 astrometry
reference_position = SkyCoord(
    ra=133.795224 * u.deg,
    dec=-7.245138 * u.deg,
    pm_ra_cosdec=-8.06 * u.arcsec / u.yr,
    pm_dec=0.70 * u.arcsec / u.yr,
    obstime=Time(55320.4, format="mjd"),
    frame="icrs",
)

# Broad screening interval around SPHEREx's nominal
# 90-degree solar elongation.
MIN_ELONGATION = 75
MAX_ELONGATION = 105


def period_midpoint(period):

    match = re.match(r"^(\d{4})W(\d{2})_", period)

    if not match:
        return None

    year = int(match.group(1))
    week = int(match.group(2))

    # Wednesday of the ISO week, at noon UTC.
    return (
        datetime.fromisocalendar(year, week, 3)
        + timedelta(hours=12)
    )


def main():

    counts = Counter()

    print("Reading DR1 inventory...")

    with open(
        INPUT_FILE,
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            counts[row["planning_period"]] += 1

    print(f"Planning periods found: {len(counts)}")

    candidates = []

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ErfaWarning)

        for period, file_count in counts.items():

            midpoint = period_midpoint(period)

            if midpoint is None:
                continue

            observation_time = Time(midpoint, scale="utc")

            # Propagate WISE 0855 to the screening date.
            target = reference_position.apply_space_motion(
                new_obstime=observation_time
            )

            # Apparent geocentric Sun position.
            sun = get_sun(observation_time).icrs

            elongation = target.separation(sun).deg

            if MIN_ELONGATION <= elongation <= MAX_ELONGATION:

                candidates.append({
                    "period": period,
                    "date": midpoint.isoformat(),
                    "elongation": elongation,
                    "files": file_count,
                })

    candidates.sort(
        key=lambda item: item["date"]
    )

    print("\nCANDIDATE PLANNING PERIODS")
    print("=" * 70)

    if not candidates:
        print("No periods inside the selected elongation range.")
        print("We may need to widen the screening interval.")

    for item in candidates:

        print(
            f"{item['period']} | "
            f"{item['date']} | "
            f"Solar elongation: {item['elongation']:.2f} deg | "
            f"Files: {item['files']:,}"
        )

    print("\n" + "=" * 70)
    print(f"Candidate periods: {len(candidates)}")
    print(
        "Candidate FITS files: "
        f"{sum(item['files'] for item in candidates):,}"
    )

    print("\nScreening complete.")


if __name__ == "__main__":
    main()
