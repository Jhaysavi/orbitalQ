
from astropy.io import fits

url = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/hips5_cube/hips_20261026/Norder5/Dir10000/"
    "Npix10226_cube.fits"
)

with fits.open(
    url,
    use_fsspec=True,
    fsspec_kwargs={"block_size": 1024 * 1024},
    lazy_load_hdus=True,
) as hdul:

    image_header = hdul["IMAGE"].header

    print("\n1. SPATIAL AND SPECTRAL WCS HEADER")
    print("=" * 55)

    for card in image_header.cards:
        key = card.keyword

        if (
            key.startswith((
                "WCS", "CTYPE", "CRVAL", "CRPIX", "CDELT",
                "CD", "PC", "PV", "PS", "CUNIT", "LTV",
                "LTM", "RADESYS", "EQUINOX"
            ))
            or key in ("NAXIS", "NAXIS1", "NAXIS2", "NAXIS3")
        ):
            print(f"{key:16} = {card.value}")

    print("\n2. SPECTRAL_CHANNELS TABLE")
    print("=" * 55)

    channels = hdul["SPECTRAL_CHANNELS"].data
    print("Columns:", hdul["SPECTRAL_CHANNELS"].columns.names)

    for row in channels[:8]:
        print(row)

    print("\nLast 5 channel rows:")
    for row in channels[-5:]:
        print(row)

    print("\n3. WCS-WAVE TABLE")
    print("=" * 55)

    wave_hdu = hdul["WCS-WAVE"]
    print("Columns:", wave_hdu.columns.names)

    for row in wave_hdu.data:
        for name in wave_hdu.columns.names:
            values = row[name]
            print(f"\n{name}:")
            print(values)

print("\nMetadata inspection complete.")
