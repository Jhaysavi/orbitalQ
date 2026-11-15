
import requests

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy_healpix import HEALPix

# WISE 0855 challenge coordinates.
# These are the supplied coordinates, not a proper-motion
# propagated position at a specific observation epoch.
ra_deg = 133.795129
dec_deg = -7.245147

# SPHEREx DR1 cube uses HEALPix order 5, NESTED.
healpix = HEALPix(
    nside=32,
    order="nested",
    frame="icrs",
)

target = SkyCoord(
    ra=ra_deg * u.deg,
    dec=dec_deg * u.deg,
    frame="icrs",
)

tile = int(healpix.lonlat_to_healpix(target.ra, target.dec))

directory = (tile // 10000) * 10000

key = (
    "dr1/hips5_cube/hips_20261026/"
    f"Norder5/Dir{directory}/Npix{tile}_cube.fits"
)

url = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    + key
)

print("WISE 0855 DR1 cube tile")
print("-----------------------")
print(f"RA:          {ra_deg:.6f} deg")
print(f"Dec:         {dec_deg:.6f} deg")
print(f"HEALPix:     {tile}")
print(f"Directory:   Dir{directory}")
print(f"Object key:  {key}")

print("\nChecking the remote FITS file without downloading it...")

response = requests.head(url, timeout=60)

print("HTTP status:", response.status_code)
print("File size:", response.headers.get("Content-Length"), "bytes")
print("Content type:", response.headers.get("Content-Type"))
print("Range support:", response.headers.get("Accept-Ranges"))
