# Streamlit interface

**Home** introduces OrbitalQ and walks through a first observation. **Solution** opens the explorer. **Team** links to the project team’s portfolios, **Documentation** covers references and the delivery and research plans, and **About** describes the technical approach.

Inside Solution, **Compare visits** opens the packaged Barnard’s Star and WISE 0855 sequences. **Spectral preview** displays the DR1 All-Sky Cube by wavelength. The **FITS workspace** accepts public archive URLs and uploaded Level 2 observations, and includes a two-exposure DR1 example. Target coordinates and display settings appear next to the spectral and FITS workspaces.

- **Swipe** uses the same color stretch for both native cutouts. It is available when both contain valid pixels and have matching dimensions and image units. The **Auto-Blink A/B** button in Swipe alternates the two real images until paused. The comparison shows the elapsed time when both visits have valid MJD-OBS values.
- **Blink** switches between observations. **Before / after** places the images side by side.
- The observation timeline, quality metadata, and provenance exports remain available beneath the comparison.

The hero uses the packaged Barnard’s Star cutout already distributed with the static viewer. It is a separate field from the built-in Level 2 example. The [original SPHEREx FITS exposure](https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W35_1A/l2b-v27-2026-230/1/level2_2025W35_1A_0432_4D1_spx_l2b-v27-2026-230.fits) is from NASA/IPAC IRSA. The processed preview comes from SPHEREx SkyShift (Ayoub, Abdou, Ilyes). Its [MIT license](../dist/licenses/skyshift.txt) is included in this repository.

Presentation code and assets are in [`ui/`](../ui/). [`app.py`](../app.py) handles Streamlit controls, archive selection, and analysis views. Scientific helpers remain in [`core/`](../core/).

The root [HTML prototype](../viewer.html) uses illustrative observations for design exploration. The [static viewer](../dist/index.html) packages real observations in its case-data script. The builder replaces that script with data from validated FITS manifests.

### External study resources

The WISE 0855 study links to a [Pan-STARRS optical cutout](https://ps1images.stsci.edu/cgi-bin/ps1cutouts?pos=133.786245+-7.244372&filter=color&filter=g&filter=r&filter=i&filter=z&filter=y&filetypes=stack&auxiliary=data&size=240&output_size=0&verbose=0&autoscale=99.500000&catlist=) from STScI and to [WiseView](https://byw.tools/wiseview) from Backyard Worlds. In WiseView, enter RA `133.786245` and Dec `-7.244372` to examine the reference field. These external views provide context for the SPHEREx observations. The app keeps data from each survey separate.

### Compare visits

The comparison workspace reads the packaged Barnard’s Star and WISE 0855 cutouts from the repository, then shows their visit dates, elapsed time, Swipe and Auto-Blink controls, and FITS provenance. Comparing the packaged visits requires no remote FITS download. The example renderer and the observation interval are implemented directly in `app.py`.

**Time-lapse** offers playback, speed, previous and next controls, and direct jumps using the date buttons or slider. Playback spends equal screen time on each visit and repeats by default. Turn off **Loop** to stop at the final visit. The player shows the real time elapsed since the first visit. The packaged examples use their stored images. The Level 2 workspace can also play uploaded or archive-loaded visits with distinct timestamps and matching detector, units, and cutout dimensions. The view uses a shared display stretch and native pixel grids.
