"""Technical information, project documentation, and external survey links."""

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
    with st.expander("Explore the WISE 0855 field in other U.S. surveys"):
        st.markdown(
            f"**Reference field:** RA and Dec in degrees: `{WISE_FIELD}`. "
            "Compare SPHEREx cutouts against independent U.S. optical and infrared archives."
        )
        optical, infrared = st.columns(2)
        with optical:
            st.link_button("Open STScI Pan-STARRS cutout", PANSTARRS_CUTOUT, use_container_width=True)
            st.caption("Inspect the optical stack and individual filters from the STScI archive.")
        with infrared:
            st.link_button("Open WiseView", WISEVIEW, use_container_width=True)
            st.caption("Enter the reference coordinates above to explore infrared images across WISE epochs.")
        st.info(
            "Anchor on surrounding background stars first. Wavelength, observing epoch, "
            "and spatial resolution all affect how a moving source appears across surveys."
        )
        st.markdown(
            "[Pan-STARRS service guide](https://outerspace.stsci.edu/pages/viewpage.action?pageId=398524447) · "
            "[WiseView documentation](https://github.com/backyardworlds/wiseview)"
        )



def _render_info_styles():
    st.markdown("""
<style>
.oq-info-hero { padding:clamp(1.5rem,4vw,3.2rem); border:1px solid #53405f; border-radius:24px;
    background:radial-gradient(ellipse at 95% 0%,#65417a55,transparent 60%),linear-gradient(135deg,#24192e,#14111e); margin:.5rem 0 1.6rem; }
.oq-info-hero h1 { color:#f6f0ff; font-size:clamp(2.1rem,4.5vw,3.6rem); line-height:1.1; letter-spacing:-.045em; padding:.5rem 0 1rem; }
.oq-info-hero p:last-child { color:#c9bfd9; max-width:68ch; line-height:1.75; margin:0; }
.oq-info-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; margin:1rem 0 1.5rem; }
.oq-info-grid.oq-info-three { grid-template-columns:repeat(3,minmax(0,1fr)); }
.oq-info-card { min-width:0; padding:clamp(1.2rem,2.4vw,1.8rem); border:1px solid #46364f; border-radius:18px;
    background:linear-gradient(145deg,#21192c,#15111f); display:flex; flex-direction:column; gap:.6rem; }
.oq-info-card h3 { margin:0; padding:0; font-size:1.25rem; color:#f6f0ff; letter-spacing:-.02em; }
.oq-info-card p { color:#c9bfd9; line-height:1.7; margin:0; }
.oq-info-tag { color:#ffc785; font:600 .72rem/1.5 monospace; letter-spacing:.07em; text-transform:uppercase; }
.oq-info-links { display:flex; flex-wrap:wrap; gap:.5rem; margin-top:auto; padding-top:.7rem; }
.oq-info-links a { display:inline-flex; align-items:center; min-height:44px; padding:.55rem .8rem; border:1px solid #695275;
    border-radius:10px; color:#ead8ff !important; text-decoration:none; font-size:.85rem; background:#30223d; }
.oq-info-links a:hover { background:#493255; border-color:#dac2ff; }
.oq-info-links a:focus-visible { outline:3px solid #ffc785; outline-offset:3px; }
.oq-info-callout { margin:1.2rem 0; padding:1.2rem 1.4rem; border-left:3px solid #ffc785;
    border-radius:0 14px 14px 0; background:#241b2d; color:#d3c8e0; line-height:1.7; }
[role="tablist"] { gap:.5rem; flex-wrap:wrap; height:auto; margin-bottom:1rem; border:0; }
button[role="tab"] { height:auto; min-height:44px; padding:.7rem 1rem; border:1px solid #493953; border-radius:12px; background:#1b1525; }
button[role="tab"][aria-selected="true"] { background:#423044; color:#ffdaac; border-color:#b68a66; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display:none; }
[role="tabpanel"] { padding-top:.5rem; }
@media(max-width:900px) { .oq-info-grid.oq-info-three { grid-template-columns:1fr; } }
@media(max-width:640px) { .oq-info-grid { grid-template-columns:1fr; } }
.st-key-oq-doc-section button { min-height:46px; padding:.65rem 1rem; border-radius:12px; border:1px solid #594365; background:#21182d; color:#dacfe7; }
.st-key-oq-doc-section button[aria-pressed="true"] { background:#483045; color:#ffe0b5; border-color:#b98d69; }
.st-key-oq-doc-section button:focus-visible { outline:3px solid #ffc785; outline-offset:3px; }
</style>
""", unsafe_allow_html=True)


def render_about():
    _render_info_styles()
    st.markdown("""
<section class="oq-info-hero">
  <p class="oq-info-tag">Behind the explorer · NASA Space Apps 2026</p>
  <h1>One sky.<br>Different moments.</h1>
  <p>OrbitalQ brings dated NASA SPHEREx observations into one workspace. Follow a field through time, inspect its infrared light, and trace what you see back to the original data.</p>
</section>
<h2>Start with three simple steps</h2>
<div class="oq-info-grid oq-info-three">
  <article class="oq-info-card"><span class="oq-info-tag">01 / Find your anchors</span><h3>Look at nearby stars</h3><p>Use surrounding background stars as reference points. Check alignment before interpreting a shift in the target.</p></article>
  <article class="oq-info-card"><span class="oq-info-tag">02 / Follow the dates</span><h3>Play, pause, inspect</h3><p>Use Time-lapse, Zoom, and Crosshair to inspect visits. Switch to Swipe or Auto-Blink to compare two observations.</p></article>
  <article class="oq-info-card"><span class="oq-info-tag">03 / Check the evidence</span><h3>Open the FITS source</h3><p>Compare observation times, detector, wavelength, quality flags, and uncertainty before interpreting a change.</p></article>
</div>
<h2>Two ways to explore</h2>
<div class="oq-info-grid">
  <article class="oq-info-card"><span class="oq-info-tag">Time / Level 2 exposures</span><h3>The sky across visits</h3><p>Individual exposures are ordered by their FITS observation times. Time-lapse, Swipe, and Blink help you inspect the same field at different moments.</p></article>
  <article class="oq-info-card"><span class="oq-info-tag">Wavelength / DR1 All-Sky Cube</span><h3>The sky in infrared light</h3><p>Explore 102 nominal wavelength channels in the built-in WISE 0855 reference field. Each channel samples a part of the spectrum.</p></article>
</div>
<div class="oq-info-callout"><strong>Wavelength is not time.</strong> The cube’s 102 spectral channels do not represent 102 dates. A temporal sequence needs separate, dated observations.</div>
""", unsafe_allow_html=True)
    with st.expander("How sky coordinates become image pixels"):
        st.markdown(
            "Each Level 2 FITS file includes a **World Coordinate System (WCS)**. "
            "OrbitalQ uses it to check field coverage and extract a target-centred cutout. "
            "Matching **FLAGS** and **VARIANCE** layers are retained when available, alongside "
            "the source URL, observation time, detector, and processing version."
        )
    with st.expander("Before measuring motion or brightness"):
        st.markdown(
            "Check image registration, wavelength and detector compatibility, quality flags, "
            "uncertainty, and point-spread-function or background effects. For moving targets, "
            "propagate reference coordinates to the observation epoch. A visible difference "
            "is a candidate for investigation, not a confirmed detection."
        )
    render_wise_field_resources()


def render_documentation():
    _render_info_styles()
    st.markdown("""
<section class="oq-info-hero">
  <p class="oq-info-tag">The knowledge behind OrbitalQ</p>
  <h1>Explore the evidence.</h1>
  <p>Find the official archives, understand how the explorer works, and follow the plans for what comes next.</p>
</section>
""", unsafe_allow_html=True)

    section = st.segmented_control(
        "Documentation section",
        ["Sources", "Business", "Sustainability", "Delivery", "Metrics", "Research"],
        default="Sources", key="oq-doc-section",
    ) or "Sources"

    if section == "Sources":
        st.markdown(f"""
<h2>Sources you can trace</h2>
<div class="oq-info-grid">
  <article class="oq-info-card"><span class="oq-info-tag">NASA / JPL</span><h3>SPHEREx mission</h3><p>Start with the mission’s infrared survey design and science objectives.</p><div class="oq-info-links"><a href="https://www.jpl.nasa.gov/missions/spherex/">Mission overview ↗</a></div></article>
  <article class="oq-info-card"><span class="oq-info-tag">NASA / IPAC IRSA</span><h3>SPHEREx observations</h3><p>Find original FITS exposures, release information, and the archive’s data-access guide.</p><div class="oq-info-links"><a href="https://irsa.ipac.caltech.edu/Missions/spherex.html">Open archive ↗</a><a href="https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/">Access guide ↗</a></div></article>
  <article class="oq-info-card"><span class="oq-info-tag">NASA / IPAC IRSA</span><h3>Data products & calibration</h3><p>Understand spectral channels, Level 2 image extensions, and calibration requirements.</p><div class="oq-info-links"><a href="https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html">DR1 overview ↗</a><a href="https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf">Technical supplement ↗</a></div></article>
  <article class="oq-info-card"><span class="oq-info-tag">NASA / IPAC IRSA</span><h3>WISE & NEOWISE</h3><p>Explore complementary infrared observations and build coadds from individual exposures.</p><div class="oq-info-links"><a href="https://irsa.ipac.caltech.edu/data/WISE/docs/release/NEOWISE/">Final data release ↗</a><a href="https://irsa.ipac.caltech.edu/applications/ICORE/">WISE coadder ↗</a></div></article>
  <article class="oq-info-card"><span class="oq-info-tag">STScI / MAST</span><h3>Pan-STARRS optical context</h3><p>Inspect optical images around a sky position using the official image cutout service.</p><div class="oq-info-links"><a href="https://ps1images.stsci.edu/cgi-bin/ps1cutouts">Image cutouts ↗</a><a href="https://mast.stsci.edu">MAST portal ↗</a></div></article>
  <article class="oq-info-card"><span class="oq-info-tag">Project documentation</span><h3>Methods & reproducibility</h3><p>Trace the implementation, research notes, and scientific limitations.</p><div class="oq-info-links"><a href="{REPO}/blob/main/docs/scientific-methods.md">Scientific methods ↗</a><a href="{REPO}/blob/main/docs/repository-structure.md">Repository guide ↗</a><a href="{REPO}/tree/main/study">Research notes ↗</a></div></article>
</div>
<div class="oq-info-callout"><strong>Expand the search.</strong> IRSA’s official SPHEREx SIA2 service supports position, wavelength, and time queries across DR1 and QR3, including deep-field collections. WISE and Pan-STARRS provide complementary survey context. These archive links do not add new validated time-lapse frames to OrbitalQ automatically.</div>
""", unsafe_allow_html=True)
        st.subheader("How the explorer is built")
        st.markdown("""
<div class="oq-info-grid oq-info-three">
  <article class="oq-info-card"><span class="oq-info-tag">01 / Application</span><h3>Your workspace</h3><p>Python and Streamlit connect page navigation, target selection, and observation controls through app.py.</p></article>
  <article class="oq-info-card"><span class="oq-info-tag">02 / Science</span><h3>Coordinates & evidence</h3><p>Core modules handle FITS, WCS, chronology, quality checks, and provenance with Astropy and NumPy.</p></article>
  <article class="oq-info-card"><span class="oq-info-tag">03 / Presentation</span><h3>Visual comparison</h3><p>HTML, CSS, JavaScript, and Matplotlib power the time-lapse, swipe controls, and image rendering.</p></article>
</div>
""", unsafe_allow_html=True)
        with st.expander("Third-party credits and licensing"):
            st.markdown(
                "SPHEREx SkyShift (Ayoub, Abdou and Ilyes) supplied processed Barnard’s Star "
                "and WISE 0855 cutouts used in the packaged examples. This is a third-party "
                "processing credit, distinct from the official mission archives. "
                f"[Read the MIT license]({REPO}/blob/main/dist/licenses/skyshift.txt)."
            )

    if section == "Business":
        st.markdown("""
<h2>Open exploration. A plan to sustain it.</h2>
<p style="color:#c9bfd9;max-width:70ch;line-height:1.7">Proposed operating model · Designed around public access, education, and long-term maintenance.</p>
<div class="oq-info-grid">
<article class="oq-info-card"><span class="oq-info-tag">Who it serves</span><h3>Curiosity has many starting points</h3><p>Citizen scientists, educators, and students exploring real infrared observations.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">Public access</span><h3>Keep the doorway open</h3><p>Maintain free access to the public explorer, example sequences, and original FITS source links.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">Potential support</span><h3>Build with education partners</h3><p>Seek STEM and citizen-science partnerships to support learning materials and maintenance. Partnerships are a proposed route, not confirmed commitments.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">Operating costs</span><h3>Fund the work behind the images</h3><p>Plan for hosting, archive bandwidth, software maintenance, and curation of verified observation sequences.</p></article>
</div>
""", unsafe_allow_html=True)

    if section == "Sustainability":
        st.markdown("""
<h2>Keep exploration dependable.</h2>
<p style="color:#c9bfd9;max-width:70ch;line-height:1.7">Operational practices and planned improvements for a maintainable public tool.</p>
<div class="oq-info-grid">
<article class="oq-info-card"><span class="oq-info-tag">Efficient access</span><h3>Reuse what is already prepared</h3><p>Packaged examples and cached archive queries reduce repeated downloads and help the first exploration load quickly.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">Reproducibility</span><h3>Keep the trail back to the data</h3><p>Preserve FITS provenance and reproduction scripts so maintainers can audit each published example.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">Resilience</span><h3>Prepare for unavailable archives</h3><p>Retain packaged examples and local FITS uploads. Monitor failed downloads and broken source links as part of maintenance.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">Responsible growth</span><h3>Expand at a measured pace</h3><p>Track hosting and data-transfer usage before growing the packaged catalogue. New sequences need validation and documented provenance.</p></article>
</div>
""", unsafe_allow_html=True)

    if section == "Delivery":
        st.markdown("""
<h2>From working prototype to a useful learning tool.</h2>
<p style="color:#c9bfd9;max-width:70ch;line-height:1.7">Delivery roadmap · Later stages are planned and depend on validation.</p>
<div class="oq-info-grid">
<article class="oq-info-card"><span class="oq-info-tag">01 / Prototype</span><h3>Make the first exploration work</h3><p>Packaged time-lapse, Zoom, Crosshair, spectral preview, and FITS workspace.<br><br><strong>Acceptance:</strong> Examples load, dates match FITS metadata, and source links resolve.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">02 / Planned pilot</span><h3>Learn from real sessions</h3><p>Guided exploration with students, educators, and citizen-science reviewers.<br><br><strong>Acceptance:</strong> Record task completion and identify usability problems.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">03 / Planned release</span><h3>Expand the verified catalogue</h3><p>Add multi-epoch IRSA sequences only after acquisition and validation.<br><br><strong>Acceptance:</strong> Every sequence includes dated frames, original FITS links, and WCS coverage checks.</p></article>
</div>
""", unsafe_allow_html=True)

    if section == "Metrics":
        st.markdown("""
<h2>Measure whether exploration becomes easier.</h2>
<p style="color:#c9bfd9;max-width:70ch;line-height:1.7">Proposed pilot criteria · These are targets to evaluate, not achieved results.</p>
<div class="oq-info-grid">
<article class="oq-info-card"><span class="oq-info-tag">First exploration</span><h3>80% within two minutes</h3><p>Target: at least 8 of 10 pilot users reach the second Barnard visit unaided. Observe from the Home page and record completion time.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">Data comprehension</span><h3>80% distinguish time from wavelength</h3><p>Ask participants a question after the time-lapse and spectral exercises to evaluate their understanding.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">Provenance</span><h3>Every frame has a source</h3><p>Check that each published example links to its original FITS exposure and that its timestamp matches the header.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">Coverage handling</span><h3>Reject out-of-field fixtures</h3><p>Use WCS validation tests and inspect the user-facing message to confirm that fixtures outside the image footprint are rejected.</p></article>
</div>
""", unsafe_allow_html=True)

    if section == "Research":
        st.markdown("""
<h2>Research with evidence at its centre.</h2>
<p style="color:#c9bfd9;max-width:70ch;line-height:1.7">Experimental roadmap · These approaches require implementation and evaluation before any performance claim.</p>
<div class="oq-info-grid">
<article class="oq-info-card"><span class="oq-info-tag">Candidate review</span><h3>Explain why a field was flagged</h3><p>A proposed evidence card would connect measured changes to observations, uncertainty, quality, and plausible alternative explanations.</p></article>
<article class="oq-info-card"><span class="oq-info-tag">Optional optimization</span><h3>Prioritize a review shortlist</h3><p>Explore candidate diversity and scientific interest under a limited review budget. Compare against classical methods before drawing conclusions.</p></article>
</div>
""", unsafe_allow_html=True)

        with st.expander("Candidate engine: evidence and evaluation", expanded=True):
            st.markdown("""
### Evidence-first candidate engine

The proposed engine would flag observations for human review and explain each
flag in a candidate card. The card would show the direction and magnitude of
the change, supporting FITS exposures, measurement uncertainty, plausible
contamination or calibration effects, and any plausible catalogue counterpart.
Each card would expose rule thresholds and mark missing measurements.

| Evidence | What the prototype would evaluate |
| --- | --- |
| Motion significance | Displacement after image registration relative to positional uncertainty and astrometric systematics. |
| Flux variability | Change in brightness relative to its uncertainty across compatible observations. |
| Spectral distinctiveness | Differences from an appropriate comparison population, given the available spectral measurements. |
| Observation quality | Valid pixels, flags, signal-to-noise, and available calibration and PSF information. |
| Catalogue status | Plausible counterparts after cross-matching at the observation epoch, with match separation and ambiguous matches recorded. |

Begin with versioned, rule-based indicators. Use the five hand-picked targets
to exercise the workflow. Evaluate thresholds on independent samples and
controls, then report false positives by artifact type and agreement with
reviewer assessments. Any prioritization score represents review urgency.
Training a general ranking model would require a larger representative
labelled dataset.

""")
        with st.expander("Optional quantum research: method and benchmarks"):
            st.markdown("""

Run this as a separate research module after candidate evidence has been
computed. Given a fixed review budget, select a shortlist that balances
scientific interest, data quality, and diversity. A QUBO would combine
candidate utility, pairwise similarity penalties, and a penalty for departing
from the requested shortlist size.

Evaluate QAOA simulation or a quantum-inspired solver against classical
greedy and simulated-annealing baselines on the same input sets. Record
objective value, runtime, feasible shortlist rate, and scaling as the candidate
pool grows. Use exact solutions on small instances to measure the gap from
the optimum. Report optimization performance under the measured conditions.
Claims about quantum advantage or discovery accuracy require separate evidence.
""")
