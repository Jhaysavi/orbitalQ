
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.io import fits
from astropy.wcs import WCS

TILE_URL = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/hips5_cube/hips_20261026/Norder5/Dir10000/"
    "Npix10226_cube.fits"
)

# Published WISE astrometry from Luhman (2014)
reference_position = SkyCoord(
    ra=133.795224 * u.deg,
    dec=-7.245138 * u.deg,
    pm_ra_cosdec=-8.06 * u.arcsec / u.yr,
    pm_dec=0.70 * u.arcsec / u.yr,
    obstime=Time(55320.4, format="mjd"),
    frame="icrs",
)

# Time limits recorded in the DR1 cube metadata
mjd_start = 60789.75076
mjd_end = 61174.49276
mjd_mid = (mjd_start + mjd_end) / 2

# Original challenge coordinates, for comparison
original_position = SkyCoord(
    ra=133.795129 * u.deg,
    dec=-7.245147 * u.deg,
    frame="icrs",
)

print("WISE 0855 — PROPER MOTION CORRECTION")
print("=" * 65)

with fits.open(
    TILE_URL,
    use_fsspec=True,
    fsspec_kwargs={"block_size": 1024 * 1024},
) as hdul:

    wcs = WCS(
        hdul["IMAGE"].header,
        fobj=hdul,
    ).celestial

    positions = [
        ("Original challenge", original_position),
        (
            "2025 start",
            reference_position.apply_space_motion(
                new_obstime=Time(mjd_start, format="mjd")
            ),
        ),
        (
            "2026 midpoint",
            reference_position.apply_space_motion(
                new_obstime=Time(mjd_mid, format="mjd")
            ),
        ),
        (
            "2026 end",
            reference_position.apply_space_motion(
                new_obstime=Time(mjd_end, format="mjd")
            ),
        ),
    ]

    for label, position in positions:
        x, y = wcs.world_to_pixel(position)

        print(f"\n{label}")
        print(f"  RA:       {position.ra.deg:.8f} deg")
        print(f"  Dec:      {position.dec.deg:.8f} deg")
        print(f"  Pixel X:  {x:.3f}")
        print(f"  Pixel Y:  {y:.3f}")
        print(f"  In tile:  {0 <= x < 512 and 0 <= y < 512}")

print("\nPosition calculation complete.")
