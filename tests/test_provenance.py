from types import SimpleNamespace
import unittest

from core.provenance import report_text
from core.validation import chronological, comparison_warning


def frame(mjd, wavelength="2.4 um", detector="2"):
    return SimpleNamespace(
        mjd_obs=mjd, date_obs="2026-01-01", obsid="obs", detector=detector,
        bunit="MJy/sr",
        wavelength=wavelength, release="QR3", processing_version="l2b", filename="x.fits",
        source_url="https://example.invalid/x",
    )


class ProvenanceTests(unittest.TestCase):
    def test_observations_sort_by_actual_mjd(self):
        self.assertEqual([x.mjd_obs for x in chronological([frame(3), frame(1), frame(2)])], [1, 2, 3])

    def test_incompatible_wavelength_is_rejected_for_scientific_comparison(self):
        self.assertIn("wavelength", comparison_warning(frame(1), frame(2, wavelength="4.2 um")))

    def test_report_contains_provenance_fields(self):
        report = report_text("target", 1.0, -2.0, [frame(1)])
        self.assertIn("DATE-OBS", report)
        self.assertIn("OBSID", report)
        self.assertIn("https://example.invalid/x", report)
