import numpy as np
import unittest

from astropy.wcs import WCS

from core.coordinates import cutout_bounds, is_inside_image, one_float, pixel_scale_arcsec


class CoordinateTests(unittest.TestCase):
    def test_one_float_converts_one_element_array_to_python_float(self):
        value = one_float(np.array([12.25]), "x")
        self.assertIsInstance(value, float)
        self.assertEqual(value, 12.25)

    def test_one_float_rejects_multiple_coordinates(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            one_float(np.array([1.0, 2.0]), "x")

    def test_cutout_bounds_accepts_numpy_scalar_and_stays_in_image(self):
        self.assertEqual(cutout_bounds(np.array([2.4]), np.float64(8.6), 10, 12, 5), (0, 5, 7, 12))

    def test_image_footprint_includes_half_pixel_edges(self):
        self.assertTrue(is_inside_image(-0.49, 9.49, 10, 10))
        self.assertFalse(is_inside_image(-0.51, 5, 10, 10))
        self.assertFalse(is_inside_image(9.5, 5, 10, 10))

    def test_celestial_pixel_scale_is_reported_in_arcseconds(self):
        wcs = WCS(naxis=2)
        wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
        wcs.wcs.crval = [10.0, 20.0]
        wcs.wcs.crpix = [4.0, 4.0]
        wcs.wcs.cdelt = [-0.001, 0.001]
        self.assertEqual(pixel_scale_arcsec(wcs), (3.6, 3.6))
