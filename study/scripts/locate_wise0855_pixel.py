
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np

url = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/hips5_cube/hips_20261026/Norder5/"
    "Dir10000/Npix10226_cube.fits"
)

ra_deg = 133.795129
dec_deg = -7.245147

target = SkyCoord(
    ra=ra_deg * u.deg,
    dec=dec_deg * u.deg,
    frame="icrs",
)

print("Opening remote FITS headers...")

with fits.open(
    url,
    use_fsspec=True,
    fsspec_kwargs={"block_size": 1024 * 1024},
    lazy_load_hdus=True,
) as hdul:

    # Important: pass the complete HDU list to WCS.
    # This allows Astropy to resolve the FITS lookup tables.
    wcs_full = WCS(hdul["IMAGE"].header, fobj=hdul)
    wcs_celestial = wcs_full.celestial

    print("\nCelestial WCS:")
    print(wcs_celestial)

    # Convert sky coordinates to zero-based pixel coordinates.
    x, y = wcs_celestial.world_to_pixel(target)

    print("\nWISE 0855 position")
    print("------------------")
    print(f"RA: {ra_deg:.6f} degrees")
    print(f"Dec: {dec_deg:.6f} degrees")
    print(f"Pixel X: {float(x):.4f}")
    print(f"Pixel Y: {float(y):.4f}")

    nx = hdul["IMAGE"].header["NAXIS1"]
    ny = hdul["IMAGE"].header["NAXIS2"]

    inside = (
        np.isfinite(x)
        and np.isfinite(y)
        and -0.5 <= x < nx - 0.5
        and -0.5 <= y < ny - 0.5
    )

    print("\nTile dimensions:", nx, "x", ny)
    print("Target inside tile:", inside)

    if inside:
        # Round-trip check: pixel coordinates back to sky.
        recovered = wcs_celestial.pixel_to_world(x, y)

        separation = target.separation(recovered)

        print("\nRound-trip coordinate check")
        print("---------------------------")
        print(f"Recovered RA: {recovered.ra.deg:.8f}")
        print(f"Recovered Dec: {recovered.dec.deg:.8f}")
        print(f"Separation: {separation.to(u.arcsec):.6f}")

print("\nCoordinate check complete.")
