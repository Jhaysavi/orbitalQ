import io
import unittest

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u

from core.fits_reader import read_level2


def make_level2():
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
    image = fits.ImageHDU(np.arange(64, dtype=float).reshape(8, 8), header=header, name="IMAGE")
    flags = fits.ImageHDU(np.zeros((8, 8), dtype=np.int64), name="FLAGS")
    variance = fits.ImageHDU(np.ones((8, 8), dtype=float), name="VARIANCE")
    stream = io.BytesIO()
    fits.HDUList([primary, image, flags, variance]).writeto(stream)
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
        self.assertEqual(obs.wavelength, "2.4 um")
        self.assertEqual(obs.flags.shape, (5, 5))
        self.assertEqual(obs.variance.shape, (5, 5))
        self.assertTrue(obs.source_url.endswith("object"))
