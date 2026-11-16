"""Visual assets and display components for the Streamlit explorer."""

import io
from base64 import b64encode
from html import escape
from pathlib import Path
from string import Template

import matplotlib.pyplot as plt
import streamlit as st
import streamlit.components.v1 as components

UI_DIR = Path(__file__).resolve().parent
LOGO_PATH = UI_DIR.parent / "orbitalq-logo.png"
FAVICON_PATH = UI_DIR.parent / "favicon.png"
HERO_FITS = "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W35_1A/l2b-v27-2026-230/1/level2_2025W35_1A_0432_4D1_spx_l2b-v27-2026-230.fits"
HERO_SOURCE = "https://github.com/ayoubna99/spherex-skyshift/blob/170e23075e88f27b10d1a1092c4147644386f6bf/frontend/static/frames_barnard.json"


@st.cache_data(show_spinner=False)
def read_assets():
    """Read packaged assets without depending on internet access."""
    return (
        (UI_DIR / "explorer.css").read_text(encoding="utf-8"),
        b64encode((UI_DIR / "barnard-dr1.png").read_bytes()).decode("ascii"),
        (UI_DIR / "swipe.html").read_text(encoding="utf-8"),
        b64encode(LOGO_PATH.read_bytes()).decode("ascii"),
    )


def render_brand():
    css, _, _, logo = read_assets()
    st.markdown(f"""
<style>{css}</style>
<div class="oq-brand">
  <img src="data:image/png;base64,{logo}" width="46" height="46" alt="">
  <div><strong>Orbital<span>Q</span></strong><small>SPHEREx observation explorer</small></div>
</div>
""", unsafe_allow_html=True)


def render_hero_observation():
    _, preview, _, _ = read_assets()
    st.markdown(f"""
<figure class="oq-hero-image">
  <div class="oq-figure-bar"><span>Barnard’s Star</span><span>SPHEREx / D1</span></div>
  <div class="oq-figure-image">
    <img src="data:image/png;base64,{preview}" alt="Infrared observation of the field around Barnard’s Star">
  </div>
  <figcaption>
    <time datetime="2025-08-27">27 AUG 2025 · UTC</time>
    <a href="{HERO_FITS}">FITS exposure ↗</a>
    <a href="{HERO_SOURCE}">Preview source ↗</a>
  </figcaption>
</figure>
""", unsafe_allow_html=True)


def _encode_cutout(data, limits):
    buffer = io.BytesIO()
    plt.imsave(
        buffer, data, format="png", origin="lower", cmap="inferno",
        vmin=limits[0], vmax=limits[1],
    )
    return b64encode(buffer.getvalue()).decode("ascii")


def display_swipe(first, second, stretch_limits):
    """Overlay equal-sized native cutouts with a browser-side divider."""
    _, _, markup, _ = read_assets()
    height, width = first.image.shape
    chronological = first.mjd_obs < second.mjd_obs
    components.html(
        Template(markup).substitute(
            width=width,
            height=height,
            max_width=f"{360 * width / height:.2f}",
            label_a="Earlier" if chronological else "Observation A",
            label_b="Later" if chronological else "Observation B",
            date_a=escape(first.date_obs or "Date unavailable"),
            date_b=escape(second.date_obs or "Date unavailable"),
            image_a=_encode_cutout(first.image, stretch_limits),
            image_b=_encode_cutout(second.image, stretch_limits),
        ),
        height=485,
    )
