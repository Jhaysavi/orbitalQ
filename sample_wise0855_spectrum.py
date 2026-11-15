
import numpy as np
import astropy.units as u

from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord

URL = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/hips5_cube/hips_20261026/Norder5/"
    "Dir10000/Npix10226_cube.fits"
)

RA = 133.795129
DEC = -7.245147

# Nine representative one-based spectral planes.
PLANES = [1, 17, 18, 35, 50, 51, 52, 68, 102]

target = SkyCoord(
    RA * u.deg,
    DEC * u.deg,
    frame="icrs",
)

print("Opening SPHEREx cube remotely...")

with fits.open(
    URL,
    use_fsspec=True,
    fsspec_kwargs={"block_size": 64 * 1024},
    lazy_load_hdus=True,
) as hdul:

    wcs = WCS(hdul["IMAGE"].header, fobj=hdul).celestial

    x, y = wcs.world_to_pixel(target)

    x = int(round(float(x)))
    y = int(round(float(y)))

    # Small 11 x 11 region around the target.
    radius = 5

    x0, x1 = x - radius, x + radius + 1
    y0, y1 = y - radius, y + radius + 1

    wavelengths = (
        hdul["WCS-WAVE"].data["WAVELENGTHS"][0].ravel()
    )

    channels = hdul["SPECTRAL_CHANNELS"].data

    print("\nTarget pixel:", x, y)
    print("Cutout:", x0, x1, y0, y1)

    print("\nDIAGNOSTIC SPECTRAL SAMPLE")
    print("=" * 85)

    print(
        f"{'Plane':>5} {'Wavelength':>12} "
        f"{'Detector':>9} {'Channel':>8} "
        f"{'Center MJy/sr':>15} {'Local median':>15} "
        f"{'Center NHITS':>13} {'Center FLAGS':>13}"
    )

    for plane_number in PLANES:

        # FITS spectral planes are one-based.
        # NumPy/Astropy section indexing is zero-based.
        index = plane_number - 1

        image = np.asarray(
            hdul["IMAGE"].section[index, y0:y1, x0:x1]
        )

        hits = np.asarray(
            hdul["NHITS"].section[index, y0:y1, x0:x1]
        )

        flags = np.asarray(
            hdul["FLAGS"].section[index, y0:y1, x0:x1]
        )

        center_value = image[radius, radius]
        center_hits = hits[radius, radius]
        center_flags = flags[radius, radius]

        finite = image[np.isfinite(image)]
        local_median = (
            float(np.median(finite))
            if finite.size else np.nan
        )

        channel = channels[index]

        print(
            f"{plane_number:5d} "
            f"{wavelengths[index]:12.4f} "
            f"{int(channel['DETECTOR']):9d} "
            f"{int(channel['SUBCHAN']):8d} "
            f"{float(center_value):15.6g} "
            f"{local_median:15.6g} "
            f"{int(center_hits):13d} "
            f"{int(center_flags):13d}"
        )

print("\nDiagnostic extraction complete.")
print("Raw flag values are reported without interpreting their bit meanings.")
