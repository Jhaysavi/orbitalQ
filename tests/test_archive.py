from io import BytesIO
import unittest
from unittest.mock import patch

import requests
from astropy.coordinates import SkyCoord
from astropy.table import Table
import astropy.units as u

from core.archive import (
    is_supported_spherex_url,
    list_spherex_level2_files,
    list_spherex_prefixes,
    resolve_archive_url,
    search_level2_footprints,
)


def http_response(body, status=200):
    response = requests.Response()
    response.status_code = status
    response.url = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
    response._content = body.encode()
    return response


class ArchiveTests(unittest.TestCase):
    def test_archive_urls_preserve_absolute_sources(self):
        url = "https://example.invalid/observation.fits"
        self.assertEqual(resolve_archive_url(url), url)

    def test_s3_key_is_resolved_to_public_bucket(self):
        url = resolve_archive_url("s3://nasa-irsa-spherex/dr1/level2/example.fits")
        self.assertEqual(
            url,
            "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/dr1/level2/example.fits",
        )

    def test_relative_archive_uri_uses_irsa_root(self):
        self.assertEqual(
            resolve_archive_url("/ibe/data/spherex/example.fits"),
            "https://irsa.ipac.caltech.edu/ibe/data/spherex/example.fits",
        )

    def test_manual_remote_loading_only_accepts_public_https_archive_hosts(self):
        self.assertTrue(is_supported_spherex_url(
            "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/dr1/level2/observation.fits"
        ))
        self.assertTrue(is_supported_spherex_url(
            "https://irsa.ipac.caltech.edu/ibe/data/spherex/observation.fits"
        ))
        self.assertFalse(is_supported_spherex_url("http://irsa.ipac.caltech.edu/file.fits"))
        self.assertFalse(is_supported_spherex_url("https://example.invalid/file.fits"))
        self.assertFalse(is_supported_spherex_url("https://irsa.ipac.caltech.edu.evil.invalid/file.fits"))
        self.assertFalse(is_supported_spherex_url("https://irsa.ipac.caltech.edu:8443/file.fits"))
        self.assertFalse(is_supported_spherex_url("https://irsa.ipac.caltech.edu/metadata"))

    def test_search_timeout_is_reported_without_claiming_no_coverage(self):
        target = SkyCoord(133.795129 * u.deg, -7.245147 * u.deg)
        with patch("requests.Session.get", side_effect=requests.Timeout("timed out")):
            result = search_level2_footprints(
                target, 133.795129, -7.245147, timeout=0.1
            )
        self.assertFalse(result["ok"])
        self.assertIn("unavailable", result["message"])
        self.assertEqual(result["matches"], [])
        self.assertNotIn("no observations", result["message"].lower())

    def test_empty_archive_result_is_distinguished_from_unavailability(self):
        target = SkyCoord(133.795129 * u.deg, -7.245147 * u.deg)
        table = Table(names=["access_url"], dtype=["U1"])
        response_body = BytesIO()
        table.write(response_body, format="votable")
        response = requests.Response()
        response.status_code = 200
        response.url = "https://irsa.ipac.caltech.edu/SIA"
        response._content = response_body.getvalue()
        with patch("requests.Session.get", return_value=response):
            result = search_level2_footprints(
                target, 133.795129, -7.245147
            )
        self.assertTrue(result["ok"])
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["matches"], [])

    def test_s3_prefix_listing_parses_one_level_and_truncation(self):
        body = """<?xml version="1.0"?>
        <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
          <IsTruncated>true</IsTruncated>
          <CommonPrefixes><Prefix>dr1/level2/2025W17_4B/</Prefix></CommonPrefixes>
          <CommonPrefixes><Prefix>dr1/level2/2025W18_4B/</Prefix></CommonPrefixes>
        </ListBucketResult>"""
        with patch("requests.get", return_value=http_response(body)) as get:
            result = list_spherex_prefixes("dr1/level2/", timeout=4, max_results=2)
        self.assertEqual(result["prefixes"], [
            "dr1/level2/2025W17_4B/",
            "dr1/level2/2025W18_4B/",
        ])
        self.assertTrue(result["truncated"])
        self.assertEqual(get.call_args.kwargs["timeout"], (3, 4))

    def test_s3_file_listing_filters_non_fits_and_preserves_provenance(self):
        body = """<?xml version="1.0"?>
        <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
          <IsTruncated>false</IsTruncated>
          <Contents>
            <Key>dr1/level2/run/1/level2_image.fits</Key>
            <Size>1048576</Size>
            <LastModified>2026-03-01T00:00:00.000Z</LastModified>
          </Contents>
          <Contents><Key>dr1/level2/run/1/README.txt</Key><Size>12</Size></Contents>
        </ListBucketResult>"""
        with patch("requests.get", return_value=http_response(body)):
            result = list_spherex_level2_files("dr1/level2/run/1", max_results=3)
        self.assertFalse(result["truncated"])
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(result["files"][0]["filename"], "level2_image.fits")
        self.assertEqual(result["files"][0]["size_bytes"], 1048576)
        self.assertEqual(
            result["files"][0]["source_url"],
            "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
            "dr1/level2/run/1/level2_image.fits",
        )

    def test_s3_listing_propagates_http_errors(self):
        response = http_response("<Error/>", status=503)
        with patch("requests.get", return_value=response):
            with self.assertRaises(requests.HTTPError):
                list_spherex_prefixes("qr3/level2/")

    def test_s3_listing_propagates_timeouts(self):
        with patch("requests.get", side_effect=requests.Timeout("timed out")):
            with self.assertRaises(requests.Timeout):
                list_spherex_prefixes("dr1/level2/", timeout=2)

    def test_s3_listing_rejects_out_of_scope_and_malformed_prefixes(self):
        for prefix in (
            "dr1/level20/",
            "dr1/level2/../private/",
            "https://example.invalid/",
            "qr3/level2?prefix=private",
        ):
            with self.subTest(prefix=prefix):
                with patch("requests.get") as get:
                    with self.assertRaises(ValueError):
                        list_spherex_prefixes(prefix)
                    get.assert_not_called()

    def test_s3_listing_validates_result_bounds(self):
        with self.assertRaises(ValueError):
            list_spherex_prefixes("dr1/level2/", max_results=1001)
        with self.assertRaises(ValueError):
            list_spherex_level2_files("dr1/level2/", max_results=101)
