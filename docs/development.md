# Development and release guide

## Environments

The application and tests use `requirements.txt`. The static viewer build has
its own dependency set in `requirements-viewer.txt` because it needs archive
validation, FITS reprojection, and HTML packaging but does not need Streamlit.
Keep these files explicit: importing a package in a script requires that
package to be declared in the dependency set used to run that script.

Create a clean environment when diagnosing installation problems:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

## Software checks

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q app.py core tests study/scripts scripts build_viewer.py
```

The tests are deterministic. They exercise WCS scalar handling, bounded
cutouts, archive URL/header parsing, FITS metadata extraction, chronological
ordering, comparison safeguards, and provenance formatting. They do not
assert that a remote archive endpoint is available.

## Streamlit application

```bash
.venv/bin/streamlit run app.py
```

The public archive is an input, not a dependency required for the app to
start. Network failures should be reported as unavailable access; they must
not be converted into claims that a target has no observations.

## Static viewer build

The Vercel entry point is `scripts/build-vercel.mjs`. It copies the static
assets, creates an isolated temporary Python environment, installs
`requirements-viewer.txt`, and runs the bounded validation/build workflow.
The Python builder is [build_viewer.py](../build_viewer.py). It consumes
validated FITS manifests, checks detector and unit consistency, reprojects
frames onto a common WCS, and embeds display images plus provenance into
`dist/index.html`.

```bash
node scripts/build-vercel.mjs
```

The build is intentionally conservative: it must not fabricate observations
when retrieval fails. A previously packaged viewer may remain available as a
deployment fallback, but the build log must make that fallback visible.

## Research scripts

Research scripts live under [study/scripts/](../study/scripts/) and are not
application startup dependencies. Run them only when the study requires a
bounded archive query or header sample. Record the source URL/object key,
release, processing version, observation identifier, retrieval date, and
limitations with any derived result. See [study/README.md](../study/README.md).

## Change discipline

- Keep reusable scientific behavior in `core/` so it can be tested without
  Streamlit.
- Keep UI composition in `app.py` and `ui/`; do not hide archive or scientific
  policy inside presentation code.
- Add or update deterministic tests when changing WCS, FITS, comparison, or
  provenance behavior.
- Preserve the distinction between spectral channels and temporal visits.
- Do not call a visual difference a detection, motion measurement, or
  variability result without the required calibration and validation steps.
