import io
import warnings

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS

st.set_page_config(page_title="orbitalQ | SPHEREx Explorer", page_icon="🌌", layout="wide")

st.title("orbitalQ")
st.caption("Explore the infrared sky with real NASA SPHEREx data.")

CUBE_URL = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/hips5_cube/hips_20261026/Norder5/Dir10000/Npix10226_cube.fits"
)

with st.sidebar:
    st.header("Target coordinates")
    ra = st.number_input("Right ascension (degrees)", min_value=0.0, max_value=360.0,
                         value=133.795129, format="%.6f")
    dec = st.number_input("Declination (degrees)", min_value=-90.0, max_value=90.0,
                          value=-7.245147, format="%.6f")
    cutout_size = st.select_slider("Cutout width (pixels)", options=[21, 31, 41, 51, 71, 101],
                                   value=51)
    st.caption("Default coordinates: WISE 0855−0714 challenge position. No reference epoch is specified.")

target = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")


def cutout_bounds(x, y, width, height, size):
    half = size // 2
    x0 = max(0, int(round(x)) - half)
    y0 = max(0, int(round(y)) - half)
    x1 = min(width, x0 + size)
    y1 = min(height, y0 + size)
    x0 = max(0, x1 - size)
    y0 = max(0, y1 - size)
    return x0, x1, y0, y1


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
        x, y = cube_wcs.world_to_pixel(target)

        if not np.isfinite(x) or not np.isfinite(y):
            st.error("These coordinates could not be projected into the selected cube tile.")
        elif not (0 <= x < image_hdu.header["NAXIS1"] and
                  0 <= y < image_hdu.header["NAXIS2"]):
            st.warning(
                "The current built-in tile does not contain these coordinates. "
                "The first prototype is preconfigured for the WISE 0855−0714 tile."
            )
        elif plane in (51, 52):
            st.warning("This is a documented blank channel adjacent to the dichroic split.")
        else:
            x0, x1, y0, y1 = cutout_bounds(
                x, y, image_hdu.header["NAXIS1"], image_hdu.header["NAXIS2"], cutout_size
            )
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
                with fits.open(io.BytesIO(uploaded.getvalue()), memmap=False) as hdul:
                    if "IMAGE" not in hdul:
                        raise ValueError("No IMAGE extension found")
                    image_hdu = hdul["IMAGE"]
                    header = image_hdu.header.copy()
                    image = np.asarray(image_hdu.data, dtype=float)
                    w = WCS(header).celestial
                    px, py = w.world_to_pixel(target)

                    if not np.isfinite(px) or not np.isfinite(py):
                        raise ValueError("WCS could not project target coordinates")
                    ny, nx = image.shape
                    if not (0 <= px < nx and 0 <= py < ny):
                        raise ValueError("Target is outside this image footprint")

                    x0, x1, y0, y1 = cutout_bounds(px, py, nx, ny, cutout_size)
                    patch = image[y0:y1, x0:x1]
                    date_obs = header.get("DATE-OBS", hdul[0].header.get("DATE-OBS", ""))
                    mjd_obs = header.get("MJD-OBS", hdul[0].header.get("MJD-OBS", np.nan))
                    obsid = header.get("OBSID", hdul[0].header.get("OBSID", ""))
                    detector = header.get("DETECTOR", hdul[0].header.get("DETECTOR", ""))
                    bunit = header.get("BUNIT", "unknown")
                    frames.append({
                        "name": uploaded.name,
                        "date": str(date_obs),
                        "mjd": float(mjd_obs) if mjd_obs not in ("", None) else np.nan,
                        "obsid": str(obsid),
                        "detector": str(detector),
                        "bunit": str(bunit),
                        "patch": patch,
                        "pixel_x": float(px),
                        "pixel_y": float(py),
                    })
            except Exception as exc:
                errors.append(f"{uploaded.name}: {exc}")

        frames.sort(key=lambda item: item["mjd"] if np.isfinite(item["mjd"]) else float("inf"))

        if errors:
            with st.expander(f"Files not displayed ({len(errors)})"):
                for error in errors:
                    st.write("• " + error)

        if frames:
            st.success(f"{len(frames)} image(s) cover the selected coordinates.")
            if len({frame["detector"] for frame in frames}) > 1:
                st.warning(
                    "These files contain multiple detectors. Do not interpret their "
                    "brightness as a temporal light curve; detector bands differ."
                )
            labels = [
                f"{i + 1}. {f['date']} · D{f['detector']} · {f['obsid']}"
                for i, f in enumerate(frames)
            ]
            selected = st.select_slider(
                "Observation frame", options=list(range(len(frames))),
                format_func=lambda i: labels[i],
            )
            frame = frames[selected]
            a, b, c = st.columns(3)
            a.metric("DATE-OBS", frame["date"] or "not in header")
            b.metric("Detector", frame["detector"] or "unknown")
            c.metric("OBSID", frame["obsid"] or "not in header")
            display_array(
                frame["patch"],
                f"{frame['name']} · {frame['bunit']}",
                marker=(frame["patch"].shape[1] // 2, frame["patch"].shape[0] // 2),
            )
            st.caption(
                f"Target pixel in original image: ({frame['pixel_x']:.2f}, "
                f"{frame['pixel_y']:.2f}) · MJD-OBS: {frame['mjd']}"
            )
            if len(frames) > 1:
                st.write("**Available visit sequence**")
                st.dataframe(
                    [{
                        "date_obs": f["date"], "mjd_obs": f["mjd"],
                        "detector": f["detector"], "obsid": f["obsid"],
                        "filename": f["name"],
                    } for f in frames],
                    use_container_width=True,
                    hide_index=True,
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
