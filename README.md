# OrbitalQ — Explore the Changing Infrared Universe

OrbitalQ is a lightweight Streamlit application for exploring genuine
NASA/IPAC IRSA SPHEREx data. It separates a fast All-Sky Cube preview from a
time-ordered viewer for Level 2 Spectral Image FITS observations.

The application is exploratory: a visible change is not a discovery claim.
Any candidate motion or variability needs WCS registration, compatible
wavelengths, quality masks, uncertainty estimates, PSF/background checks and
independent validation.

## Run the application

From the repository root (Python 3.10 or later):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

The app can display a small real SPHEREx DR1 All-Sky Cube cutout from the
public cloud object, resolve an object name when the configured name service
can resolve it, and browse bounded directory listings from the public SPHEREx
S3 archive. Browsing is by release, planning period, processing run and
detector; it is not presented as a complete coordinate search. Selected remote
FITS files pass an actual WCS check before their cutouts are loaded. The app
also offers a one-click sequence of two genuine DR1 observations at a clearly
identified example field. This visual example is not WISE 0855 and does not
claim astrophysical variability.

In the **Compare Level 2 visits** tab, use the public S3 browser, load the
verified example sequence, paste a public FITS URL, or upload genuine Level 2
MEF files. The app reads `DATE-OBS`, `MJD-OBS`, `OBSID`, detector, units, WCS,
`FLAGS` and `VARIANCE`; no synthetic image or coverage claim is substituted
when retrieval fails. Before/after and blink views use a shared image stretch,
but remain visual aids rather than scientific difference measurements.
Streamlit caches successful remote cutouts and archive listings in-process;
uploaded FITS files and local caches are not committed.

## Streamlit Community Cloud

1. Push the prepared repository to a GitHub branch you control.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Create
   app**, select the repository and branch, and set the main file to `app.py`
   at the repository root.
3. In **Advanced settings**, choose Python 3.10 or later, then deploy. Cloud
   installs the runtime dependencies from `requirements.txt`.
4. No secrets or credentials are required. Do not add local FITS files,
   `.env` files, or `.streamlit/secrets.toml` to Git.

The app accesses the public SPHEREx S3 archive over HTTPS. If remote browsing
or file access is unavailable, the app reports the error and local FITS
uploads remain available. Community Cloud storage is ephemeral; its cache is
not a durable archive.

## Tests and checks

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q app.py core tests study/scripts
```

The unit tests are in [tests/](./tests/). Network archive probes and research
scripts are intentionally not part of the automated test suite; see
[study/](./study/) for their inputs, outputs and limitations.

## Repository map

| Path | Purpose |
| --- | --- |
| `app.py` | Streamlit views, archive controls and observation workflow |
| `ui/` | [Streamlit presentation components and preview assets](docs/interface.md) |
| `core/` | WCS, FITS, provenance and scientific validation helpers |
| `config/` | Target presets and other small, reviewable configuration |
| `data/` | Local cutouts, previews, manifests and cache placeholders |
| `tests/` | Fast deterministic unit tests |
| `study/scripts/` | Archive experiments, inventory tools and coordinate studies |
| `study/results/` | Generated study tables and saved archive responses |
| `scripts/` | Reusable retrieval/deployment utilities |
| `docs/` | Scientific method, source references and maintenance notes |

Large inventories, FITS files, caches and generated study products stay local
and are ignored by Git. Their provenance should be recorded in a manifest or
in the study notes rather than committed to the repository.

## Scientific data policy

- Use SPHEREx **DR1** for Surveys 1–2 and **QR3** for Surveys 3–4. DR1 and
  QR3 supersede QR2 for new work.
- The All-Sky Cube has 102 nominal spectral channels. Those channels are
  wavelengths, not observation dates.
- Temporal ordering uses separate Level 2 observations and their actual
  `DATE-OBS`, `MJD-OBS` and `OBSID` metadata.
- Comparisons must check wavelength/bandpass compatibility, detector and
  processing version, WCS alignment, `FLAGS`, `VARIANCE`, PSF/ePSF and
  background/calibration differences.
- Target coordinates with proper motion must be propagated to the observation
  epoch when reference astrometry is available. The challenge coordinate for
  WISE 0855 is not silently treated as valid at every epoch.

Read [docs/scientific-methods.md](./docs/scientific-methods.md) for the full
method and source list, and [study/README.md](./study/README.md) for the
research scripts, including
[sample_dr1_period_dates.py](./study/scripts/sample_dr1_period_dates.py).
The older project brief remains available in
[README_ORBITALQ.md](./README_ORBITALQ.md), and the original retrieval notes
in [README-MILESTONE-01.md](./README-MILESTONE-01.md).
