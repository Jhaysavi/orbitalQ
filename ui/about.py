"""Public introduction and getting-started guide for OrbitalQ."""

import streamlit as st

REPO = "https://github.com/SouBeatrizKaroline/NasaSpaceApp_OrbitalQ"

WISE_FIELD = "133.786245 -7.244372"
PANSTARRS_CUTOUT = (
    "https://ps1images.stsci.edu/cgi-bin/ps1cutouts?pos=133.786245+-7.244372"
    "&filter=color&filter=g&filter=r&filter=i&filter=z&filter=y"
    "&filetypes=stack&auxiliary=data&size=240&output_size=0&verbose=0"
    "&autoscale=99.500000&catlist="
)
WISEVIEW = "https://byw.tools/wiseview"


def render_wise_field_resources():
    """Link to independent survey views for the WISE 0855 study field."""
    with st.expander("Explore the WISE 0855 field in other surveys"):
        st.markdown(
            f"**Reference field:** RA and Dec in degrees: `{WISE_FIELD}`. "
            "These links open external survey tools."
        )
        optical, infrared = st.columns(2)
        with optical:
            st.link_button("Open Pan-STARRS cutout", PANSTARRS_CUTOUT, use_container_width=True)
            st.caption("Inspect the optical stack and individual filters from the STScI archive.")
        with infrared:
            st.link_button("Open WiseView", WISEVIEW, use_container_width=True)
            st.caption("Enter the reference coordinates above to explore infrared images across WISE epochs.")
        st.info(
            "Start with surrounding stars as reference points. Wavelength, observing epoch "
            "and image resolution can change a source’s appearance across surveys."
        )
        st.markdown(
            "[Pan-STARRS service guide](https://outerspace.stsci.edu/pages/viewpage.action?pageId=398524447) · "
            "[WiseView documentation](https://github.com/backyardworlds/wiseview)"
        )


def open_view(view, action=None):
    st.session_state["explorer_view"] = view
    if action is not None:
        action()


def render_about(load_example):
    st.markdown("""
<section class="oq-about-intro" aria-labelledby="about-title">
  <div class="oq-section-label">NASA Space Apps 2026 / Planet X and SPHEREx</div>
  <h2 id="about-title">About OrbitalQ</h2>
  <p>What can you learn by looking at the same patch of sky twice? OrbitalQ puts real NASA SPHEREx observations in a browser so anyone can explore infrared light and look for changes between visits.</p>
</section>
""", unsafe_allow_html=True)
    example, spectral = st.columns(2)
    example.button(
        "Try two real observations", type="primary", on_click=open_view,
        args=("Compare Level 2 visits", load_example), use_container_width=True,
    )
    spectral.button(
        "Explore the infrared sky", on_click=open_view,
        args=("Real DR1 sky preview",), use_container_width=True,
    )
    st.markdown("""
<section class="oq-about-section" aria-labelledby="getting-started">
  <h3 id="getting-started">Your first observation</h3>
  <ol class="oq-about-grid">
    <li><h4>Open the real example</h4><p>The app loads two public images and shows its progress as it checks that each exposure covers the example field.</p></li>
    <li><h4>Compare the images</h4><p>Drag Swipe across the image, switch between visits with Blink, or place the images side by side. Look for points that seem to move relative to their neighbours.</p></li>
    <li><h4>Follow the evidence</h4><p>Open Observation timeline to see dates and detectors. Use Quality and provenance to inspect data flags and file sources. You can export the observation list as a CSV.</p></li>
  </ol>
</section>
<section class="oq-about-section" aria-labelledby="studies">
  <h3 id="studies">Two things to try</h3>
  <div class="oq-about-grid oq-about-pair">
    <article><div class="oq-section-label">Wavelength</div><h4>Explore the WISE 0855−0714 field</h4><p>In Real DR1 sky preview, choose the WISE preset and change the channel. The 102 channels represent different wavelengths of infrared light. Compare how the same field looks as you move the slider.</p></article>
    <article><div class="oq-section-label">Time</div><h4>Compare two visits to one field</h4><p>Start with the public example, then try your own Level 2 FITS files. Check the duration between visits and use surrounding stars as reference points.</p></article>
  </div>
</section>
""", unsafe_allow_html=True)
    render_wise_field_resources()
    with st.expander("Using your own files"):
        st.markdown(
            "Set a sky position in **Target coordinates**, then open **Compare Level 2 visits**. "
            "Browse public SPHEREx folders, paste a public FITS link, or upload files "
            "you already downloaded. Folder browsing lists archive files. When you load a file, "
            "OrbitalQ checks its sky coordinates to confirm it covers your target."
        )
    with st.expander("What counts as evidence of change?"):
        st.markdown(
            "The All-Sky Cube shows spectral context. Comparisons over time use separate "
            "Level 2 observations with their own timestamps. An apparent shift is a clue "
            "to investigate. Compare wavelengths and quality flags, then check image alignment "
            "and measurement uncertainty before drawing a conclusion."
        )

    st.subheader("Documentation and data")
    st.markdown(
        f"[Scientific methods]({REPO}/blob/main/docs/scientific-methods.md) · "
        f"[Research notes and scripts]({REPO}/tree/main/study) · "
        f"[Project code]({REPO})"
    )
    st.markdown(
        "[SPHEREx DR1 overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html) · "
        "[Data products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/) · "
        "[Data releases](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-releases/)"
    )
    st.subheader("Meet the team")
    st.markdown("""
<div class="oq-about-grid oq-about-pair">
  <a href="https://aspiraqualquer.vercel.app/"><strong>Aspira Qualquer</strong><span>Visit portfolio ↗</span></a>
  <a href="https://jhay.goskip.app/"><strong>Jay</strong><span>Visit portfolio ↗</span></a>
</div>
""", unsafe_allow_html=True)
