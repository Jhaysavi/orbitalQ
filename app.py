import io
import json
from pathlib import Path
import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS

from core.coordinates import is_inside_image, world_to_pixel_one
from core.fits_reader import read_level2
from core.provenance import report_text
from core.validation import chronological, comparison_warning

st.set_page_config(page_title="orbitalQ | SPHEREx Explorer", page_icon="🌌", layout="wide")

st.title("orbitalQ")
st.caption("Explore the infrared sky with real NASA SPHEREx data.")

CUBE_URL = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/hips5_cube/hips_20261026/Norder5/Dir10000/Npix10226_cube.fits"
)

TARGET_PRESETS = json.loads((Path(__file__).parent / "config" / "targets.json").read_text())

with st.sidebar:
    st.header("Target coordinates")
    known_presets = [name for name, values in TARGET_PRESETS.items() if values.get("ra_deg") is not None]
    preset = st.selectbox("Target preset", ["Custom"] + known_presets)
    preset_values = TARGET_PRESETS.get(preset, {})
    if preset != "Custom" and preset_values.get("ra_deg") is None:
        st.info("This target is preserved in the research inventory, but no reliable coordinates are configured yet.")
    ra = st.number_input("Right ascension (degrees)", min_value=0.0, max_value=360.0,
                         value=float(preset_values.get("ra_deg") or 133.795129), format="%.6f")
    dec = st.number_input("Declination (degrees)", min_value=-90.0, max_value=90.0,
                          value=float(preset_values.get("dec_deg") if preset_values.get("dec_deg") is not None else -7.245147), format="%.6f")
    cutout_size = st.select_slider("Cutout width (pixels)", options=[21, 31, 41, 51, 71, 101],
                                   value=51)
    st.caption("Default coordinates: WISE 0855−0714 challenge position. No reference epoch is specified.")

target = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")


@st.cache_resource(show_spinner="Connecting to the public SPHEREx DR1 cube…")
def open_public_cube():
    # FITS is accessed through fsspec so image sections can be fetched by byte range.
    return fits.open(
        CUBE_URL,
        use_fsspec=True,
        fsspec_kwargs={"block_size": 1024 * 1024},
    )


def display_array(data, title, marker=None):
    data = np.asarray(data, dtype=float)
    finite = np.isfinite(data)
    if not finite.any():
        st.warning("No finite image pixels in this cutout.")
        return
    lo, hi = np.nanpercentile(data[finite], [2, 98])
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        lo = float(np.nanmin(data[finite]))
        hi = float(np.nanmax(data[finite])) if np.nanmax(data[finite]) > lo else lo + 1
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(data, origin="lower", cmap="inferno", vmin=lo, vmax=hi)
    if marker is not None:
        ax.plot(marker[0], marker[1], marker="+", color="cyan", markersize=14, mew=2)
    ax.set_title(title)
    ax.set_xlabel("Cutout X (pixel)")
    ax.set_ylabel("Cutout Y (pixel)")
    fig.colorbar(im, ax=ax, label="MJy/sr")
    fig.tight_layout()
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


tab_cube, tab_visits, tab_about = st.tabs(
    ["Real DR1 sky preview", "Compare Level 2 visits", "About orbitalQ"]
)

with tab_cube:
    st.subheader("SPHEREx DR1 All-Sky Cube")
    st.info(
        "This is a real SPHEREx DR1 product. Its 102 planes are wavelength channels, "
        "not observation dates. Use the second tab for a sequence of separate Level 2 visits."
    )
    plane = st.slider("Spectral plane", min_value=1, max_value=102, value=17)
    try:
        hdul = open_public_cube()
        image_hdu = hdul["IMAGE"]
        cube_wcs = WCS(image_hdu.header, fobj=hdul).celestial
        # Astropy may return one-element NumPy arrays here. Convert exactly one
        # coordinate to a Python float before bounds checks, round(), or indexing.
        x, y = world_to_pixel_one(cube_wcs, target)

        if not is_inside_image(x, y, image_hdu.header["NAXIS1"], image_hdu.header["NAXIS2"]):
            st.warning(
                "The current built-in tile does not contain these coordinates. "
                "The first prototype is preconfigured for the WISE 0855−0714 tile."
            )
        elif plane in (51, 52):
            st.warning("This is a documented blank channel adjacent to the dichroic split.")
        else:
            half = cutout_size // 2
            x0 = max(0, int(round(x)) - half)
            y0 = max(0, int(round(y)) - half)
            x1 = min(image_hdu.header["NAXIS1"], x0 + cutout_size)
            y1 = min(image_hdu.header["NAXIS2"], y0 + cutout_size)
            x0 = max(0, x1 - cutout_size)
            y0 = max(0, y1 - cutout_size)
            # FITS cube Python array order is [spectral_plane, y, x].
            image = np.asarray(
                image_hdu.section[plane - 1, y0:y1, x0:x1], dtype=float
            )
            nhits = np.asarray(
                hdul["NHITS"].section[plane - 1, y0:y1, x0:x1], dtype=float
            )
            flags = np.asarray(
                hdul["FLAGS"].section[plane - 1, y0:y1, x0:x1], dtype=np.int64
            )

            channel_table = hdul["SPECTRAL_CHANNELS"].data
            channel = channel_table[plane - 1]
            wavelength = float(channel["WAVELENGTH"])
            detector = str(channel["DETECTOR"]).strip()
            subchannel = int(channel["SUBCHAN"])
            cx, cy = x - x0, y - y0

            m1, m2, m3 = st.columns(3)
            m1.metric("Wavelength", f"{wavelength:.3f} µm")
            m2.metric("Detector", f"{detector} · channel {subchannel}")
            centre_hits = int(nhits[int(round(cy)), int(round(cx))])
            m3.metric("Centre NHITS", str(centre_hits))

            display_array(
                image,
                f"WISE 0855−0714 field · plane {plane} · {wavelength:.3f} µm",
                marker=(cx, cy),
            )

            finite = np.isfinite(image)
            if finite.any():
                st.write(
                    f"Cutout median: **{np.nanmedian(image):.5g} MJy/sr** · "
                    f"Valid pixels: **{int(finite.sum())}/{image.size}** · "
                    f"Centre pixel: **{image[int(round(cy)), int(round(cx))]:.5g} MJy/sr**"
                )
            st.caption(
                f"Cube pixel: ({x:.2f}, {y:.2f}) · Tile: Npix10226 · "
                "Cube values are zodiacal-subtracted surface brightness. "
                "This is a spectral preview, not a time-series measurement."
            )
            st.caption(f"Provenance: SPHEREx DR1 All-Sky Cube · {CUBE_URL}")
            with st.expander("Quality flags in this cutout"):
                values, counts = np.unique(flags, return_counts=True)
                st.dataframe(
                    {"flag_value": values.astype(int), "pixel_count": counts},
                    use_container_width=True,
                    hide_index=True,
                )
    except Exception as exc:
        st.error(f"Could not load the remote cube: {exc}")
        st.write(
            "Check your internet connection and the public S3 endpoint. "
            "The app reads a small cutout from the remote FITS cube; it is not intended "
            "to download the entire 306 MB tile."
        )

with tab_visits:
    st.subheader("Chronological Level 2 image viewer")
    st.write(
        "Upload two or more SPHEREx Level 2 MEF FITS files. orbitalQ extracts the "
        "same sky-coordinate cutout from each file using its own WCS and orders the "
        "frames by DATE-OBS."
    )
    st.warning(
        "This first viewer is for visual inspection only. Before interpreting brightness "
        "differences, observations must be matched in wavelength and PSF and checked "
        "using FLAGS and VARIANCE. A fixed coordinate is used here; high-proper-motion "
        "targets need epoch propagation."
    )
    uploads = st.file_uploader(
        "Upload Level 2 FITS files (same target; ideally same detector)",
        type=["fits", "fit"],
        accept_multiple_files=True,
    )

    if uploads:
        frames = []
        errors = []
        for uploaded in uploads:
            try:
                frames.append(read_level2(
                    io.BytesIO(uploaded.getvalue()), target, cutout_size, uploaded.name,
                    source_url=f"uploaded:{uploaded.name}",
                ))
            except Exception as exc:
                errors.append(f"{uploaded.name}: {exc}")

        frames = chronological(frames)

        if errors:
            with st.expander(f"Files not displayed ({len(errors)})"):
                for error in errors:
                    st.write("• " + error)

        if frames:
            st.success(f"{len(frames)} image(s) cover the selected coordinates.")
            if len({frame.detector for frame in frames}) > 1:
                st.warning(
                    "These files contain multiple detectors. Do not interpret their "
                    "brightness as a temporal light curve; detector bands differ."
                )
            labels = [
                f"{i + 1}. {f.date_obs or 'date unavailable'} · D{f.detector or '?'} · {f.obsid or 'OBSID unavailable'}"
                for i, f in enumerate(frames)
            ]
            selected = st.select_slider(
                "Observation frame", options=list(range(len(frames))),
                format_func=lambda i: labels[i],
            )
            frame = frames[selected]
            a, b, c = st.columns(3)
            a.metric("DATE-OBS", frame.date_obs or "not in header")
            b.metric("Detector", frame.detector or "unknown")
            c.metric("OBSID", frame.obsid or "not in header")
            display_array(
                frame.image,
                f"{frame.filename} · {frame.bunit}",
                marker=(frame.image.shape[1] // 2, frame.image.shape[0] // 2),
            )
            st.caption(
                f"Target pixel in original image: ({frame.pixel_x:.2f}, "
                f"{frame.pixel_y:.2f}) · MJD-OBS: {frame.mjd_obs} · "
                f"Release: {frame.release} · Processing: {frame.processing_version} · "
                f"Wavelength: {frame.wavelength}"
            )
            if len(frames) > 1:
                st.write("**Available visit sequence**")
                st.dataframe(
                    [{
                        "date_obs": f.date_obs, "mjd_obs": f.mjd_obs,
                        "detector": f.detector, "obsid": f.obsid,
                        "wavelength": f.wavelength, "release": f.release,
                        "filename": f.filename,
                    } for f in frames],
                    use_container_width=True,
                    hide_index=True,
                )
            if len(frames) > 1:
                compare_index = st.selectbox(
                    "Compare selected frame with",
                    options=[i for i in range(len(frames)) if i != selected],
                    format_func=lambda i: labels[i],
                )
                warning = comparison_warning(frame, frames[compare_index])
                if warning:
                    st.warning(f"Comparison separated: {warning}. No difference image is shown.")
                else:
                    st.info("Metadata are compatible enough for visual comparison; WCS registration and PSF matching are still required before scientific differencing.")
                left, right = st.columns(2)
                with left:
                    display_array(frame.image, f"Before/selected · {frame.date_obs}")
                with right:
                    display_array(frames[compare_index].image, f"After/comparison · {frames[compare_index].date_obs}")
                st.download_button(
                    "Download provenance report",
                    report_text(preset if preset != "Custom" else "custom target", ra, dec, frames),
                    file_name="orbitalq_discovery_report.md",
                    mime="text/markdown",
                )
        elif not errors:
            st.info("Upload Level 2 FITS files to begin.")

with tab_about:
    st.subheader("What orbitalQ does")
    st.write(
        "orbitalQ is a target-centred interface for exploring real SPHEREx observations "
        "and investigating how the infrared sky changes over time."
    )
    st.markdown(
        """
        **Scientific rule:** spectral channels are wavelengths; observation dates come
        from separate Level 2 exposures.

        **Current prototype:** a real DR1 All-Sky Cube cutout plus a Level 2 FITS
        upload viewer. The cube preview is spectral context, not a temporal movie.

        **Next engineering milestone:** automated archive footprint search, proper-motion
        propagation, and wavelength/PSF-aware comparison of matched visits.
        """
    )
    st.markdown(
        "[SPHEREx DR1 overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html) · "
        "[Data products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/) · "
        "[Data releases](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-releases/)"
    )
