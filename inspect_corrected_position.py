
import warnings
import numpy as np
import astropy.units as u

from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.io import fits
from astropy.wcs import WCS
from erfa import ErfaWarning


TILE_URL = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/hips5_cube/hips_20261026/Norder5/Dir10000/"
    "Npix10226_cube.fits"
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

# Provisional midpoint of the DR1 cube time coverage
mjd_mid = (60789.75076 + 61174.49276) / 2

target = reference_position.apply_space_motion(
    new_obstime=Time(mjd_mid, format="mjd")
)

# Wavelength planes to inspect
planes = [1, 17, 18, 35, 50, 68, 102]

# Inspect an 11 x 11 pixel neighbourhood
half_size = 5

print("CORRECTED WISE 0855 NEIGHBOURHOOD")
print("=" * 65)

print(f"Provisional epoch MJD: {mjd_mid:.5f}")
print(f"Corrected RA: {target.ra.deg:.8f}")
print(f"Corrected Dec: {target.dec.deg:.8f}")


# Suppress the expected missing-distance warning.
# This does NOT add parallax to the position calculation.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", ErfaWarning)

    with fits.open(
        TILE_URL,
        use_fsspec=True,
        fsspec_kwargs={"block_size": 1024 * 1024},
    ) as hdul:

        # Read the celestial WCS
        wcs = WCS(
            hdul["IMAGE"].header,
            fobj=hdul,
        ).celestial

        # Convert corrected sky position into cube pixels
        x, y = wcs.world_to_pixel(target)

        cx = int(round(float(x)))
        cy = int(round(float(y)))

        print(f"\nCorrected pixel: X={x:.3f}, Y={y:.3f}")
        print(f"Rounded pixel:   X={cx}, Y={cy}")

        # Define the 11 x 11 neighbourhood
        x0 = cx - half_size
        x1 = cx + half_size + 1

        y0 = cy - half_size
        y1 = cy + half_size + 1

        print("\nPlane measurements")
        print("-" * 65)

        # Inspect each selected wavelength plane
        for plane in planes:

            # Read the image, hit-count and flag neighbourhoods
            flags = np.asarray(
                hdul["FLAGS"].section[
                    plane - 1, y0:y1, x0:x1
                ]
            )

            hits = np.asarray(
                hdul["NHITS"].section[
                    plane - 1, y0:y1, x0:x1
                ]
            )

            image = np.asarray(
                hdul["IMAGE"].section[
                    plane - 1, y0:y1, x0:x1
                ]
            )

            # Count occurrences of each complete flag value
            unique, counts = np.unique(
                flags,
                return_counts=True
            )

            # Count SOURCE and OUTLIER flags
            source_count = np.count_nonzero(
                flags & (1 << 21)
            )

            outlier_count = np.count_nonzero(
                flags & (1 << 19)
            )

            # Values at the central pixel
            center_value = image[half_size, half_size]
            center_hits = hits[half_size, half_size]

            # Median of finite image values in the patch
            finite = image[np.isfinite(image)]

            median = (
                float(np.median(finite))
                if finite.size
                else float("nan")
            )

            print(f"\nPlane {plane}")
            print(f"  SOURCE pixels:  {source_count}/121")
            print(f"  OUTLIER pixels: {outlier_count}/121")
            print(f"  Centre NHITS:   {center_hits}")
            print(f"  Centre IMAGE:   {center_value}")
            print(f"  Patch median:   {median}")

            print("  Flag counts:")

            for value, count in zip(unique, counts):
                print(f"    {value:>10}: {count}")

            # ------------------------------------------------
            # NEW SECTION: inspect additional quality flags
            # ------------------------------------------------

            # Bit 0  = TRANSIENT
            # Bit 2  = SUR_ERROR
            # Bit 28 = HALO

            suspicious_mask = (
                ((flags & (1 << 0)) != 0)
                | ((flags & (1 << 2)) != 0)
                | ((flags & (1 << 28)) != 0)
            )

            locations = np.argwhere(suspicious_mask)

            if len(locations) > 0:

                print("  Additional quality-flagged pixels:")

                for py, px in locations:

                    print(
                        f"    Pixel ({x0 + px}, {y0 + py})"
                        f" | FLAG={int(flags[py, px])}"
                        f" | NHITS={int(hits[py, px])}"
                        f" | IMAGE={float(image[py, px])}"
                    )

            else:
                print("  No additional quality flags found.")

print("\nCorrected-position inspection complete.")
