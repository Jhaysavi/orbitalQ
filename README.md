# Orbital Eye

An observation viewer for **Planet X and SPHEREx**, NASA Space Apps Challenge 2026. Compare two real SPHEREx images of the same sky field, inspect the expected target position and open the original FITS.

## Generate the viewer

Use Python 3.11 or 3.12 in a virtual environment.

```powershell
python -m pip install -r requirements-viewer.txt
python validate_spherex.py --target Barnard --ra 269.4515 --dec 4.769 --bandpass SPHEREx-D1 --size 0.08 --max-downloads 8
python build_viewer.py --barnard data/inventory/Barnard_manifest.json
```

Open `dist/index.html` in your browser. The output embeds its image frames and works offline after generation. For a public demo, serve it from any static host. Start with the earliest and latest frames, switch to **Side by side**, then use **Expected position** to locate the target.

### Add WISE 0855

```powershell
python validate_spherex.py --target "WISE 0855" --ra 133.761 --dec -7.242 --bandpass SPHEREx-D6 --size 0.10 --max-downloads 8
python build_viewer.py --barnard data/inventory/Barnard_manifest.json --wise-0855 data/inventory/WISE_0855_manifest.json
```

The wider field is centered near the target's approximate SPHEREx-era position. To try D5, use a different target label during retrieval so that the D6 manifest is preserved. Add `?target=wise_0855` to a hosted viewer link to open that field directly.

## Read the evidence

- Each case needs at least two distinct IRSA observation times with overlapping image coverage. If the dates are too close for visible motion, inspect the inventory CSV and choose observations further apart before presenting the result.
- The builder reprojects the FITS IMAGE extension to a common WCS grid and applies one display stretch per case. The display is for visual comparison. Filter flags, bandpass variation, PSF, uncertainties and parallax need separate treatment for scientific measurements.
- The overlay is an approximate catalog position propagated with proper motion. A marker or a downloaded image alone does not establish detection. Report WISE 0855 as inconclusive if the images do not clearly support identification.
- Original data and timestamps come from NASA/IPAC IRSA. [Data documentation](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/) and [retrieval milestone](README-MILESTONE-01.md).
