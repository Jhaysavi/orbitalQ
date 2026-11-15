# Streamlit interface

The interface starts with Level 2 observations. **Load real example** opens the two archive files listed in `app.py`. After loading, the comparison appears above the file controls and observation metadata. **DR1 sky preview** opens the remote spectral cube on demand.

- **Swipe** uses the same color stretch for both native cutouts. It is available when both contain valid pixels and have matching dimensions and image units.
- **Blink** switches between observations. **Before / after** places the images side by side.
- The observation timeline, quality metadata, and provenance exports remain available beneath the comparison.

The hero uses the packaged Barnard’s Star cutout already distributed with the static viewer. It is a separate field from the built-in Level 2 example. The [original SPHEREx FITS exposure](https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W35_1A/l2b-v27-2026-230/1/level2_2025W35_1A_0432_4D1_spx_l2b-v27-2026-230.fits) is from NASA/IPAC IRSA. The [processed preview](https://github.com/ayoubna99/spherex-skyshift/blob/170e23075e88f27b10d1a1092c4147644386f6bf/frontend/static/frames_barnard.json) comes from SPHEREx SkyShift (Ayoub, Abdou, Ilyes). Its [MIT license](../dist/licenses/skyshift.txt) is included in this repository.

Presentation code and assets are in [`ui/`](../ui/). [`app.py`](../app.py) handles Streamlit controls, archive selection, and analysis views. Scientific helpers remain in [`core/`](../core/).
