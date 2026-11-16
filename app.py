import io
import json
import csv
from base64 import b64decode, b64encode
from html import escape
from pathlib import Path
from string import Template
from struct import unpack
import aiohttp
import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS

from core.archive import (
    is_supported_spherex_url,
    list_spherex_level2_files,
    list_spherex_prefixes,
    search_level2_footprints,
)
from core.coordinates import is_inside_image, pixel_scale_arcsec, world_to_pixel_one
from core.fits_reader import read_level2
from core.provenance import report_text
from core.validation import chronological, comparison_warning
from ui.about import REPO, render_about, render_documentation, render_wise_field_resources
from ui.presentation import FAVICON_PATH, display_swipe, render_brand, render_hero_observation

st.set_page_config(
    page_title="OrbitalQ | SPHEREx Explorer",
    page_icon=str(FAVICON_PATH),
    layout="wide",
)

CUBE_URL = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/hips5_cube/hips_20261026/Norder5/Dir10000/Npix10226_cube.fits"
)
LEVEL2_CACHE_VERSION = "level2-v2"
DEFAULT_TARGET = "WISE 0855−0714"
EXAMPLE_TARGET = "SPHEREx DR1 example field"
DEMO_FITS_URLS = (
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/level2/2025W17_4B/l2b-v27-2026-196/1/"
    "level2_2025W17_4B_0001_1D1_spx_l2b-v27-2026-196.fits",
    "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    "dr1/level2/2025W17_4B/l2b-v27-2026-196/1/"
    "level2_2025W17_4B_0001_2D1_spx_l2b-v27-2026-196.fits",
)

TARGET_PRESETS = json.loads((Path(__file__).parent / "config" / "targets.json").read_text(encoding="utf-8"))
DEMO_RA = TARGET_PRESETS[EXAMPLE_TARGET]["ra_deg"]
DEMO_DEC = TARGET_PRESETS[EXAMPLE_TARGET]["dec_deg"]


@st.cache_data(ttl=86400, show_spinner=False)
def resolve_object_name(name: str):
    """Resolve an object name through Astropy's configured name service."""
    try:
        coordinate = SkyCoord.from_name(name)
        return {"ok": True, "ra": float(coordinate.ra.deg), "dec": float(coordinate.dec.deg)}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}


def clear_resolved_target():
    st.session_state.pop("resolved_object", None)
    st.session_state.pop("resolved_object_name", None)
    st.session_state.pop("object_name_input", None)


def activate_demo_sequence():
    clear_resolved_target()
    st.session_state["target_preset"] = EXAMPLE_TARGET
    st.session_state["ra_input"] = DEMO_RA
    st.session_state["dec_input"] = DEMO_DEC
    st.session_state["demo_sequence_pending"] = True
    st.session_state["demo_sequence_active"] = True


@st.cache_data(ttl=1800, show_spinner=False)
def cached_s3_prefixes(prefix: str):
    return list_spherex_prefixes(prefix, timeout=8)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_s3_files(prefix: str, max_results: int):
    return list_spherex_level2_files(prefix, max_results=max_results, timeout=8)


SITE_PAGES = {
    "home": "Home", "solution": "Solution", "team": "Team",
    "documentation": "Documentation", "about": "About",
}
EXPLORER_VIEWS = {
    "Ready-to-view examples": "Compare visits",
    "Real DR1 sky preview": "Spectral preview",
    "Compare Level 2 visits": "FITS workspace",
    "Official archive": "Search NASA archive",
}


def select_site_page(label):
    st.session_state["site_page"] = label
    page = label.lower()
    if page == "home":
        if "page" in st.query_params:
            del st.query_params["page"]
    else:
        st.query_params["page"] = page


def launch_explorer():
    st.session_state["explorer_view"] = "Ready-to-view examples"
    select_site_page("Solution")


def render_site_navigation():
    if "site_page" not in st.session_state:
        st.session_state["site_page"] = SITE_PAGES.get(st.query_params.get("page"), "Home")
    with st.container(key="oq-navigation"):
        brand, navigation = st.columns([1, 1.6], vertical_alignment="center")
        with brand:
            render_brand()
        with navigation, st.container(
            key="oq-nav-links", horizontal=True, horizontal_alignment="right", gap="xxsmall",
        ):
            for slug, label in SITE_PAGES.items():
                st.button(
                    label, key=f"oq-nav-{slug}",
                    type="primary" if st.session_state["site_page"] == label else "tertiary",
                    on_click=select_site_page, args=(label,),
                )
    return st.session_state["site_page"]


def render_home():
    st.markdown("""
<style>
.oq-home-copy h1 { max-width:17ch; font-size:clamp(2.2rem,4.2vw,4rem); }
.oq-home-copy .oq-home-note { font-size:.8rem; color:#bcb0ca; margin-top:1rem; }
.oq-home-section { margin:2.8rem 0 1rem; }
.oq-home-section h2 { max-width:28ch; color:#f6f0ff; font-size:clamp(1.5rem,3vw,2.2rem); letter-spacing:-.035em; line-height:1.2; padding:.4rem 0; }
.oq-home-section > p { max-width:72ch; color:#c9bfd9; line-height:1.75; }
.oq-home-features { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem; margin:1.2rem 0; padding:0; list-style:none; }
.oq-home-feature { padding:1.6rem; min-width:0; border:1px solid #4d3c59; border-radius:20px; background:linear-gradient(145deg,#261b33,#15111f); }
.oq-home-feature h3 { color:#f6f0ff; font-size:1.2rem; padding:.7rem 0; }
.oq-home-feature p { color:#c9bfd9; line-height:1.7; margin:0; }
.oq-home-number { display:inline-grid; place-items:center; width:40px; height:40px; border:1px solid #80618d; border-radius:12px; background:#372340; color:#ffcf93; font:700 .9rem monospace; }
.oq-home-strip { display:flex; flex-wrap:wrap; gap:.65rem; padding:1.3rem 0; border-bottom:1px solid #41324e; }
.oq-home-strip span { color:#dacbe8; font-size:.8rem; padding:.45rem .8rem; border:1px solid #493652; border-radius:999px; }
.st-key-oq-home-cta { margin-top:2rem; padding:clamp(1.4rem,3vw,2.3rem); border:1px solid #78546f; border-radius:22px; background:linear-gradient(120deg,#3a253a,#21182e); }
.st-key-oq-home-cta h2 { color:#ffe0b7; padding:0; }
.st-key-oq-home-cta p { color:#d5c7df; }
@media(max-width:760px) { .oq-home-features { grid-template-columns:1fr; } }
</style>
""", unsafe_allow_html=True)
    with st.container(key="oq-landing"):
        intro, observation = st.columns([1.05, 1], vertical_alignment="center", gap="large")
        with intro:
            st.markdown("""
<div class="oq-home-copy">
  <p class="oq-section-label">Meet OrbitalQ · Explore real NASA SPHEREx data</p>
  <h1>The sky has a story.<br><em>Watch it unfold.</em></h1>
  <p>Turn infrared observations into a journey through time. Explore a star field, compare different visits, and follow your curiosity back to the evidence.</p>
  <p class="oq-home-note">Start with ready-to-view observations. No account needed.</p>
</div>
""", unsafe_allow_html=True)
            primary, secondary = st.columns([1.15, 1])
            primary.button("Explore the sky →", type="primary", on_click=launch_explorer, width="stretch")
            secondary.markdown('<a class="oq-how-link" href="#oq-home-details-title">See how it works ↓</a>', unsafe_allow_html=True)
        with observation:
            render_hero_observation()
            st.caption("Your starting point: the field around Barnard’s Star, observed by SPHEREx.")
    st.markdown("""
<div class="oq-home-strip" aria-label="Project highlights">
  <span>Real infrared observations</span><span>Dated visits</span><span>Original FITS source links</span><span>Built for NASA Space Apps 2026</span>
</div>
<section class="oq-home-section">
  <p class="oq-section-label">What is OrbitalQ?</p>
  <h2>A closer look at a sky that keeps changing.</h2>
  <p>OrbitalQ is an interactive explorer for NASA SPHEREx observations. It brings images, dates, and source information into one place, making it easier for curious people, students, and educators to inspect the infrared sky.</p>
  <div class="oq-home-features">
    <article class="oq-home-feature"><span class="oq-section-label">Explore time</span><h3>Return to the same field</h3><p>Play dated observations or select individual visits. Look at the target and its surroundings to investigate apparent changes.</p></article>
    <article class="oq-home-feature"><span class="oq-section-label">Compare the details</span><h3>Take a second look</h3><p>Drag the Swipe divider, zoom in, or use the crosshair. Compare two views at your own pace.</p></article>
    <article class="oq-home-feature"><span class="oq-section-label">Follow the evidence</span><h3>See where it came from</h3><p>Open the original FITS exposure and inspect dates, detectors, and quality information. Every interpretation starts with the data.</p></article>
  </div>
</section>
<section class="oq-home-section" aria-labelledby="oq-home-details-title">
  <p class="oq-section-label">Your first exploration</p>
  <h2 id="oq-home-details-title">From curious to exploring.<br>Three simple steps.</h2>
  <p>Start with Barnard’s Star, one of the ready-to-view fields. You can explore the examples before working with coordinates or uploading files.</p>
  <ol class="oq-home-features">
    <li class="oq-home-feature"><span class="oq-home-number">01</span><h3>Choose a field</h3><p>Select “Explore the sky”, then choose an available target in “Compare visits”. Each field shows the observations ready to open.</p></li>
    <li class="oq-home-feature"><span class="oq-home-number">02</span><h3>Follow the timeline</h3><p>Press Play, pause on a visit, or select a date. Switch to Swipe to compare two observations directly.</p></li>
    <li class="oq-home-feature"><span class="oq-home-number">03</span><h3>Investigate what you see</h3><p>Check surrounding stars and open the FITS source. Differences can come from motion, brightness, wavelength, or the way an image was observed.</p></li>
  </ol>
</section>
""", unsafe_allow_html=True)
    with st.expander("Do I need astronomy experience?"):
        st.write("No. Begin with the packaged fields and the visual controls. Observation details are available when you want to go deeper.")
    with st.expander("What can I explore beyond the examples?"):
        st.write("Spectral preview explores infrared wavelength channels in the built-in field. FITS workspace lets you load and compare official exposures. Search NASA archive queries a sky position; results depend on archive availability.")
    with st.expander("Does a visible difference mean a discovery?"):
        st.write("A difference is a starting point for investigation. Measuring motion or brightness requires checks for image alignment, wavelength, quality, and uncertainty. Spectral channels represent wavelengths, not dates.")
    with st.container(key="oq-home-cta"):
        copy, action = st.columns([2, 1], vertical_alignment="center")
        with copy:
            st.subheader("Your next question starts with a closer look.")
            st.write("Open the explorer and follow the first sequence.")
        action.button("Start exploring →", key="home-bottom-start", type="primary",
                      on_click=launch_explorer, width="stretch")


def render_team():
    st.markdown("""
<style>
.oq-team-hero { position:relative; overflow:hidden; padding:clamp(1.6rem,5vw,3.5rem);
    border:1px solid #514063; border-radius:24px; margin:.5rem 0 1.5rem;
    background:radial-gradient(ellipse at 100% 0%,#51336788,transparent 60%),#191321; }
.oq-team-hero:after { content:""; position:absolute; width:260px; height:260px;
    border:1px solid #dac2ff22; border-radius:50%; right:-80px; top:-110px; pointer-events:none; }
.oq-team-hero h1 { font-size:clamp(2.2rem,5vw,4rem); line-height:1.08;
    letter-spacing:-.045em; color:#f6f0ff; padding:.6rem 0 .9rem; max-width:16ch; }
.oq-team-hero h1 span { color:#ffc785; }
.oq-team-hero p:last-child { color:#c9bfd9; max-width:62ch; line-height:1.7; margin:0; }
.oq-team-members { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1.25rem; }
.oq-team-card { padding:clamp(1.25rem,3vw,2rem); border:1px solid #493953; border-radius:20px;
    background:linear-gradient(145deg,#241b30,#15111f); min-width:0; display:flex; flex-direction:column; }
.oq-team-card-heading { display:flex; align-items:center; gap:1rem; margin-bottom:1.4rem; }
.oq-team-monogram { display:grid; place-items:center; flex:0 0 64px; height:64px; border-radius:20px;
    background:linear-gradient(135deg,#dac2ff,#a582ca); color:#241431;
    font-size:1.35rem; font-weight:800; box-shadow:0 8px 24px #05020c33; }
.oq-team-card-jay .oq-team-monogram { background:linear-gradient(135deg,#ffdbad,#c79575); }
.oq-team-card h2 { color:#f6f0ff; font-size:clamp(1.3rem,2.5vw,1.8rem); padding:0; letter-spacing:-.025em; }
.oq-team-card .oq-team-label { margin:.25rem 0 0; color:#bfb1d0; font-size:.85rem; }
.oq-team-card > p { color:#c9bfd9; line-height:1.65; margin:0 0 1.5rem; }
.oq-team-links { display:flex; flex-wrap:wrap; gap:.65rem; margin-top:auto; }
.oq-team-links a { display:inline-flex; align-items:center; justify-content:space-between; gap:.8rem;
    min-height:44px; padding:.65rem 1rem; border:1px solid #6f587e; border-radius:12px;
    color:#efe0ff !important; background:#332440; font-size:.9rem; font-weight:600; text-decoration:none; }
.oq-team-links a:hover { background:#473056; border-color:#dac2ff; }
.oq-team-links a:focus-visible { outline:3px solid #ffc785; outline-offset:4px; }
.oq-team-note { display:flex; flex-wrap:wrap; justify-content:space-between; gap:.5rem 1rem;
    margin:1.5rem 0 1rem; padding:1.2rem 0; border-top:1px solid #493953; color:#bfb1d0; font-size:.9rem; }
@media(max-width:760px) { .oq-team-members { grid-template-columns:1fr; } }
@media(max-width:420px) { .oq-team-links { flex-direction:column; } .oq-team-monogram { flex-basis:50px; height:50px; border-radius:15px; } }
</style>
<section class="oq-team-hero">
  <p class="oq-section-label">The people behind OrbitalQ</p>
  <h1>Curiosity brought<br>us <span>together.</span></h1>
  <p>We built OrbitalQ for Planet X and SPHEREx at the 2026 NASA Space Apps Challenge. Meet the team and explore the work behind the names.</p>
</section>
<div class="oq-team-members">
  <article class="oq-team-card" aria-labelledby="oq-team-aspira">
    <div class="oq-team-card-heading">
      <div class="oq-team-monogram" aria-hidden="true">AQ</div>
      <div><h2 id="oq-team-aspira">Aspira Qualquer</h2><p class="oq-team-label">OrbitalQ team</p></div>
    </div>
    <p>Explore my personal projects and game development portfolio.</p>
    <div class="oq-team-links">
      <a href="https://soubeatrizkaroline.vercel.app/">Personal portfolio <span aria-hidden="true">↗</span></a>
      <a href="https://aspiraqualquer.vercel.app/">Game portfolio <span aria-hidden="true">↗</span></a>
    </div>
  </article>
  <article class="oq-team-card oq-team-card-jay" aria-labelledby="oq-team-jay">
    <div class="oq-team-card-heading">
      <div class="oq-team-monogram" aria-hidden="true">J</div>
      <div><h2 id="oq-team-jay">Jay</h2><p class="oq-team-label">OrbitalQ team</p></div>
    </div>
    <p>Discover the projects and work behind my contribution to OrbitalQ.</p>
    <div class="oq-team-links">
      <a href="https://jhay.goskip.app/">Jay’s portfolio <span aria-hidden="true">↗</span></a>
    </div>
  </article>
</div>
<div class="oq-team-note">
  <span>Built together for a changing sky.</span>
  <span>NASA Space Apps Challenge 2026</span>
</div>
""", unsafe_allow_html=True)
    st.link_button("Explore OrbitalQ on GitHub ↗", REPO)


def render_solution_navigation():
    st.markdown("""
<div class="oq-workspace-heading">
  <p class="oq-section-label">Observation workspace · NASA / IPAC IRSA</p>
  <h1>Explore the changing sky.</h1>
  <p>Compare visits over time, explore infrared wavelengths, or open your own files.</p>
</div>
""", unsafe_allow_html=True)
    return st.segmented_control(
        "Explorer mode", list(EXPLORER_VIEWS),
        format_func=EXPLORER_VIEWS.__getitem__, default="Ready-to-view examples",
        label_visibility="collapsed", key="explorer_view",
    ) or "Ready-to-view examples"


site_page = render_site_navigation()
if "explorer_view" in st.session_state:
    st.session_state["explorer_view"] = st.session_state["explorer_view"]
view = render_solution_navigation() if site_page == "Solution" else site_page


def render_target_controls(instruments):
    with instruments, st.container(key="oq-advanced-settings", border=True):
        st.header("Target coordinates")
        known_presets = [name for name, values in TARGET_PRESETS.items() if values.get("ra_deg") is not None]
        preset_options = [DEFAULT_TARGET] + [name for name in known_presets if name != DEFAULT_TARGET] + ["Custom"]
        preset = st.selectbox(
            "Target preset",
            preset_options,
            key="target_preset",
            on_change=clear_resolved_target,
            help="Choose a reference sky field, or select Custom to enter coordinates manually.",
        )
        preset_values = TARGET_PRESETS.get(preset, {})
        target_name = preset
        if preset == "Custom":
            target_name = st.text_input("Target name", value="Custom target", key="custom_target_name")
        object_name = st.text_input(
            "Resolve object name (optional)",
            key="object_name_input",
            help="Uses Astropy's configured name resolver. If it cannot resolve the name, enter ICRS coordinates manually.",
        )
        if st.button("Resolve name"):
            if not object_name.strip():
                st.warning("Enter an object name first.")
            else:
                with st.spinner("Resolving object name…"):
                    resolved = resolve_object_name(object_name.strip())
                    st.session_state["resolved_object"] = resolved
                    st.session_state["resolved_object_name"] = object_name.strip()
                    if resolved.get("ok"):
                        st.session_state["ra_input"] = resolved["ra"]
                        st.session_state["dec_input"] = resolved["dec"]
        if preset != "Custom" and not object_name.strip():
            st.session_state.pop("resolved_object", None)
            st.session_state.pop("resolved_object_name", None)
        resolved_object = st.session_state.get("resolved_object")
        resolved_for_name = (
            resolved_object
            if st.session_state.get("resolved_object_name") == object_name.strip()
            else None
        )
        if resolved_for_name and resolved_for_name.get("ok"):
            target_name = object_name.strip()
            st.success(
                f"Resolved: RA {resolved_for_name['ra']:.6f}°, "
                f"Dec {resolved_for_name['dec']:.6f}°"
            )
        elif resolved_for_name and not resolved_for_name.get("ok"):
            st.warning(
                f"Object name could not be resolved: "
                f"{resolved_for_name.get('message', 'unknown error')}"
            )
        default_ra = float(
            resolved_for_name["ra"]
            if resolved_for_name and resolved_for_name.get("ok")
            else preset_values.get("ra_deg") or 133.795129
        )
        default_dec = float(
            resolved_for_name["dec"]
            if resolved_for_name and resolved_for_name.get("ok")
            else preset_values.get("dec_deg")
            if preset_values.get("dec_deg") is not None
            else -7.245147
        )
        if "ra_input" not in st.session_state:
            st.session_state["ra_input"] = default_ra
        if "dec_input" not in st.session_state:
            st.session_state["dec_input"] = default_dec
        coordinate_source = (
            (preset, "resolved", object_name.strip())
            if resolved_for_name and resolved_for_name.get("ok")
            else (preset, "preset")
        )
        if preset == "Custom" and not (resolved_for_name and resolved_for_name.get("ok")):
            coordinate_source = ("Custom",)
        if st.session_state.get("coordinate_source") != coordinate_source:
            if preset != "Custom" or (resolved_for_name and resolved_for_name.get("ok")):
                st.session_state["ra_input"] = default_ra
                st.session_state["dec_input"] = default_dec
            st.session_state["coordinate_source"] = coordinate_source
        ra = st.number_input(
            "Right ascension (degrees)",
            min_value=0.0,
            max_value=360.0,
            format="%.6f",
            key="ra_input",
        )
        dec = st.number_input(
            "Declination (degrees)",
            min_value=-90.0,
            max_value=90.0,
            format="%.6f",
            key="dec_input",
        )
        cutout_size = st.select_slider("Cutout width (pixels)", options=[21, 31, 41, 51, 71, 101],
                                       value=51, key="cutout_size")
        display_low = st.slider("Display lower percentile", 0.0, 20.0, 2.0, 0.5, key="display_low")
        display_high = st.slider("Display upper percentile", 80.0, 100.0, 98.0, 0.5, key="display_high")
        if preset_values and not (resolved_for_name and resolved_for_name.get("ok")):
            note = preset_values["note"]
            if preset_values.get("epoch"):
                note = f"Reference epoch: {preset_values['epoch']}. {note}"
            st.caption(note)
            if preset_values.get("source"):
                st.markdown(f"[Preset coordinate source]({preset_values['source']})")

    try:
        ra = float(ra)
        dec = float(dec)
        if not np.isfinite(ra) or not np.isfinite(dec):
            raise ValueError("RA and Dec must be finite numbers.")
        target = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
    except (TypeError, ValueError) as exc:
        st.error(f"Invalid target coordinates: {exc}")
        st.stop()
    display_percentiles = (display_low, display_high)
    target_signature = (round(float(ra), 6), round(float(dec), 6), int(cutout_size))
    demo_coordinates = (
        abs(float(ra) - DEMO_RA) < 1e-6
        and abs(float(dec) - DEMO_DEC) < 1e-6
    )
    demo_active = bool(st.session_state.get("demo_sequence_active") and demo_coordinates)
    if not demo_active:
        st.session_state["demo_sequence_active"] = False
    else:
        target_name = "Verified SPHEREx DR1 example field"
        instruments.info(
            "Example field active: RA 160.6180°, Dec +30.6694°. "
            "This is not WISE 0855."
        )
    if st.session_state.get("level2_state_version") != LEVEL2_CACHE_VERSION:
        st.session_state.pop("remote_frames", None)
        st.session_state.pop("remote_errors", None)
        st.session_state.pop("frame_signature", None)
        st.session_state["level2_state_version"] = LEVEL2_CACHE_VERSION
    if st.session_state.get("target_signature") != target_signature:
        st.session_state["target_signature"] = target_signature
        st.session_state.pop("archive_result", None)
        st.session_state.pop("demo_sequence_result", None)
        st.session_state.pop("remote_frames", None)
        st.session_state.pop("remote_errors", None)
        st.session_state.pop("frame_signature", None)
        st.session_state["epoch_selector"] = 0
        if demo_active:
            st.session_state["demo_sequence_pending"] = True
    return target_name, ra, dec, target, cutout_size, display_percentiles


if view in ("Real DR1 sky preview", "Compare Level 2 visits"):
    science_workspace, instruments = st.columns([3, 1.15], gap="medium")
    target_name, ra, dec, target, cutout_size, display_percentiles = render_target_controls(instruments)
else:
    # Keep instrument settings when their widgets are off-screen.
    for widget_key in ("target_preset", "custom_target_name", "object_name_input", "ra_input",
                       "dec_input", "cutout_size", "display_low", "display_high"):
        if widget_key in st.session_state:
            st.session_state[widget_key] = st.session_state[widget_key]


@st.cache_resource(show_spinner="Connecting to the public SPHEREx DR1 cube…")
def open_public_cube():
    # FITS is accessed through fsspec so image sections can be fetched by byte range.
    return fits.open(
        CUBE_URL,
        use_fsspec=True,
        fsspec_kwargs={
            "block_size": 1024 * 1024,
            "client_kwargs": {"timeout": aiohttp.ClientTimeout(total=30)},
        },
    )


@st.cache_data(show_spinner=False)
def cube_channel_labels():
    """Return archive-provided channel labels without inventing wavelengths."""
    try:
        table = open_public_cube()["SPECTRAL_CHANNELS"].data
        labels = []
        for index, row in enumerate(table):
            labels.append(
                f"{index + 1}: {float(row['WAVELENGTH']):.3f} µm · "
                f"{str(row['DETECTOR']).strip()} channel {int(row['SUBCHAN'])}"
            )
        if not labels:
            raise ValueError("SPECTRAL_CHANNELS table is empty")
        return labels, None
    except Exception as exc:
        return (
            [f"Channel {index + 1} (wavelength unavailable)" for index in range(102)],
            f"Archive channel metadata unavailable: {exc}",
        )


@st.cache_data(ttl=3600, show_spinner=False)
def cached_remote_level2(
    cache_version: str,
    source_url: str,
    ra_deg: float,
    dec_deg: float,
    size: int,
):
    """Cache successful remote cutouts for this process and target."""
    if cache_version != LEVEL2_CACHE_VERSION:
        raise ValueError("Unsupported Level 2 cache version")
    target_coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
    filename = source_url.rsplit("/", 1)[-1].split("?", 1)[0]
    return read_level2(
        source_url,
        target_coord,
        size,
        filename,
        source_url=source_url,
    )


def quality_counts(data, flags=None, variance=None):
    image = np.asarray(data)
    finite_pixels = int(np.isfinite(image).sum())
    flag_pixels = 0
    if flags is not None:
        flag_data = np.asarray(flags)
        flag_pixels = int(np.count_nonzero(np.isfinite(flag_data) & (flag_data != 0)))
    median_variance = None
    if variance is not None:
        variance_data = np.asarray(variance)
        finite_variance = variance_data[np.isfinite(variance_data)]
        if finite_variance.size:
            median_variance = float(np.median(finite_variance))
    return finite_pixels, flag_pixels, median_variance


def display_array(data, title, marker=None, percentiles=None, stretch_limits=None, *, unit="MJy/sr"):
    data = np.asarray(data, dtype=float)
    finite = np.isfinite(data)
    if not finite.any():
        st.warning("No finite image pixels in this cutout.")
        return
    low, high = percentiles or display_percentiles
    if low >= high:
        low, high = 2.0, 98.0
    lo, hi = stretch_limits or np.nanpercentile(data[finite], [low, high])
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        lo = float(np.nanmin(data[finite]))
        hi = float(np.nanmax(data[finite])) if np.nanmax(data[finite]) > lo else lo + 1
    fig, ax = plt.subplots(figsize=(7, 6), facecolor="#0d1122")
    ax.set_facecolor("#060812")
    ax.tick_params(colors="#bdcbea")
    for spine in ax.spines.values():
        spine.set_color("#3b3561")
    im = ax.imshow(data, origin="lower", cmap="inferno", vmin=lo, vmax=hi)
    if marker is not None:
        ax.plot(marker[0], marker[1], marker="+", color="cyan", markersize=14, mew=2)
    ax.set_title(title, color="#f1f5ff")
    ax.set_xlabel("Cutout X (pixel)", color="#bdcbea")
    ax.set_ylabel("Cutout Y (pixel)", color="#bdcbea")
    colorbar = fig.colorbar(im, ax=ax, label=unit)
    colorbar.ax.tick_params(colors="#bdcbea")
    colorbar.ax.yaxis.label.set_color("#bdcbea")
    fig.tight_layout()
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def shared_stretch_limits(*arrays):
    finite_arrays = [
        np.asarray(array, dtype=float)[np.isfinite(array)]
        for array in arrays
    ]
    finite_arrays = [array for array in finite_arrays if array.size]
    if not finite_arrays:
        return None
    values = np.concatenate(finite_arrays)
    low, high = np.nanpercentile(values, display_percentiles)
    if not np.isfinite(low) or not np.isfinite(high) or low == high:
        low = float(np.nanmin(values))
        high = float(np.nanmax(values))
        if high <= low:
            high = low + 1
    return float(low), float(high)


def observation_csv(frames, target_name, ra, dec, selected_index=None, comparison_index=None, warning=None):
    """Serialize the visible observation table without dropping provenance."""
    fields = [
        "target", "target_ra_deg", "target_dec_deg", "date_obs", "mjd_obs", "obsid",
        "detector", "wavelength", "release", "release_source", "processing_version", "filename",
        "source_url", "bunit", "pixel_x", "pixel_y", "finite_image_pixels",
        "nonzero_flags_pixels", "median_variance", "comparison_status",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for index, frame in enumerate(frames):
        finite_pixels, flagged_pixels, median_variance = quality_counts(
            frame.image, frame.flags, frame.variance
        )
        comparison_status = ""
        if index in (selected_index, comparison_index):
            comparison_status = f"selected pair: {warning}" if warning else "metadata compatible"
        row = {field: getattr(frame, field, "") for field in fields}
        row.update({
            "target": target_name,
            "target_ra_deg": ra,
            "target_dec_deg": dec,
            "finite_image_pixels": f"{finite_pixels}/{frame.image.size}",
            "nonzero_flags_pixels": flagged_pixels,
            "median_variance": "" if median_variance is None else median_variance,
            "comparison_status": comparison_status,
        })
        writer.writerow(row)
    return output.getvalue()


def show_observation_interval(date_a, mjd_a, date_b, mjd_b):
    """Show timestamps and the actual interval for the selected pair."""
    duration = "Unavailable"
    if np.isfinite(mjd_a) and np.isfinite(mjd_b):
        days = abs(mjd_b - mjd_a)
        if days >= 1:
            duration = f"{days:.2f} days"
        elif days >= 1 / 24:
            duration = f"{days * 24:.2f} hours"
        elif days >= 1 / 1440:
            duration = f"{days * 1440:.1f} min"
        else:
            duration = f"{days * 86400:.1f} sec"
    st.markdown(
        '<dl class="oq-interval">'
        f'<div><dt>Observation A</dt><dd>{escape(date_a or "Date unavailable")}</dd></div>'
        f'<div><dt>Time between visits</dt><dd>{duration}</dd></div>'
        f'<div><dt>Observation B</dt><dd>{escape(date_b or "Date unavailable")}</dd></div>'
        '</dl>',
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def read_packaged_observations():
    """Read the same genuine SPHEREx cutouts shipped with the static viewer."""
    root = Path(__file__).resolve().parent
    html = (root / "dist" / "index.html").read_text(encoding="utf-8")
    start = '<script id="case-data" type="application/json">'
    _, found, block = html.partition(start)
    cases = json.loads(block.split("</script>", 1)[0]) if found else []
    extra_path = root / "data" / "packaged_sequences.json"
    if extra_path.exists():
        cases.extend(json.loads(extra_path.read_text(encoding="utf-8")))
    return list({case["key"]: case for case in cases}.values())


def display_time_lapse(frames):
    """Render a browser-side timeline of dated sky cutouts."""
    template = Path(__file__).resolve().parent / "ui" / "timeline.html"
    payload = json.dumps(frames, allow_nan=False).replace("<", "\\u003c")
    components.html(
        Template(template.read_text(encoding="utf-8")).substitute(frames=payload),
        height=610,
    )


def build_time_lapse_frames(observations):
    """Build previews with a single display stretch across the sequence."""
    limits = shared_stretch_limits(*(frame.image for frame in observations))
    result = []
    for frame in observations:
        buffer = io.BytesIO()
        plt.imsave(
            buffer, frame.image, format="png", origin="lower", cmap="inferno",
            vmin=limits[0], vmax=limits[1],
        )
        result.append({
            "date": frame.date_obs or f"MJD {frame.mjd_obs:.5f}",
            "mjd": float(frame.mjd_obs),
            "wavelength": frame.wavelength,
            "source": frame.source_url if frame.source_url.startswith("https://") else "",
            "image": "data:image/png;base64," + b64encode(buffer.getvalue()).decode("ascii"),
        })
    return result


def show_packaged_examples():
    try:
        cases = {case["name"]: case for case in read_packaged_observations()
                 if len(case.get("frames", [])) >= 2}
    except (OSError, ValueError) as exc:
        st.error(f"Could not open the packaged SPHEREx observations: {exc}")
        return
    if not cases:
        st.info("No packaged examples are available. Open the FITS workspace to load observations.")
        return

    with st.container(key="oq-targets", border=True):
        name = st.selectbox("Target field", list(cases),
            format_func=lambda name: f"{name} · {len(cases[name]['frames'])} available visits")
    case = cases[name]
    frames = sorted(case["frames"], key=lambda item: item["mjd"])
    viewport, instrumentation = st.columns([3, 1.15], gap="medium")
    with instrumentation:
        with st.container(key="oq-instrumentation", border=True):
            st.subheader("Observation guide")
            mode = st.segmented_control("Comparison mode", ["Time-lapse", "Swipe"], default="Time-lapse") or "Time-lapse"
            st.caption(f"{case['detector']} · {len(frames)} dated observations")
            observing_guides = {
                "Epsilon Indi B": "Follow the field across four visits. Use surrounding stars as reference points and check the wavelength shown for each observation.",
                "RW Aurigae": "Compare the region around this young star across three dates. Check the wavelength before interpreting differences in brightness.",
                "R Draconis": "Explore three visits to the field around this variable star. Compare the target with nearby stars and inspect the original exposure.",
            }
            st.write(observing_guides.get(name, case["description"]))
            st.link_button("NASA/IPAC original FITS ↗", frames[0]["fits"])
            st.caption("Opens the first visit. Each timeline frame also links to its own exposure.")
            if case.get("processing_note") or case.get("snapshot"):
                with st.expander("Data sources and processing credits"):
                    if case.get("processing_note"):
                        st.write(case["description"])
                        st.write(case["processing_note"])
                    if case.get("snapshot"):
                        st.markdown(f"[Processed image source — SkyShift]({case['snapshot']})")
                    st.markdown("[Processing license and credits](https://github.com/SouBeatrizKaroline/NasaSpaceApp_OrbitalQ/blob/main/dist/licenses/skyshift.txt)")
                    st.dataframe(
                        [{"date": item["date"], "wavelength_um": item["wavelength"],
                          "official_fits": item["fits"]} for item in frames],
                        hide_index=True, use_container_width=True,
                    )
    with viewport:
        if mode == "Time-lapse":
            display_time_lapse([
                {
                    "date": frame["date"],
                    "mjd": frame["mjd"],
                    "image": frame["image"],
                    "wavelength": f"{frame['wavelength']:.3f} µm",
                    "source": frame["fits"],
                }
                for frame in frames
            ])
        else:
            display_packaged_swipe(case, frames)



@st.cache_data(ttl=900, show_spinner=False)
def search_official_observations(ra, dec, releases):
    result = search_level2_footprints(
        SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs"),
        ra, dec, radius_deg=0.01, max_results=24, releases=releases, timeout=30,
    )
    if not result.get("ok"):
        raise RuntimeError("NASA/IPAC is temporarily unavailable. Retry or select a single release. Loaded images are retained.")
    return result



def render_official_archive():
    st.subheader("Search real SPHEREx exposures")
    st.caption("NASA/IPAC IRSA · Official SIA2 API · DR1 / QR3")
    st.write("Query a sky position and load original FITS pixels. Each candidate is checked against its celestial WCS.")
    with st.form("official_archive_search"):
        left, right = st.columns(2)
        ra = left.number_input("ICRS RA (degrees)", 0.0, 360.0, 269.452077, format="%.6f")
        dec = right.number_input("ICRS Dec (degrees)", -90.0, 90.0, 4.693365, format="%.6f")
        releases = st.multiselect("Releases", ["DR1", "QR3"], default=["DR1", "QR3"])
        st.caption("Default: Barnard’s Star J2000 reference field. Proper motion is not propagated.")
        submitted = st.form_submit_button("Search official observations", type="primary")
    if submitted:
        st.session_state.pop("official_cutout", None)
        st.session_state.pop("official_search", None)
        if not releases:
            st.warning("Choose at least one release.")
        else:
            with st.spinner("Querying NASA/IPAC and checking footprints…"):
                try:
                    result = search_official_observations(ra, dec, tuple(releases))
                    st.session_state["official_search"] = (ra, dec, result)
                except Exception as exc:
                    st.error(f"Archive unavailable: {exc}")
    saved = st.session_state.get("official_search")
    if not saved:
        st.info("Submit a position to retrieve official observations.")
        return
    search_ra, search_dec, result = saved
    st.caption(f"Results for RA {search_ra:.6f}°, Dec {search_dec:.6f}°")
    if not result.get("ok"):
        st.warning(result.get("message", "Archive unavailable."))
        return
    st.info(result["message"])
    matches = list({item["source_url"]: item for item in result.get("matches", [])}.values())
    matches.sort(key=lambda item: item["mjd_obs"] if np.isfinite(item["mjd_obs"]) else float("inf"))
    if result.get("rejected"):
        with st.expander("Query limits and rejected candidates"):
            for reason in result["rejected"]:
                st.text(reason)
    if not matches:
        st.warning("No verified cutouts in this bounded query. This does not prove absence of observations.")
        return
    selected = st.selectbox("Verified exposure", range(len(matches)),
        format_func=lambda i: f"{matches[i]['date_obs'] or 'Date unavailable'} · {matches[i]['release']} · {matches[i]['filename']}")
    item = matches[selected]
    st.link_button("Original NASA/IPAC FITS ↗", item["source_url"])
    st.caption("Up to 24 candidates checked; this is not a complete archive census.")
    if st.button("Load this official image", type="primary"):
        st.session_state.pop("official_cutout", None)
        with st.spinner("Reading original FITS pixels…"):
            try:
                frame = cached_remote_level2(LEVEL2_CACHE_VERSION, item["source_url"], search_ra, search_dec, 71)
                st.session_state["official_cutout"] = (item["source_url"], frame)
            except Exception as exc:
                st.error(f"Could not load exposure: {exc}")
    loaded = st.session_state.get("official_cutout")
    if loaded and loaded[0] == item["source_url"]:
        frame = loaded[1]
        display_array(frame.image, frame.date_obs or "Official exposure", percentiles=(2.0, 98.0), unit=frame.bunit)
        st.caption(f"NASA/IPAC IRSA · OBSID: {frame.obsid} · Detector: {frame.detector} · Date: {frame.date_obs} · Units: {frame.bunit}")
        st.caption("Original FITS pixels; 2–98 percentile display stretch. No generated imagery.")
        st.info("Coverage is not target detection. Measurements require epoch, wavelength, quality, and calibration checks.")


def display_packaged_swipe(case, frames):
    first_slot, second_slot = st.columns(2)
    first_index = first_slot.selectbox(
        "First visit", range(len(frames) - 1), format_func=lambda i: frames[i]["date"],
        key=f"example_first_{case['key']}",
    )
    later_options = [i for i in range(first_index + 1, len(frames))
                     if frames[i]["mjd"] > frames[first_index]["mjd"]]
    if not later_options:
        st.info("This visit has no later timestamp in the packaged sequence.")
        return
    second_index = second_slot.selectbox(
        "Later visit", later_options, index=len(later_options) - 1,
        format_func=lambda i: frames[i]["date"], key=f"example_second_{case['key']}",
    )
    first, second = frames[first_index], frames[second_index]
    show_observation_interval(first["date"], first["mjd"], second["date"], second["mjd"])
    image_a = first["image"].removeprefix("data:image/png;base64,")
    image_b = second["image"].removeprefix("data:image/png;base64,")
    width, height = unpack(">II", b64decode(image_a[:32])[16:24])
    template = Path(__file__).resolve().parent / "ui" / "swipe.html"
    components.html(
        Template(template.read_text(encoding="utf-8")).substitute(
            width=width, height=height, max_width=f"{360 * width / height:.2f}",
            label_a="Earlier", label_b="Later",
            date_a=escape(first["date"]), date_b=escape(second["date"]),
            image_a=image_a, image_b=image_b,
        ),
        height=485,
    )
    st.caption(
        f"Detector: {case['detector']}. Use nearby stars as visual references. "
        "A visible shift is a starting point for investigation."
    )
    left, right = st.columns(2)
    left.link_button("Earlier FITS source", first["fits"])
    right.link_button("Later FITS source", second["fits"])


def render_spectral_preview():
    st.subheader("SPHEREx DR1 All-Sky Cube")
    st.info(
        "The 102 planes of the DR1 cube represent infrared wavelengths. "
        "Open Compare visits or the FITS workspace to compare exposures by date."
    )
    channel_labels, channel_error = cube_channel_labels()
    if channel_error:
        st.warning(channel_error)
    plane = st.select_slider(
        "Spectral channel (wavelength, not date)",
        options=list(range(len(channel_labels))),
        value=min(16, len(channel_labels) - 1),
        format_func=lambda index: channel_labels[index],
    )
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
                "Choose WISE 0855−0714 for the built-in preview, or open the FITS workspace with files covering your target."
            )
        elif plane + 1 in (51, 52):
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
                image_hdu.section[plane, y0:y1, x0:x1], dtype=float
            )
            nhits = np.asarray(
                hdul["NHITS"].section[plane, y0:y1, x0:x1], dtype=float
            )
            flags = np.asarray(
                hdul["FLAGS"].section[plane, y0:y1, x0:x1], dtype=float
            )

            channel_table = hdul["SPECTRAL_CHANNELS"].data
            channel = channel_table[plane]
            wavelength = float(channel["WAVELENGTH"])
            detector = str(channel["DETECTOR"]).strip()
            subchannel = int(channel["SUBCHAN"])
            cx, cy = x - x0, y - y0

            m1, m2, m3 = st.columns(3)
            m1.metric("Wavelength", f"{wavelength:.3f} µm")
            m2.metric("Detector", f"{detector} · channel {subchannel}")
            centre_hits = nhits[int(round(cy)), int(round(cx))]
            m3.metric(
                "Centre NHITS",
                str(int(centre_hits)) if np.isfinite(centre_hits) else "unavailable",
            )

            display_array(
                image,
                f"{target_name} field · channel {plane + 1} · {wavelength:.3f} µm",
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
                f"Cube pixel: ({x:.2f}, {y:.2f}) · Tile: Npix10226 · Release: DR1 · "
                "Cube values are zodiacal-subtracted surface brightness. "
                "This is a spectral preview, not a time-series measurement."
            )
            scale_x, scale_y = pixel_scale_arcsec(cube_wcs)
            st.caption(
                f"Cutout field of view: {image.shape[1] * scale_x:.1f}″ × "
                f"{image.shape[0] * scale_y:.1f}″"
            )
            st.caption(f"Provenance: SPHEREx DR1 All-Sky Cube · {CUBE_URL}")
            with st.expander("Quality flags in this cutout"):
                finite_flags = flags[np.isfinite(flags)]
                values, counts = np.unique(finite_flags, return_counts=True)
                st.dataframe(
                    {"flag_value": values, "pixel_count": counts},
                    use_container_width=True,
                    hide_index=True,
                )
                missing_flags = flags.size - finite_flags.size
                if missing_flags:
                    st.caption(f"FLAGS pixels without finite values: {missing_flags}")
    except Exception as exc:
        st.error(f"Could not load the remote cube: {exc}")
        st.write(
            "Check your internet connection and the public S3 endpoint. "
            "The app reads a small cutout from the remote FITS cube; it is not intended "
            "to download the entire 306 MB tile."
        )
    render_wise_field_resources()

def render_fits_workspace():
    with st.container(border=True):
        demo_copy, demo_action = st.columns([2, 1])
        with demo_copy:
            st.subheader("One sky field, two observations")
            st.write(
                "Open two public DR1 observations and drag the divider to reveal each visit."
            )
        with demo_action:
            st.button(
                "Load real example",
                type="primary",
                on_click=activate_demo_sequence,
                use_container_width=True,
            )
            st.caption("Example field: RA 160.6180°, Dec +30.6694°")
    if st.session_state.pop("demo_sequence_pending", False):
        demo_frames = []
        demo_errors = []
        with st.status("Loading real SPHEREx observations…", expanded=True) as status:
            for index, url in enumerate(DEMO_FITS_URLS, start=1):
                st.write(f"Reading and checking observation {index} of {len(DEMO_FITS_URLS)}…")
                try:
                    demo_frames.append(cached_remote_level2(
                        LEVEL2_CACHE_VERSION,
                        url,
                        float(ra),
                        float(dec),
                        int(cutout_size),
                    ))
                except Exception as exc:
                    demo_errors.append(f"{url.rsplit('/', 1)[-1]}: {exc}")
            if demo_errors:
                status.update(label="Some observations could not load", state="error")
            else:
                status.update(label="Both observations loaded", state="complete", expanded=False)
        st.session_state["remote_frames"] = demo_frames
        st.session_state["remote_errors"] = demo_errors
        st.session_state["demo_sequence_result"] = {
            "loaded": len(demo_frames),
            "errors": demo_errors,
        }

    demo_result = st.session_state.get("demo_sequence_result")
    if demo_result:
        if demo_result["loaded"] == len(DEMO_FITS_URLS):
            st.info(
                "Both real DR1 observations loaded and passed target-coordinate "
                "WCS checks. Their metadata do not establish scientific variability."
            )
        for error in demo_result["errors"]:
            st.error(f"Could not load a demonstration observation: {error}")

            st.caption("You can also upload FITS files downloaded directly from the archive.")


    with st.expander("Find more official visits for this field"):
        st.caption("Search DR1 and QR3. Only successfully loaded exposures are added; existing images are retained.")
        if st.button("Find and add available exposures"):
            with st.spinner("Querying NASA/IPAC and verifying cutouts…"):
                try:
                    result = search_official_observations(float(ra), float(dec), ("DR1", "QR3"))
                    existing = list(st.session_state.get("remote_frames", []))
                    urls = {frame.source_url for frame in existing}
                    identities = {(frame.obsid, frame.detector, frame.processing_version)
                                  for frame in existing if frame.obsid}
                    candidates = {item["source_url"]: item for item in result.get("matches", [])
                                  if item["source_url"] not in urls}
                    ordered = sorted(candidates.values(),
                        key=lambda item: item["mjd_obs"] if np.isfinite(item["mjd_obs"]) else float("inf"))
                    indices = np.linspace(0, len(ordered)-1, min(8,len(ordered)), dtype=int) if ordered else []
                    added, failures = [], []
                    for index in indices:
                        item = ordered[int(index)]
                        try:
                            frame = cached_remote_level2(LEVEL2_CACHE_VERSION, item["source_url"], float(ra), float(dec), int(cutout_size))
                            identity = (frame.obsid, frame.detector, frame.processing_version)
                            if frame.obsid and identity in identities:
                                continue
                            if not np.isfinite(frame.image).any():
                                continue
                            added.append(frame)
                            identities.add(identity)
                        except Exception as exc:
                            failures.append(f"{item['filename']}: {exc}")
                    st.session_state["remote_frames"] = existing + added
                    if added:
                        st.success(f"Added {len(added)} verified exposure(s) to the comparison below.")
                    else:
                        st.info("No additional images could be loaded in this query.")
                    st.caption("Bounded search: up to 24 candidates checked and eight new cutouts loaded. Distinct dates are not guaranteed.")
                    if failures or result.get("rejected"):
                        with st.expander("Query details"):
                            for message in result.get("rejected", []) + failures:
                                st.text(message)
                except Exception as exc:
                    st.warning(str(exc))

    workspace = st.container()
    st.subheader("Add your own observations")
    st.caption("Use Level 2 FITS files that cover the coordinates in Target coordinates.")
    with st.expander("Browse the public SPHEREx archive"):
        st.caption(
            "The public S3 listing is an alternative to coordinate search. "
            "Browse a bounded folder sample, then load "
            "selected FITS files; only their own WCS can confirm target coverage."
        )
        release_name = st.selectbox(
            "Data release",
            ["DR1", "QR3"],
            key="s3_release",
        )
        release_prefix = f"{release_name.lower()}/level2/"
        try:
            with st.spinner("Listing public planning periods…"):
                period_result = cached_s3_prefixes(release_prefix)
            periods = sorted(period_result["prefixes"], reverse=True)
            if not periods:
                st.warning("The public archive returned no planning-period folders.")
            else:
                if period_result["truncated"]:
                    st.warning(
                        "The planning-period listing is bounded and incomplete. "
                        "A missing folder is not evidence of missing observations."
                    )
                period = st.selectbox(
                    "Planning period",
                    periods,
                    format_func=lambda value: value.rstrip("/").split("/")[-1],
                    key=f"s3_period_{release_name}",
                )
                run_result = cached_s3_prefixes(period)
                runs = run_result["prefixes"]
                if not runs:
                    st.warning("No processing runs were listed for this planning period.")
                else:
                    run = st.selectbox(
                        "Processing run",
                        runs,
                        format_func=lambda value: value.rstrip("/").split("/")[-1],
                        key=f"s3_run_{period}",
                    )
                    detector_result = cached_s3_prefixes(run)
                    detectors = detector_result["prefixes"]
                    if not detectors:
                        st.warning("No detector folders were listed for this run.")
                    else:
                        detector = st.selectbox(
                            "Detector folder",
                            detectors,
                            format_func=lambda value: value.rstrip("/").split("/")[-1],
                            key=f"s3_detector_{run}",
                        )
                        file_result = cached_s3_files(detector, 24)
                        archive_files = file_result["files"]
                        if archive_files:
                            st.caption(
                                f"Showing {len(archive_files)} public FITS files from "
                                f"`{detector.rstrip('/').split('/')[-1]}`."
                                + (" More files exist in this folder." if file_result["truncated"] else "")
                            )
                            st.dataframe(
                                [{
                                    "filename": item["filename"],
                                    "size_mb": round(item["size_bytes"] / (1024 * 1024), 1),
                                    "last_modified": item["last_modified"],
                                } for item in archive_files],
                                use_container_width=True,
                                hide_index=True,
                            )
                            file_labels = [
                                f"{item['filename']} · {item['size_bytes'] / (1024 * 1024):.1f} MB"
                                for item in archive_files
                            ]
                            selected_files = st.multiselect(
                                "Select files to verify at the current target",
                                options=list(range(len(archive_files))),
                                default=[],
                                format_func=lambda index: file_labels[index],
                                key=f"s3_files_{detector}",
                            )
                            if st.button(
                                "Verify FITS WCS and load selected files",
                                disabled=not selected_files,
                            ):
                                loaded_files = []
                                load_errors = []
                                with st.spinner("Reading selected FITS cutouts and checking WCS…"):
                                    for index in selected_files:
                                        item = archive_files[index]
                                        try:
                                            loaded_files.append(cached_remote_level2(
                                                LEVEL2_CACHE_VERSION,
                                                item["source_url"],
                                                float(ra),
                                                float(dec),
                                                int(cutout_size),
                                            ))
                                        except Exception as exc:
                                            load_errors.append(f"{item['filename']}: {exc}")
                                if loaded_files:
                                    existing = st.session_state.get("remote_frames", [])
                                    by_url = {frame.source_url: frame for frame in existing}
                                    by_url.update({frame.source_url: frame for frame in loaded_files})
                                    st.session_state["remote_frames"] = list(by_url.values())
                                st.session_state["s3_load_errors"] = load_errors
                                st.session_state["s3_load_count"] = len(loaded_files)
                                st.rerun()
                        else:
                            st.info("No FITS files were listed in this detector folder.")
        except Exception as exc:
            st.error(f"Public S3 archive browsing failed: {exc}")
            st.caption(
                "No coverage conclusion is drawn from a listing or network failure. "
                "The verified example, direct FITS URL and upload paths remain available."
            )
        for error in st.session_state.pop("s3_load_errors", []):
            st.warning(f"Selected file was not loaded: {error}")
        loaded_count = st.session_state.pop("s3_load_count", 0)
        if loaded_count:
            st.info(
                f"{loaded_count} selected file(s) passed their FITS WCS checks. "
                "This is a user-selected folder sample, not a global coverage search."
            )

    with st.expander("Load from a public FITS link"):
        with st.form("remote_fits_form"):
            remote_url = st.text_input(
                "Public SPHEREx Level 2 FITS URL",
                help="Direct loading is independent of archive discovery. Only the public IRSA SPHEREx hosts are accepted.",
                key="remote_fits_url",
            )
            load_remote = st.form_submit_button("Load remote FITS")
        if load_remote:
            if not is_supported_spherex_url(remote_url.strip()):
                st.error(
                    "Enter an HTTPS FITS URL from nasa-irsa-spherex.s3.us-east-1.amazonaws.com "
                    "or irsa.ipac.caltech.edu."
                )
            else:
                try:
                    with st.spinner("Reading the target-centred FITS cutout from the public archive…"):
                        remote_frame = cached_remote_level2(
                            LEVEL2_CACHE_VERSION,
                            remote_url.strip(),
                            float(ra),
                            float(dec),
                            int(cutout_size),
                        )
                    existing = st.session_state.get("remote_frames", [])
                    st.session_state["remote_frames"] = [
                        frame for frame in existing if frame.source_url != remote_frame.source_url
                    ] + [remote_frame]
                    st.success(f"Loaded verified FITS footprint: {remote_frame.filename}")
                except Exception as exc:
                    st.error(f"Could not load remote FITS observation: {exc}")

    uploads = st.file_uploader(
        "Upload Level 2 FITS files",
        help="For a closer comparison, choose visits of the same field from the same detector.",
        type=["fits", "fit"],
        accept_multiple_files=True,
    )

    remote_frames = st.session_state.get("remote_frames", [])
    if uploads or remote_frames:
        frames = []
        errors = []
        frames.extend(remote_frames)
        for uploaded in uploads or []:
            try:
                frames.append(read_level2(
                    io.BytesIO(uploaded.getvalue()), target, cutout_size, uploaded.name,
                    source_url=f"uploaded:{uploaded.name}",
                ))
            except Exception as exc:
                errors.append(f"{uploaded.name}: {exc}")

        frames = chronological(frames)

        with workspace:
            if errors:
                with st.expander(f"Files not displayed ({len(errors)})"):
                    for error in errors:
                        st.write("• " + error)

            if frames:
                st.subheader(target_name)
                st.caption(f"{len(frames)} verified cutout(s) · RA {ra:.4f}° · Dec {dec:+.4f}°")
                blank_frames = [
                    f.filename for f in frames if not np.isfinite(f.image).any()
                ]
                if blank_frames:
                    st.warning(
                        "These observations have no finite IMAGE pixels in the cutout "
                        "and cannot display a valid image: " + ", ".join(blank_frames)
                    )
                if len({frame.detector for frame in frames}) > 1:
                    st.warning(
                        "These files contain multiple detectors. Do not interpret their "
                        "brightness as a temporal light curve; detector bands differ."
                    )
                labels = [
                    f"{i + 1}. {f.date_obs or 'date unavailable'} · D{f.detector or '?'} · {f.obsid or 'OBSID unavailable'}"
                    for i, f in enumerate(frames)
                ]
                frame_signature = tuple(
                    (
                        f.source_url,
                        f.obsid,
                        f.mjd_obs if np.isfinite(f.mjd_obs) else None,
                    )
                    for f in frames
                )
                if st.session_state.get("frame_signature") != frame_signature:
                    st.session_state["frame_signature"] = frame_signature
                    st.session_state["epoch_selector"] = 0

                first_slot, second_slot = st.columns(2) if len(frames) > 1 else (None, None)
                selected = (
                    first_slot.selectbox(
                        "First observation", options=list(range(len(frames))),
                        format_func=lambda i: labels[i],
                        key="epoch_selector",
                    )
                    if len(frames) > 1 else 0
                )
                frame = frames[selected]
                comparison_stage = st.container()
                with st.expander("Inspect selected observation", expanded=len(frames) == 1):
                    a, b, c, d = st.columns(4)
                    a.metric("DATE-OBS", frame.date_obs or "not in header")
                    b.metric("MJD-OBS", f"{frame.mjd_obs:.5f}" if np.isfinite(frame.mjd_obs) else "not in header")
                    c.metric("Detector", frame.detector or "unknown")
                    d.metric("Wavelength", frame.wavelength)
                    st.caption(
                        f"Cutout field of view: {frame.image.shape[1] * frame.pixel_scale_x_arcsec:.1f}″ × "
                        f"{frame.image.shape[0] * frame.pixel_scale_y_arcsec:.1f}″"
                    )
                    display_array(
                        frame.image,
                        "Selected observation",
                        unit=frame.bunit,
                        marker=(frame.cutout_pixel_x, frame.cutout_pixel_y),
                    )
                    st.caption(
                        f"Target pixel in original image: ({frame.pixel_x:.2f}, "
                        f"{frame.pixel_y:.2f}) · OBSID: {frame.obsid or 'not in header'} · "
                        f"Release: {frame.release} ({frame.release_source}) · "
                        f"Processing: {frame.processing_version} · "
                        f"Units: {frame.bunit} · Reference epoch: {frame.reference_epoch}"
                    )
                with st.expander("Quality and provenance"):
                    finite_pixels = int(np.isfinite(frame.image).sum())
                    st.write(f"Finite IMAGE pixels in cutout: {finite_pixels}/{frame.image.size}")
                    if frame.flags is None:
                        st.info(
                            "FLAGS unavailable: "
                            + frame.extension_issues.get("FLAGS", "no compatible extension")
                        )
                    else:
                        finite_flags = frame.flags[np.isfinite(frame.flags)]
                        values, counts = np.unique(finite_flags, return_counts=True)
                        st.dataframe(
                            {"flag_value": values, "pixel_count": counts},
                            use_container_width=True,
                            hide_index=True,
                        )
                        missing_flag_pixels = int(frame.flags.size - finite_flags.size)
                        if missing_flag_pixels:
                            st.caption(f"FLAGS pixels without finite values: {missing_flag_pixels}")
                        st.caption("FLAGS are quality metadata; SOURCE is not automatically treated as a bad-pixel mask.")
                    if frame.variance is None:
                        st.info(
                            "VARIANCE unavailable: "
                            + frame.extension_issues.get("VARIANCE", "no compatible extension")
                        )
                    else:
                        finite_variance = frame.variance[np.isfinite(frame.variance)]
                        if finite_variance.size:
                            st.write(f"Median variance: {np.nanmedian(finite_variance):.5g} ({frame.bunit})²")
                        else:
                            st.warning("VARIANCE extension has no finite values in this cutout.")
                    st.write(f"Source: `{frame.source_url}`")
                    if frame.extension_issues:
                        st.caption(
                            "Unavailable quality metadata: "
                            + "; ".join(
                                f"{name}: {reason}"
                                for name, reason in frame.extension_issues.items()
                            )
                        )
                if len(frames) > 1:
                    with st.expander("Observation timeline", expanded=True):
                        st.dataframe(
                            [{
                                "date_obs": f.date_obs, "mjd_obs": f.mjd_obs,
                                "detector": f.detector, "obsid": f.obsid,
                                "wavelength": f.wavelength, "release": f.release,
                                "processing": f.processing_version, "filename": f.filename,
                                "source": f.source_url,
                            } for f in frames],
                            use_container_width=True,
                            hide_index=True,
                        )
                with comparison_stage:
                    if len(frames) > 1:
                        compare_index = second_slot.selectbox(
                            "Second observation",
                            options=[i for i in range(len(frames)) if i != selected],
                            format_func=lambda i: labels[i],
                        )
                        warning = comparison_warning(frame, frames[compare_index])
                        if warning:
                            st.warning(f"Visual comparison only: {warning}. Check the metadata before interpreting changes.")
                        first, second = (frames[index] for index in sorted((selected, compare_index)))
                        matching_units = (
                            first.bunit == second.bunit
                            and first.bunit.strip().lower() not in {"", "unknown"}
                        )
                        shared_limits = (
                            shared_stretch_limits(first.image, second.image) if matching_units else None
                        )
                        modes = ["Before / after", "Blink"]
                        if (
                            shared_limits is not None
                            and first.image.shape == second.image.shape
                            and np.isfinite(first.image).any()
                            and np.isfinite(second.image).any()
                        ):
                            modes.insert(0, "Swipe")
                        sequence = [
                            visit for visit in frames
                            if visit.detector and visit.detector == frame.detector
                            and visit.bunit == frame.bunit
                            and visit.bunit.strip().lower() not in {"", "unknown"}
                            and visit.image.shape == frame.image.shape
                            and np.isfinite(visit.mjd_obs)
                            and np.isfinite(visit.image).any()
                        ]
                        by_time = {visit.mjd_obs: visit for visit in sequence}
                        sequence = [by_time[mjd] for mjd in sorted(by_time)]
                        if len(sequence) > 1:
                            modes.append("Time-lapse")
                        mode = st.segmented_control("Comparison view", modes, default=modes[0]) or modes[0]
                        if "Swipe" not in modes:
                            st.caption("Swipe requires matching image dimensions and units, with valid pixels in both visits.")
                        if mode != "Time-lapse":
                            show_observation_interval(
                                first.date_obs, first.mjd_obs, second.date_obs, second.mjd_obs,
                            )
                        if mode == "Time-lapse":
                            st.caption(
                                f"{len(sequence)} visits from the selected detector with shared units "
                                "and display scale. The cutouts retain their native pixel grids."
                            )
                            display_time_lapse(build_time_lapse_frames(sequence))
                        elif mode == "Swipe":
                            st.caption("Both cutouts share a color scale and retain their native pixel grids.")
                            display_swipe(first, second, shared_limits)
                        elif mode == "Blink":
                            blink_key = f"blink_{first.obsid}_{second.obsid}_{selected}_{compare_index}"
                            if blink_key not in st.session_state:
                                st.session_state[blink_key] = 0
                            if st.button("Show next blink frame", key=f"button_{blink_key}"):
                                st.session_state[blink_key] = 1 - st.session_state[blink_key]
                            blink_frame = (first, second)[st.session_state[blink_key]]
                            st.caption(
                                ("Both images share a color scale. " if shared_limits else "Each image uses its own color scale. ")
                                + "Use the button to switch between observations."
                            )
                            display_array(
                                blink_frame.image,
                                f"Blink frame · {blink_frame.date_obs or 'date unavailable'} · {blink_frame.obsid or 'OBSID unavailable'}",
                                marker=(blink_frame.cutout_pixel_x, blink_frame.cutout_pixel_y),
                                stretch_limits=shared_limits,
                                unit=blink_frame.bunit,
                            )
                        else:
                            before_frame, after_frame = first, second
                            chronological_pair = (
                                np.isfinite(before_frame.mjd_obs)
                                and np.isfinite(after_frame.mjd_obs)
                                and before_frame.mjd_obs < after_frame.mjd_obs
                            )
                            before_title = (
                                f"Before · {before_frame.date_obs or 'date unavailable'}"
                                if chronological_pair
                                else f"Observation A · {before_frame.date_obs or 'date unavailable'}"
                            )
                            after_title = (
                                f"After · {after_frame.date_obs or 'date unavailable'}"
                                if chronological_pair
                                else f"Observation B · {after_frame.date_obs or 'date unavailable'}"
                            )
                            st.caption(
                                ("Both panels share a color scale. " if shared_limits else "Each panel uses its own color scale. ")
                                + "Both panels retain the original pixel grids."
                            )
                            left, right = st.columns(2)
                            with left:
                                display_array(
                                    before_frame.image,
                                    before_title,
                                    unit=before_frame.bunit,
                                    marker=(before_frame.cutout_pixel_x, before_frame.cutout_pixel_y),
                                    stretch_limits=shared_limits,
                                )
                            with right:
                                display_array(
                                    after_frame.image,
                                    after_title,
                                    unit=after_frame.bunit,
                                    marker=(after_frame.cutout_pixel_x, after_frame.cutout_pixel_y),
                                    stretch_limits=shared_limits,
                                )
                        with st.expander("How to interpret the comparison"):
                            st.write(
                                "These views support visual inspection. Measuring motion or brightness "
                                "requires image registration, compatible wavelengths, quality flags, "
                                "variance and PSF checks. High-proper-motion targets also need "
                                "coordinates propagated to each observation epoch."
                            )
                    else:
                        compare_index = None
                        warning = None
                st.download_button(
                    "Export observation list (CSV)",
                    observation_csv(
                        frames, target_name, float(ra), float(dec), selected,
                        compare_index, warning,
                    ),
                    file_name="orbitalq_observations.csv",
                    mime="text/csv",
                )
                st.download_button(
                    "Download discovery report",
                    report_text(
                        target_name, float(ra), float(dec), frames, selected,
                        compare_index, warning,
                    ),
                    file_name="orbitalq_discovery_report.md",
                    mime="text/markdown",
                )
            elif not errors:
                st.info("Upload Level 2 FITS files to begin.")

if view == "Home":
    render_home()
elif view == "Team":
    render_team()
elif view == "Documentation":
    render_documentation()
elif view == "About":
    render_about()
elif view == "Ready-to-view examples":
    show_packaged_examples()
elif view == "Official archive":
    render_official_archive()
else:
    with science_workspace:
        if view == "Real DR1 sky preview":
            render_spectral_preview()
        else:
            render_fits_workspace()

st.markdown(f"""
<footer class="oq-footer">
  <span>OrbitalQ · NASA Space Apps Challenge 2026</span>
  <a href="{REPO}">GitHub ↗</a>
  <a href="https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/">SPHEREx data ↗</a>
</footer>
""", unsafe_allow_html=True)
