
from astroquery.ipac.irsa import Irsa
from astropy.coordinates import SkyCoord
import astropy.units as u

# WISE 0855 supplied coordinates.
# Reference epoch is not specified, so treat these as
# provisional coordinates for this initial archive search.
coord = SkyCoord(
    ra=133.795129 * u.deg,
    dec=-7.245147 * u.deg,
    frame="icrs",
)

query = f"""
SELECT
    a.uri,
    p.time_bounds_lower,
    p.energy_bandpassname
FROM spherex.artifact AS a
JOIN spherex.plane AS p
    ON a.planeid = p.planeid
WHERE 1 = CONTAINS(
    POINT('ICRS', {coord.ra.deg}, {coord.dec.deg}),
    p.poly
)
ORDER BY p.time_bounds_lower
"""

print("Submitting SPHEREx TAP query...")
print("Target:", coord.to_string("decimal"))

try:
    results = Irsa.query_tap(query)

    print("\nQuery successful!")
    print("Matching image records:", len(results))
    print("Columns:", results.colnames)

    if len(results) > 0:
        output = "wise0855_tap_candidates.csv"
        results.write(output, format="csv", overwrite=True)

        print("Saved:", output)
        print("\nFirst 10 records:")
        print(results[:10])

    else:
        print("No image footprints contain the supplied coordinates.")

except Exception as error:
    print("\nTAP QUERY FAILED")
    print(repr(error))
