# Scientific method and sources

## Purpose and scope

orbitalQ is a public-facing inspection tool for real SPHEREx observations. It
helps a user see where a target falls on the sky and how separate observations
may differ. It does not establish a new planet, proper motion, or variability
from an uncalibrated visual difference.

## Data products

### All-Sky Cube preview

The DR1 All-Sky Cube is used for a small, target-centred preview. Its 102
nominal planes are spectral channels across the SPHEREx near-infrared range,
not 102 dates. The preview therefore answers “what does this sky position
look like in this spectral channel?” rather than “what changed over time?”.
The app records the cube object URL, tile, WCS-derived pixel position,
channel/wavelength metadata and release in the provenance panel.

### Level 2 temporal observations

Temporal inspection uses Level 2 Spectral Image multi-extension FITS files.
Each observation is represented by its actual header metadata: original
filename/object key, release, processing version, `OBSID`, `DATE-OBS`,
`MJD-OBS`, detector, WCS and units. The `IMAGE`, `FLAGS` and `VARIANCE`
extensions are retained when available. The app sorts by parsed observation
time, never by filename or spectral-channel order.

## Coordinate and epoch method

The WCS conversion is treated as a scalar operation: a single coordinate must
produce exactly one pixel pair before bounds checks, integer indexing or
cutout calculations. NumPy/Astropy scalar-like values are converted to Python
`float` values only after validating that the result has one element.

For moving targets, a coordinate is meaningful only with an epoch. The WISE
0855 challenge coordinate is preserved as a supplied reference value, not as
an all-epoch truth. Where a published position and proper motion are used, the
study scripts propagate the coordinate with Astropy to the observation epoch.
Parallax and catalogue systematics must be stated separately; propagation is
not a detection measurement.

## Comparison safeguards

Before a scientific difference image or photometry is attempted, check:

1. The two files overlap the target after WCS transformation and image
   registration.
2. Wavelength/bandpass, detector and processing release are compatible.
3. `FLAGS` are interpreted with the official bit definitions and excluded
   pixels are visible to the user.
4. `VARIANCE` is used to report measurement uncertainty rather than relying on
   raw pixel differences.
5. PSF/ePSF, background, zodiacal-light treatment and calibration differences
   are documented.
6. The apparent change survives independent astrometric/photometric checks.

The Level 2 `IMAGE` is calibrated surface brightness and the Level 2 `ZODI`
model is a separate extension; a raw image subtraction is not automatically a
source flux measurement. A candidate result is exploratory evidence only.

## Study method: `sample_dr1_period_dates.py`

The script [sample_dr1_period_dates.py](../study/scripts/sample_dr1_period_dates.py)
groups a local DR1 Level 2 inventory by planning period, chooses one
representative detector-1 file, and reads only its FITS header through the
public object URL. It propagates the WISE 0855 reference astrometry to the
header's `MJD-OBS`, computes solar elongation, and writes a planning table.

This is a scheduling/metadata screen, not a coverage result: one sampled
header does not prove that the target was observed, detected, or measured. The
inventory and output are deliberately local because they are generated
research data.

## Archive and technical sources

- [SPHEREx Data Access at IRSA](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)
  documents browsable directories, APIs, SIA, cloud access, and Python access.
- [SPHEREx Data Releases](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-releases/)
  defines DR1, QR3 and the recommendation to use DR1+QR3 rather than QR2 for
  new work.
- [SPHEREx Data Products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/)
  documents Level 2 MEFs, the `IMAGE`, `FLAGS`, `VARIANCE`, `ZODI`, `EPSF`
  and `WCS-WAVE` extensions, detector bands and filename/OBSID conventions.
- [SPHEREx DR1 overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html)
  documents the 102-channel All-Sky Cube and DR1 spectral images, and provides
  the recommended DR1 data citations/DOIs.
- [IRSA SPHEREx cutout tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/)
  demonstrates coordinate queries and Level 2 cutout retrieval.
- [IRSA SPHEREx introductory tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/)
  demonstrates MEF reading, WCS inspection, and archive querying.
- [SPHEREx Explanatory Supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf)
  is the authoritative technical reference for calibration, flags, PSF/ePSF
  and product interpretation.
- [NASA Space Apps 2026](https://www.spaceappschallenge.org/2026/) is the
  challenge context for “Planet X and SPHEREx”.

When publishing results based on DR1, include the archive acknowledgement and
the appropriate DR1 Spectral Images or All-Sky Cube DOI listed in the official
DR1 overview. Preserve the exact object URL/key and header metadata alongside
any derived result.
