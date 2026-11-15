import numpy as np
import unittest

from core.coordinates import cutout_bounds, one_float


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
