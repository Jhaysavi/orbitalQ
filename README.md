# orbitalQ — Explore the Changing Infrared Universe

orbitalQ is a lightweight Streamlit application for exploring genuine
NASA/IPAC IRSA SPHEREx data. It separates a fast All-Sky Cube preview from a
time-ordered viewer for Level 2 Spectral Image FITS observations.

The application is exploratory: a visible change is not a discovery claim.
Any candidate motion or variability needs WCS registration, compatible
wavelengths, quality masks, uncertainty estimates, PSF/background checks and
independent validation.

## Run the application

Use the existing virtual environment when available. From the repository
root:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

The app can display a small real SPHEREx DR1 All-Sky Cube cutout from the
public cloud object and can load genuine Level 2 MEF FITS files from upload or
the local cache. It reads observation metadata from FITS headers, including
`DATE-OBS`, `MJD-OBS`, `OBSID`, detector, units, WCS, `FLAGS` and `VARIANCE`.
No synthetic image is substituted when retrieval fails.

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
| `app.py` | Streamlit user interface |
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
