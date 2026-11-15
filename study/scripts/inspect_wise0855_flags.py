
import numpy as np
from astropy.io import fits

URL = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/hips5_cube/hips_20261026/Norder5/"
    "Dir10000/Npix10226_cube.fits"
)

X, Y = 205, 233
RADIUS = 5

PLANES = [1, 17, 18, 35, 50, 68, 102]

with fits.open(
    URL,
    use_fsspec=True,
    fsspec_kwargs={"block_size": 65536},
    lazy_load_hdus=True,
) as hdul:

    x0, x1 = X - RADIUS, X + RADIUS + 1
    y0, y1 = Y - RADIUS, Y + RADIUS + 1

    print("WISE 0855 FLAG NEIGHBOURHOOD")
    print("=" * 65)

    for plane in PLANES:
        index = plane - 1

        flags = np.asarray(
            hdul["FLAGS"].section[
                index, y0:y1, x0:x1
            ]
        )

        values, counts = np.unique(
            flags, return_counts=True
        )

        print(f"\nPlane {plane}")
        print("-" * 40)

        for value, count in zip(values, counts):
            print(
                f"Flag value: {int(value):>10} "
                f"Count: {int(count):>3}"
            )

        source_count = np.count_nonzero(
            (flags.astype(np.uint32) & (1 << 21)) != 0
        )

        print(
            f"Pixels carrying SOURCE flag: "
            f"{source_count}/{flags.size}"
        )

print("\nFlag inspection complete.")
