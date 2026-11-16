"""Regression cases found during the technical QA pass."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import numpy as np
from astropy.io import fits
from core.archive import read_level2_headers, _padded_data_size
from core.validation import comparison_warning

def observation(**changes):
    values = dict(image=np.ones((3,3)), detector="1", bunit="MJy/sr",
                  release="DR1", processing_version="v1", wavelength="1.0",
                  mjd_obs=60000., pixel_scale_x_arcsec=6., pixel_scale_y_arcsec=6.)
    values.update(changes)
    return SimpleNamespace(**values)

class QaRegressionTests(unittest.TestCase):
    def test_missing_metadata_is_not_compatibility(self):
        for field in ("detector","bunit","release","processing_version"):
            with self.subTest(field=field):
                self.assertIn("incomplete", comparison_warning(
                    observation(**{field:"unknown"}), observation(mjd_obs=60001., **{field:"unknown"})))

    def test_missing_or_identical_times_warn(self):
        for time in (float("nan"), 60000.):
            self.assertIsNotNone(comparison_warning(observation(), observation(mjd_obs=time)))

    def test_unspecified_wavelength_range_warns(self):
        self.assertIn("wavelength", comparison_warning(
            observation(wavelength="header wavelength range present"),
            observation(mjd_obs=60001., wavelength="header wavelength range present")))

    def test_matching_known_metadata_has_no_metadata_warning(self):
        self.assertIsNone(comparison_warning(observation(), observation(mjd_obs=60001.)))

    def test_image_extension_need_not_be_first(self):
        primary=fits.PrimaryHDU().header
        table=fits.BinTableHDU.from_columns([], name="METADATA").header
        image=fits.ImageHDU(np.ones((3,3)), name="IMAGE").header
        with patch("core.archive._read_header", side_effect=[(primary,2880),(table,2880),(image,2880)]) as read:
            _, found=read_level2_headers("https://irsa.ipac.caltech.edu/test.fits", Mock())
        self.assertEqual(found["EXTNAME"], "IMAGE")
        self.assertEqual(read.call_count, 3)

    def test_missing_image_is_bounded(self):
        primary=fits.PrimaryHDU().header
        with patch("core.archive._read_header", return_value=(primary,2880)) as read:
            with self.assertRaisesRegex(ValueError,"No IMAGE"):
                read_level2_headers("https://irsa.ipac.caltech.edu/test.fits", Mock())
        self.assertEqual(read.call_count,33)

    def test_group_payload_size(self):
        header=fits.Header({"NAXIS":1,"NAXIS1":2000,"BITPIX":16,"PCOUNT":10,"GCOUNT":2})
        self.assertEqual(_padded_data_size(header),8640)

if __name__ == "__main__":
    unittest.main()
