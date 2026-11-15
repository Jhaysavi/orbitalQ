# orbitalQ — Project Brief & MVP Build Plan

**NASA Space Apps Challenge 2026 · Challenge 12: Planet X and SPHEREx**  
**Project status:** MVP foundation / real-data prototype  
**Project type:** Public-facing astronomy web application

## 1. What is orbitalQ?

**orbitalQ is a target-centred SPHEREx sky explorer.** A user enters celestial coordinates or selects a known target, views real SPHEREx infrared data around that position, and browses available observations in chronological order to investigate changes in position or brightness.

The central experience is simple:

1. Choose a target or enter RA/Dec.
2. See the target's location on a real SPHEREx sky image.
3. Browse the available observations by date.
4. Blink between visits to make moving or changing sources easier to notice.
5. Inspect image quality, wavelength, observation metadata, and the evidence behind any apparent change.

The goal is not to claim a new planet from a visual change. The goal is to make the archive approachable and help people identify interesting candidates that can be checked against astrometry, catalogues, and known Solar System objects.

## 2. The challenge we are answering

The 2026 NASA Space Apps Challenge, **“Planet X and SPHEREx,”** asks for a public-facing web tool that displays images of the sky from the SPHEREx mission and makes it easy for anyone to see how they change over time.

SPHEREx maps the sky in near-infrared light. Its 102 spectral channels cover approximately 0.75–5.0 micrometres. The challenge is about temporal change: objects such as asteroids, comets, stars, and brown dwarfs may move or vary between observations.

**Important distinction:** 102 spectral channels are 102 wavelength samples, not 102 dates. A spectral cube is useful for exploring wavelength-dependent sky data, but a temporal sequence must be assembled from separate Level 2 observations with their own observation times and sky footprints.

## 3. The scientific data model

### SPHEREx products

The application is designed around two complementary products:

**A. Level 2 Spectral Image MEFs — primary source for time comparisons**

- One multi-extension FITS image per sky pointing and detector.
- Image plane is 2040 × 2040 pixels.
- `IMAGE`: calibrated surface brightness, typically MJy/sr.
- `FLAGS`: per-pixel quality and processing flags.
- `VARIANCE`: per-pixel variance.
- `ZODI`: modelled zodiacal foreground; it is not subtracted from the Level 2 `IMAGE`.
- `EPSF`: effective point-spread functions in DR1/QR3.
- `WCS-WAVE`: wavelength lookup information for the linear-variable-filter detector geometry.
- FITS headers include observation identifiers, detector, WCS, and observation time such as `DATE-OBS` / `MJD-OBS`.

A valid time comparison must account for sky registration, detector identity, wavelength response, PSF, uncertainty, and quality flags. Two images at the same sky coordinate are not automatically measurements at the same wavelength.

**B. DR1 All-Sky Cube — quick real-data visual context**

- Full-sky tiled product with 102 spectral planes.
- Each tile is 512 × 512 pixels, about 12.9 arcsec per pixel.
- The 102 planes represent spectral channels.
- The cube has zodiacal light subtracted.
- It is excellent for a quick target-centred spectral preview, but it is not a time-resolved movie.

### Releases to use

Use **DR1 and QR3** for new work. DR1 contains reprocessed Survey 1 and Survey 2 data; QR3 contains Survey 3 and Survey 4 data. Together they supersede QR2. Do not mix QR2 with DR1/QR3 without explicitly handling the calibration differences.

### Archive access

The project has an inventory of the public DR1 Level 2 S3 objects and has successfully read FITS headers using HTTP byte-range requests. During development, the IRSA SIA/TAP endpoints returned HTTP 502 errors, so the first prototype uses the public SPHEREx AWS S3 objects directly. This is an implementation fallback, not a claim that IRSA services are permanently unavailable.

## 4. What makes orbitalQ useful

- **Target-first:** people can start with an object name or coordinates instead of navigating millions of files.
- **Time-first:** the main discovery interface is an ordered sequence of actual observations, not a stack of spectral channels mislabeled as epochs.
- **Evidence-first:** each view should show observation date, OBSID, detector, wavelength context, data quality, and source provenance.
- **Accessible:** a clear public interface, plain-language explanations, and a guided first target.
- **Reproducible:** exportable tables and explicit links/identifiers for the underlying NASA/IPAC data.

## 5. Target list for the first science tests

The initial validation targets are:

- Barnard's Star
- Epsilon Indi B
- WISE 0855−0714
- RW Aurigae
- R Draconis

WISE 0855−0714 is the first engineering target. The challenge coordinate supplied for it is:

- RA = 133.795129°
- Dec = −7.245147°

That coordinate has no stated reference epoch. WISE 0855 has high proper motion, so a science-grade search must not silently treat those coordinates as valid for every observation date. If using an astrometric catalogue position with a known reference epoch and proper motion, propagate it to each `MJD-OBS`; state whether parallax was included.

## 6. MVP scope

### MVP must do

1. Accept RA/Dec and show a target-centred real SPHEREx image cutout.
2. Display the wavelength channel correctly when showing the All-Sky Cube.
3. Accept multiple real Level 2 FITS files and extract target-centred cutouts using each file's celestial WCS.
4. Sort uploaded observations by `DATE-OBS` and let the user step through them.
5. Show basic provenance: filename, OBSID, detector, DATE-OBS, MJD-OBS, and image units.
6. Clearly warn when the display is a spectral channel rather than a time sequence.
7. Avoid unsupported claims of detection or variability.

### Next after the first working app

1. Build a candidate exposure index from the DR1/QR3 S3 inventories.
2. Use WCS footprints to find exposures that actually cover the target.
3. Propagate high-proper-motion targets to each observation epoch.
4. Add same-detector / wavelength-aware temporal matching.
5. Add quality-aware photometry using IMAGE, VARIANCE, FLAGS, and ePSF.
6. Add blink, side-by-side comparison, and carefully qualified difference images.
7. Add CSV export and a source/provenance panel.
8. Deploy the public app.

### Explicitly out of scope for the first MVP

- Claiming discovery of Planet X.
- Treating spectral channels as dates.
- Automated astrophysical classification without validation.
- Quantum computing as a core dependency. Any quantum experiment is optional and must be benchmarked against a classical baseline.

## 7. Current verified progress

- Python environment and core astronomy dependencies are installed in the existing `orbitalQ` repository.
- Public DR1 inventory: 1,179,406 Level 2 FITS objects.
- QR3 inventory was also created separately.
- FITS headers were successfully read with HTTP range requests.
- The DR1 All-Sky Cube tile containing the supplied WISE 0855 coordinates was located: HEALPix tile 10226.
- The cube's WCS was checked and the target coordinate mapped into the tile.
- The cube contains 102 spectral planes; planes 51 and 52 are documented blank channels.
- A small sample around the target was extracted remotely.
- The Level 2 observation grouping and detector filename pattern were investigated.

**Not yet verified:** a Level 2 exposure whose WCS footprint actually covers WISE 0855. The 110 sampled planning-period headers do not prove coverage. The 102 All-Sky Cube planes do not constitute a time series.

## 8. Technology

- Python
- Streamlit for the public web interface
- Astropy for FITS, WCS, coordinates, and time
- NumPy for array operations
- Matplotlib for scientific image display
- pandas for inventories and observation tables
- fsspec / aiohttp for range-based access to public S3 FITS objects
- GitHub for version control
- Streamlit Community Cloud as the initial deployment target

## 9. User experience

### Landing page
“Explore how the infrared sky changes.” Coordinate search, target presets, and a short explanation of SPHEREx.

### Target workspace
Target coordinates, epoch/proper-motion note, sky preview, data-source indicator, and observation list.

### Image viewer
A date-ordered frame selector with image cutout, detector, wavelength context, exposure metadata, and quality information.

### Compare mode
Blink or side-by-side views of two observations. Difference images are enabled only after the frames have been registered and matched in wavelength and PSF.

### Evidence/export
A downloadable observation table and clear source/provenance links.

## 10. Scientific guardrails

- A detector image's `IMAGE` values are surface brightness, not automatically source flux.
- Level 2 `IMAGE` has not had zodiacal light subtracted; `ZODI` is a separate model layer.
- The All-Sky Cube is zodiacal-subtracted but is not time resolved.
- `SOURCE` is a source-location mask flag, not automatically a bad-pixel flag.
- Quality flags must be interpreted bitwise using the official flag definitions.
- A change in pixel value can be caused by wavelength, PSF, background, detector position, or quality—not only astrophysical variability.
- Report uncertainty and limitations; a non-detection is not proof of no motion.

## 11. Official references

- NASA Space Apps Challenge 2026 — Planet X and SPHEREx: https://www.spaceappschallenge.org/2026/
- SPHEREx DR1 overview: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html
- SPHEREx data releases: https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-releases/
- SPHEREx data products: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/
- SPHEREx data access: https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/
- SPHEREx Explanatory Supplement v2.1: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf

## 12. Project statement

**orbitalQ turns the SPHEREx archive into a target-centred, time-aware exploration experience. It helps people inspect real infrared observations, understand what changed, and trace every visual result back to the data that produced it.**
