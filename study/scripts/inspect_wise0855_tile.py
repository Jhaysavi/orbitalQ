
from astropy.io import fits

url = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/hips5_cube/hips_20261026/Norder5/Dir10000/"
    "Npix10226_cube.fits"
)

print("Opening remote SPHEREx FITS cube...")
print("Only FITS headers will be inspected.")
print("Image data will NOT be loaded.\n")

with fits.open(
    url,
    use_fsspec=True,
    fsspec_kwargs={"block_size": 1024 * 1024},
    lazy_load_hdus=True,
) as hdul:

    print("FITS structure")
    print("==============")
    hdul.info()

    for index, hdu in enumerate(hdul):
        print(f"\n{'=' * 60}")
        print(f"HDU {index}: {hdu.name}")
        print("=" * 60)

        header = hdu.header

        for key in [
            "XTENSION",
            "BITPIX",
            "NAXIS",
            "NAXIS1",
            "NAXIS2",
            "NAXIS3",
            "EXTNAME",
            "BUNIT",
            "BTYPE",
            "CTYPE1",
            "CTYPE2",
            "CTYPE3",
            "CRVAL1",
            "CRVAL2",
            "CRVAL3",
            "CRPIX1",
            "CRPIX2",
            "CDELT1",
            "CDELT2",
            "CDELT3",
            "BUNIT3",
            "BLANKCH",
        ]:
            if key in header:
                print(f"{key:12} = {header[key]}")

print("\nHeader inspection complete.")
