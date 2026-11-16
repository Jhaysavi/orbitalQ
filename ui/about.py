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


def render_about():
    st.markdown("""
<section class="oq-about-intro">
  <h1>About the technology</h1>
  <p>OrbitalQ brings NASA SPHEREx data products into an explorer for visual inspection of infrared observations.</p>
</section>
""", unsafe_allow_html=True)
    st.subheader("Two views of the same sky")
    st.markdown("""
| Data product | What the explorer displays |
| --- | --- |
| Level 2 Spectral Images | Individual exposures ordered by their FITS observation times. Used for viewing visits in sequence or comparing a pair. |
| DR1 All-Sky Cube | A cutout at one of 102 nominal infrared wavelength channels in the built-in WISE 0855 field. |

### From sky coordinates to image pixels

Level 2 FITS files contain an image and a World Coordinate System (WCS).
OrbitalQ uses the WCS to locate the requested sky position and checks whether
the file covers it. When present, the viewer reads the matching **FLAGS** and
**VARIANCE** cutouts and records the original source, observation time, detector
and processing version.

### How to spot object motion

- **Anchor on background stars:** Fixed stars stay in place across visits; a nearby high-proper-motion or solar-system target shifts relative to them.
- **Use Time-lapse + Crosshair + Zoom:** Enable **Crosshair** and **2× / 3× Zoom** in the time-lapse player to spot small pixel-level displacements between epochs.
- **Verify with Swipe and metadata:** Drag **Swipe** or run **Auto-Blink A/B**, then check elapsed time, detector compatibility, **FLAGS**, and **VARIANCE** before interpreting a shift.

### What to check before measuring a change

Check image registration, wavelength and detector compatibility, quality
flags, uncertainty, and the effects of the point spread function and background.
For a moving target, account for its reference epoch and propagate the coordinates
to each observation date. A visible shift is a candidate for follow-up.
""")
    render_wise_field_resources()


def render_documentation():
    st.markdown("""
<section class="oq-about-intro">
  <h1>Documentation</h1>
  <p>Official U.S. data sources, software architecture, and proposed plans for running and evaluating OrbitalQ.</p>
</section>
""", unsafe_allow_html=True)

    references, business, sustainability, delivery, evaluation, research = st.tabs([
        "References and tools", "Business model", "Sustainability", "Delivery plan",
        "Success metrics", "Experimental roadmap",
    ])

    with references:
        st.markdown(f"""
| Official U.S. Resource | How OrbitalQ uses it |
| --- | --- |
| [NASA JPL SPHEREx Mission](https://www.jpl.nasa.gov/missions/spherex/) | Mission overview, 102-color infrared survey design, and science objectives. |
| [NASA/IPAC IRSA SPHEREx Archive](https://irsa.ipac.caltech.edu/Missions/spherex.html) · [User Guide](https://caltech-ipac.github.io/spherex-archive-documentation/) | Public FITS exposures, cloud archive browsing, and Level 2 provenance. |
| [SPHEREx DR1 Overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html) · [Explanatory Supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf) | All-Sky Cube channels, FITS product definitions, and calibration notes. |
| [NASA Science: WISE/NEOWISE](https://science.nasa.gov/mission/neowise/) · [STScI Pan-STARRS](https://ps1images.stsci.edu/cgi-bin/ps1cutouts) | Independent U.S. infrared and optical survey context for moving-object fields. |
| SPHEREx SkyShift (Ayoub, Abdou and Ilyes) | Processed Barnard’s Star and WISE 0855 cutouts included in the examples. [MIT license]({REPO}/blob/main/dist/licenses/skyshift.txt) |
| [Scientific methods]({REPO}/blob/main/docs/scientific-methods.md) · [Repository structure]({REPO}/blob/main/docs/repository-structure.md) · [Research notes]({REPO}/tree/main/study) | Implementation choices, coverage checks, limitations, and reproducible study scripts. |

### Application architecture (`app.py` entrypoint)

- **Streamlit entrypoint (`app.py`):** Renders the `Home`, `Solution`, `Team`, `Documentation`, and `About` pages, manages target coordinates, and runs the comparison workspace.
- **Core science modules (`core/`):** Handles IRSA archive listing (`archive.py`), coordinate resolution (`coordinates.py`), Level 2 FITS/WCS cutouts (`fits_reader.py`), provenance export (`provenance.py`), and chronological/unit validation (`validation.py`).
- **Interface components (`ui/`):** Provides the interactive `timeline.html` player (with **Zoom** and **Crosshair** motion aids), `swipe.html` A/B divider, `about.py`, `presentation.py`, and `explorer.css`.

The app uses **Python and Streamlit** for the interface, **Astropy** for FITS
and WCS handling, **NumPy and Matplotlib** for images, and **HTML, CSS, and
JavaScript** for playback and comparison controls.
""")

    with business:
        st.markdown("""
- OrbitalQ serves citizen scientists, educators and students exploring infrared observations.
- Keep the public explorer, example sequences and source links free to access.
- Seek support from education and citizen-science partners. Optional workshops could fund curriculum development and maintenance.
- Budget for hosting, archive bandwidth, and maintenance of samples and source links.
""")

    with sustainability:
        st.markdown("""
- Use the existing packaged cutouts for the public demo and cache public archive reads to limit repeat fetches.
- Keep FITS provenance and reproduction instructions with the project so another maintainer can verify the examples.
- Monitor download failures and broken source links. The FITS workspace supports local uploads when remote archive access is unavailable.
- Track hosting and data-transfer use before expanding the target catalogue.
""")

    with delivery:
        st.markdown("""
| Stage | Deliverable | Acceptance check |
| --- | --- | --- |
| Prototype | Packaged time-lapse, spectral preview and Level 2 FITS workspace | The examples open, dates follow the FITS metadata, and exposure links are available. |
| Pilot | Guided sessions with students, educators and citizen-science users | Users complete the baseline tasks below and report where they get stuck. |
| Next release | Improve onboarding and add targets with verified exposures | Each new sequence has dated frames, traceable FITS sources and documented coverage. |
""")

    with evaluation:
        st.caption("Proposed pilot targets. These are evaluation criteria for a future pilot.")
        st.markdown("""
| Measure | Proposed target | How to evaluate |
| --- | --- | --- |
| First exploration | At least 80% of 10 pilot users reach the second Barnard visit unaided within two minutes | Observe the task from the Home page and record completion time. |
| Data comprehension | At least 80% correctly distinguish an observation date from a wavelength channel | Ask one question after the time-lapse and spectral exercises. |
| Provenance | Every published example frame links to its original FITS exposure | Check each link and match its timestamp against the FITS header. |
| Coverage handling | Every out-of-field FITS fixture is rejected | Run the WCS validation tests and confirm the user-facing message in the workspace. |
""")

    with research:
        st.markdown("""
### Evidence-first candidate engine

The proposed engine would flag observations for human review and explain each
flag in a candidate card. The card would show the direction and magnitude of
the change, the supporting FITS exposures, measurement uncertainty, plausible
contamination or calibration effects, and any plausible catalogue counterpart.
Each card would expose the rule thresholds and mark missing measurements.

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

### Quantum research for shortlist selection

Run this as a separate research module after candidate evidence has been
computed. Given a fixed review budget, select a shortlist that balances
scientific interest, data quality and diversity. A QUBO would combine
candidate utility, pairwise similarity penalties and a penalty for departing
from the requested shortlist size.

Evaluate QAOA simulation or a quantum-inspired solver against classical
greedy and simulated-annealing baselines on the same input sets. Record
objective value, runtime, feasible shortlist rate and scaling as the candidate
pool grows. Use exact solutions on small instances to measure the gap from
the optimum. Report optimization performance under the measured conditions.
Claims about quantum advantage or discovery accuracy require separate evidence.
""")
