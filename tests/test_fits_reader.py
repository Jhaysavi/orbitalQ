import io
import unittest

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u

from core.fits_reader import read_level2


def make_level2(image_data=None, flags_data=None, include_quality=True):
    header = fits.Header()
    header["NAXIS"] = 2
    header["NAXIS1"] = 8
    header["NAXIS2"] = 8
    header["CTYPE1"] = "RA---TAN"
    header["CTYPE2"] = "DEC--TAN"
    header["CRVAL1"] = 10.0
    header["CRVAL2"] = 20.0
    header["CRPIX1"] = 4.5
    header["CRPIX2"] = 4.5
    header["CDELT1"] = -0.001
    header["CDELT2"] = 0.001
    header["DATE-OBS"] = "2026-01-02T03:04:05"
    header["MJD-OBS"] = 61040.1278
    header["OBSID"] = "TEST-OBSID"
    header["DETECTOR"] = "2"
    header["BUNIT"] = "MJy/sr"
    header["RELEASE"] = "QR3"
    header["VERSION"] = "l2b-test"
    header["WAVELENGTH"] = "2.4 um"
    primary = fits.PrimaryHDU()
    image = fits.ImageHDU(
        np.arange(64, dtype=float).reshape(8, 8) if image_data is None else image_data,
        header=header,
        name="IMAGE",
    )
    hdus = [fits.PrimaryHDU(), image]
    if include_quality:
        flags = fits.ImageHDU(
            np.zeros((8, 8), dtype=np.int64) if flags_data is None else flags_data,
            name="FLAGS",
        )
        variance = fits.ImageHDU(np.ones((8, 8), dtype=float), name="VARIANCE")
        hdus.extend([flags, variance])
    stream = io.BytesIO()
    fits.HDUList(hdus).writeto(stream)
    stream.seek(0)
    return stream


class FitsReaderTests(unittest.TestCase):
    def test_level2_metadata_wcs_and_quality_planes_are_read(self):
        target = SkyCoord(10.0 * u.deg, 20.0 * u.deg, frame="icrs")
        obs = read_level2(make_level2(), target, 5, "realistic-test.fits", "https://example.invalid/object")
        self.assertEqual(obs.obsid, "TEST-OBSID")
        self.assertTrue(obs.date_obs.startswith("2026-01-02"))
        self.assertEqual(obs.mjd_obs, 61040.1278)
        self.assertEqual(obs.detector, "2")
        self.assertEqual(obs.release, "QR3")
        self.assertEqual(obs.release_source, "FITS header")
        self.assertEqual(obs.wavelength, "2.4 um")
        self.assertAlmostEqual(obs.cutout_pixel_x, 1.5)
        self.assertAlmostEqual(obs.cutout_pixel_y, 2.5)
        self.assertEqual(obs.flags.shape, (5, 5))
        self.assertEqual(obs.variance.shape, (5, 5))
        self.assertAlmostEqual(obs.pixel_scale_x_arcsec, 3.6)
        self.assertAlmostEqual(obs.pixel_scale_y_arcsec, 3.6)
        self.assertTrue(obs.source_url.endswith("object"))

    def test_release_can_be_derived_from_official_archive_path_when_header_omits_it(self):
        stream = io.BytesIO()
        with fits.open(make_level2()) as hdul:
            del hdul["IMAGE"].header["RELEASE"]
            hdul.writeto(stream)
        stream.seek(0)
        obs = read_level2(
            stream,
            SkyCoord(10.0 * u.deg, 20.0 * u.deg),
            5,
            "dr1-observation.fits",
            source_url=(
                "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
                "dr1/level2/2026W01/run/1/dr1-observation.fits"
            ),
        )
        self.assertEqual(obs.release, "DR1")
        self.assertEqual(obs.release_source, "public archive URL")

    def test_date_obs_can_supply_missing_mjd_obs(self):
        stream = make_level2()
        with fits.open(stream, mode="update") as hdul:
            del hdul["IMAGE"].header["MJD-OBS"]
            hdul.flush()
            stream.seek(0)
            obs = read_level2(stream, SkyCoord(10.0 * u.deg, 20.0 * u.deg), 5, "date-only.fits")
        self.assertTrue(np.isfinite(obs.mjd_obs))

    def test_missing_quality_extensions_are_reported(self):
        obs = read_level2(
            make_level2(include_quality=False),
            SkyCoord(10.0 * u.deg, 20.0 * u.deg),
            5,
            "no-quality.fits",
        )
        self.assertIsNone(obs.flags)
        self.assertIsNone(obs.variance)
        self.assertEqual(obs.extension_issues["FLAGS"], "extension is missing")
        self.assertEqual(obs.extension_issues["VARIANCE"], "extension is missing")

    def test_quality_extension_with_incompatible_dimensions_is_reported(self):
        flags = np.zeros((7, 8), dtype=np.int16)
        obs = read_level2(
            make_level2(flags_data=flags),
            SkyCoord(10.0 * u.deg, 20.0 * u.deg),
            5,
            "mismatched-quality.fits",
        )
        self.assertIsNone(obs.flags)
        self.assertIn("do not match IMAGE dimensions", obs.extension_issues["FLAGS"])

    def test_nan_values_are_preserved_in_image_and_flags(self):
        image = np.full((8, 8), np.nan)
        flags = np.zeros((8, 8), dtype=float)
        flags[2, 2] = np.nan
        obs = read_level2(
            make_level2(image_data=image, flags_data=flags),
            SkyCoord(10.0 * u.deg, 20.0 * u.deg),
            5,
            "nan-values.fits",
        )
        self.assertFalse(np.isfinite(obs.image).any())
        self.assertTrue(np.isnan(obs.flags).any())

    def test_file_without_image_extension_is_rejected(self):
        stream = io.BytesIO()
        fits.HDUList([fits.PrimaryHDU()]).writeto(stream)
        stream.seek(0)
        with self.assertRaisesRegex(ValueError, "No IMAGE extension"):
            read_level2(stream, SkyCoord(10.0 * u.deg, 20.0 * u.deg), 5, "incomplete.fits")

    def test_invalid_fits_bytes_are_rejected(self):
        with self.assertRaises(Exception):
            read_level2(
                io.BytesIO(b"not a FITS file"),
                SkyCoord(10.0 * u.deg, 20.0 * u.deg),
                5,
                "invalid.fits",
            )

    def test_coordinate_on_half_pixel_edge_is_inside_and_cutout_is_bounded(self):
        with fits.open(make_level2()) as hdul:
            wcs = WCS(hdul["IMAGE"].header).celestial
        target = wcs.pixel_to_world(-0.49, 3.0)
        obs = read_level2(make_level2(), target, 5, "edge.fits")
        self.assertEqual(obs.image.shape, (5, 5))
        self.assertGreaterEqual(obs.cutout_pixel_x, -0.5)
        self.assertLess(obs.cutout_pixel_x, obs.image.shape[1] - 0.5)

    def test_coordinate_outside_half_pixel_boundary_is_rejected(self):
        header = make_level2()
        with fits.open(header) as hdul:
            wcs = WCS(hdul["IMAGE"].header).celestial
        target = wcs.pixel_to_world(-0.51, 3.0)
        with self.assertRaisesRegex(ValueError, "outside image footprint"):
            read_level2(make_level2(), target, 5, "outside.fits")
