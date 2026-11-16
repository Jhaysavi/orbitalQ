# orbitalQ — Explore the changing infrared sky

orbitalQ is a public-facing Streamlit application for exploring real NASA/IPAC
SPHEREx observations. It combines a fast DR1 All-Sky Cube preview with a
time-aware workspace for Level 2 Spectral Image FITS observations.

The project is an inspection and education tool, not a discovery pipeline. A
visual change is only a candidate signal: scientific interpretation requires
epoch-aware coordinates, WCS registration, compatible bandpasses and
detectors, quality masks, uncertainty estimates, PSF/background checks, and
independent validation.

## What the application does

- Accepts a target preset or ICRS right ascension and declination.
- Shows a real SPHEREx All-Sky Cube cutout and labels its spectral channel
  correctly. Spectral channels are wavelengths, not observation dates.
- Browses bounded public DR1 and QR3 Level 2 archive prefixes.
- Reads uploaded or public Level 2 MEF FITS files, validates their celestial
  WCS, and extracts target-centred cutouts.
- Orders visits by `MJD-OBS`/`DATE-OBS` and exposes detector, release, units,
  wavelength metadata, `FLAGS`, `VARIANCE`, and provenance.
- Provides blink, side-by-side, and shared-stretch visual comparisons without
  presenting them as calibrated difference measurements.
- Produces a provenance-oriented Markdown report for reproducibility.

## Quick start

Python 3.10 or newer is supported. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

The app needs no credentials. It reads public archive data over HTTPS when
network access is available; uploaded FITS files remain available when the
archive cannot be reached. Remote data are cached only in the running process
and are not a durable archive.

## Verification and builds

Run the deterministic software checks with the same interpreter used for the
application:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q app.py core tests study/scripts scripts build_viewer.py
```

The static comparison viewer is built for Vercel with:

```bash
node scripts/build-vercel.mjs
```

That build uses `requirements-viewer.txt`, validates a bounded real-data
sample when the archive is reachable, and updates the packaged case data only
when validation and manifest generation succeed. If the archive is
temporarily unavailable, the script keeps the already-packaged viewer and
reports the fallback; this is an availability fallback, not a scientific
result.

For local development, see [docs/development.md](./docs/development.md).

## Scientific basis and limitations

SPHEREx DR1 and QR3 are the supported releases for new work. DR1’s All-Sky
Cube contains 102 spectral planes; those planes describe wavelength channels,
not a time series. Temporal comparisons use separate Level 2 observations and
their actual observation metadata.

Level 2 `IMAGE` values are calibrated surface brightness. `ZODI` is a
separate zodiacal-light model, while `FLAGS`, `VARIANCE`, `EPSF`, and
`WCS-WAVE` require product-specific interpretation. A target coordinate with
proper motion must be propagated from a stated astrometric reference epoch;
the WISE 0855 challenge coordinate is intentionally not treated as valid at
every epoch.

Read [docs/scientific-methods.md](./docs/scientific-methods.md) for the data
model, comparison safeguards, references, and study methodology.

## Repository guide

| Path | Role |
| --- | --- |
| [app.py](./app.py) | Streamlit entry point and application workflow |
| [core/](./core/) | Reusable archive, FITS, WCS, validation, and provenance logic |
| [ui/](./ui/) | Presentation components and interface assets |
| [config/](./config/) | Reviewed target presets |
| [tests/](./tests/) | Deterministic unit tests that do not require the live archive |
| [study/](./study/) | Preserved exploratory scripts, results, and research notes |
| [scripts/](./scripts/) | Reusable retrieval and deployment utilities |
| [docs/](./docs/) | Scientific method, interface, structure, and development documentation |
| [dist/](./dist/) | Static viewer published by the Vercel build |

The research material in [study/README.md](./study/README.md) is retained as
evidence of the project’s data investigation. Generated FITS files, caches,
inventories, and virtual environments are intentionally excluded from source
control.

## Sources and attribution

The project uses public NASA/IPAC IRSA SPHEREx data and follows the official
SPHEREx data-product documentation. The full source list and publication
acknowledgement guidance are in
[docs/scientific-methods.md](./docs/scientific-methods.md). The packaged
static viewer also retains its third-party SkyShift license in
[dist/licenses/skyshift.txt](./dist/licenses/skyshift.txt).
