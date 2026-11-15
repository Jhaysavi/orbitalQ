# orbitalQ — Explore the Changing Infrared Universe

Runnable Streamlit MVP for inspecting genuine NASA/IPAC IRSA SPHEREx data.

## Run

Use the existing environment; it is not necessary to recreate it:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

The **Real DR1 sky preview** reads a small section of the public SPHEREx DR1
All-Sky Cube through the verified public S3 URL. Its 102 planes are wavelengths,
not dates. The **Compare Level 2 visits** tab accepts genuine Level 2 MEF FITS
files, extracts a target-centred WCS cutout, reads `DATE-OBS`, `MJD-OBS`,
`OBSID`, detector, release, processing version, units, `FLAGS` and `VARIANCE`,
and sorts by actual observation time. It never substitutes a synthetic image
when archive access fails.

The current archive route for Level 2 is an upload/cached-file workflow. The
repository contains preserved DR1/QR3 inventories and research scripts for
future small, provenance-preserving archive discovery; no full survey scan is
performed by the app.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests use a small FITS fixture to exercise metadata and WCS parsing. Archive
availability must be checked separately because public endpoints can be
temporarily unavailable. See [README_ORBITALQ.md](README_ORBITALQ.md) for the
project’s existing scientific rationale and official references.
