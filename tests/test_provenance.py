from types import SimpleNamespace
import unittest

import numpy as np

from core.provenance import report_text
from core.validation import chronological, comparison_warning


def frame(mjd, wavelength="2.4 um", detector="2"):
    return SimpleNamespace(
        mjd_obs=mjd, date_obs="2026-01-01", obsid="obs", detector=detector,
        bunit="MJy/sr",
        wavelength=wavelength, release="QR3", release_source="FITS header",
        processing_version="l2b", filename="x.fits",
        source_url="https://example.invalid/x",
        image=np.ones((5, 5)),
        flags=np.zeros((5, 5)),
        variance=np.ones((5, 5)),
        reference_epoch="J2000",
        pixel_scale_x_arcsec=3.6,
        pixel_scale_y_arcsec=3.6,
    )


class ProvenanceTests(unittest.TestCase):
    def test_observations_sort_by_actual_mjd(self):
        self.assertEqual([x.mjd_obs for x in chronological([frame(3), frame(1), frame(2)])], [1, 2, 3])

    def test_incompatible_wavelength_is_rejected_for_scientific_comparison(self):
        self.assertIn("wavelength", comparison_warning(frame(1), frame(2, wavelength="4.2 um")))

    def test_incompatible_processing_version_is_rejected(self):
        later = frame(2)
        later.processing_version = "l2b-v28"
        self.assertIn("processing versions", comparison_warning(frame(1), later))

    def test_report_contains_provenance_fields(self):
        report = report_text("target", 1.0, -2.0, [frame(1)], 0, None)
        self.assertIn("DATE-OBS", report)
        self.assertIn("OBSID", report)
        self.assertIn("https://example.invalid/x", report)
        self.assertIn("25/25", report)
        self.assertIn("Median VARIANCE", report)

    def test_report_records_selected_pair_and_incompatibility(self):
        report = report_text(
            "target", 1.0, -2.0, [frame(1), frame(2)], 0, 1, "detectors differ"
        )
        self.assertIn("Selected: x.fits", report)
        self.assertIn("not comparable — detectors differ", report)

    def test_cutouts_with_different_dimensions_are_not_comparable(self):
        later = frame(2)
        later.image = np.ones((3, 3))
        self.assertIn("cutout dimensions differ", comparison_warning(frame(1), later))

    def test_cutouts_with_different_pixel_scales_are_not_comparable(self):
        later = frame(2)
        later.pixel_scale_x_arcsec = 4.0
        self.assertIn("pixel scales differ", comparison_warning(frame(1), later))
