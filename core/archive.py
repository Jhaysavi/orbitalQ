"""Bounded, provenance-preserving SPHEREx Level 2 archive access."""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath
from typing import Any
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlsplit

import numpy as np
import requests
import time
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time
from astropy.wcs import WCS

from .coordinates import is_inside_image, world_to_pixel_one


IRSA_SIA_URL = "https://irsa.ipac.caltech.edu/SIA"
IRSA_ROOT = "https://irsa.ipac.caltech.edu/"
S3_ROOT = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"


def _validate_s3_prefix(prefix: str) -> str:
    value = str(prefix).strip().strip("/")
    if (
        not any(
            value == root or value.startswith(root + "/")
            for root in ("dr1/level2", "qr3/level2")
        )
        or any(part in {".", ".."} for part in value.split("/"))
        or any(character in value for character in ("?", "#", "\\"))
    ):
        raise ValueError("S3 browsing is limited to public DR1/QR3 Level 2 folders")
    return value + "/"


def list_spherex_prefixes(
    prefix: str,
    timeout: float = 10,
    max_results: int = 1000,
) -> dict[str, Any]:
    """List one level of public Level 2 folders using S3 ListObjectsV2."""
    if not 1 <= max_results <= 1000:
        raise ValueError("max_results must be between 1 and 1000")
    safe_prefix = _validate_s3_prefix(prefix)
    response = requests.get(
        S3_ROOT,
        params={
            "list-type": "2",
            "prefix": safe_prefix,
            "delimiter": "/",
            "max-keys": str(max_results),
        },
        timeout=(3, timeout),
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    prefixes = sorted({
        element.text
        for element in root.findall(".//{*}CommonPrefixes/{*}Prefix")
        if element.text
    })
    return {
        "prefix": safe_prefix,
        "prefixes": prefixes,
        "truncated": root.findtext("{*}IsTruncated") == "true",
        "source_url": response.url,
    }


def list_spherex_level2_files(
    prefix: str,
    max_results: int = 24,
    timeout: float = 10,
) -> dict[str, Any]:
    """List a bounded set of public FITS objects from one archive folder."""
    if not 1 <= max_results <= 100:
        raise ValueError("max_results must be between 1 and 100")
    safe_prefix = _validate_s3_prefix(prefix)
    response = requests.get(
        S3_ROOT,
        params={
            "list-type": "2",
            "prefix": safe_prefix,
            "max-keys": str(max_results),
        },
        timeout=(3, timeout),
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    files = []
    for element in root.findall(".//{*}Contents"):
        key = element.findtext("{*}Key") or ""
        if not key.lower().endswith((".fits", ".fit")):
            continue
        files.append({
            "key": key,
            "filename": PurePosixPath(key).name,
            "size_bytes": int(element.findtext("{*}Size") or 0),
            "last_modified": element.findtext("{*}LastModified") or "",
            "source_url": S3_ROOT + quote(key, safe="/"),
        })
    return {
        "prefix": safe_prefix,
        "files": files,
        "truncated": root.findtext("{*}IsTruncated") == "true",
        "source_url": response.url,
    }


def _value(row: Any, *names: str, default: str = "") -> str:
    """Read a case-insensitive SIA column without leaking masked values."""
    columns = {str(name).lower(): name for name in row.colnames}
    for name in names:
        column = columns.get(name.lower())
        if column is None:
            continue
        value = row[column]
        if np.ma.is_masked(value):
            continue
        text = str(value).strip()
        if text and text.lower() not in {"none", "nan"}:
            return text
    return default


def resolve_archive_url(value: str) -> str:
    """Resolve an SIA URI or S3 key into a reproducible HTTP URL."""
    value = str(value).strip()
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("s3://"):
        return S3_ROOT + value.removeprefix("s3://").split("/", 1)[-1]
    return IRSA_ROOT + value.lstrip("/")


def is_supported_spherex_url(value: str) -> bool:
    """Accept only HTTPS URLs on public SPHEREx archive hosts."""
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme == "https"
            and parsed.hostname in {
                "nasa-irsa-spherex.s3.us-east-1.amazonaws.com",
                "irsa.ipac.caltech.edu",
            }
            and parsed.port in (None, 443)
            and parsed.username is None
            and parsed.password is None
            and parsed.path.lower().endswith((".fits", ".fit"))
        )
    except ValueError:
        return False


def _parse_mjd(date_obs: str, raw_mjd: str) -> float:
    try:
        return float(raw_mjd)
    except (TypeError, ValueError):
        if not date_obs:
            return float("nan")
        try:
            return float(Time(date_obs).mjd)
        except (TypeError, ValueError):
            return float("nan")


def _read_header(
    session: requests.Session,
    url: str,
    offset: int = 0,
    timeout: float = 20,
) -> tuple[fits.Header, int]:
    """Read one FITS header with 2880-byte HTTP range requests only."""
    raw = bytearray()
    position = offset
    while True:
        response = session.get(
            url,
            headers={"Range": f"bytes={position}-{position + 2879}"},
            timeout=timeout,
        )
        response.raise_for_status()
        if response.status_code != 206:
            raise RuntimeError(
                f"archive did not honour FITS range request (HTTP {response.status_code})"
            )
        if not response.content:
            raise RuntimeError("archive returned an empty FITS header block")
        raw.extend(response.content)
        position += len(response.content)
        cards = [raw[index:index + 80] for index in range(0, len(raw), 80)]
        if any(card[:8].strip() == b"END" for card in cards if len(card) == 80):
            break
        if len(raw) > 1024 * 1024:
            raise RuntimeError("FITS header exceeded the safe 1 MiB range-read limit")
    header = fits.Header.fromstring(bytes(raw).decode("ascii"), sep="")
    return header, len(raw)


def _padded_data_size(header: fits.Header) -> int:
    naxis = int(header.get("NAXIS", 0) or 0)
    if naxis == 0:
        return 0
    elements = 1
    for axis in range(1, naxis + 1):
        elements *= max(0, int(header.get(f"NAXIS{axis}", 0) or 0))
    bitpix = abs(int(header.get("BITPIX", 0) or 0))
    raw_size = (elements + int(header.get("PCOUNT", 0) or 0)) * bitpix // 8
    raw_size *= int(header.get("GCOUNT", 1) or 1)
    return ((raw_size + 2879) // 2880) * 2880


def read_level2_headers(
    url: str,
    session: requests.Session | None = None,
    timeout: float = 20,
) -> tuple[fits.Header, fits.Header]:
    """Read primary and IMAGE headers without downloading FITS image arrays."""
    client = session or requests.Session()
    primary, primary_size = _read_header(client, url, timeout=timeout)
    offset = primary_size + _padded_data_size(primary)
    for _ in range(32):
        image, header_size = _read_header(client, url, offset, timeout=timeout)
        if str(image.get("EXTNAME", "")).strip().upper() == "IMAGE":
            if int(image.get("NAXIS", 0)) != 2:
                raise ValueError("IMAGE extension must be two-dimensional")
            return primary, image
        offset += header_size + _padded_data_size(image)
    raise ValueError("No IMAGE extension found within 32 extensions")


def _candidate_from_headers(
    *,
    url: str,
    filename: str,
    collection: str,
    table_row: Any,
    primary: fits.Header,
    image: fits.Header,
    target: Any,
) -> dict[str, Any]:
    wcs = WCS(image).celestial
    pixel_x, pixel_y = world_to_pixel_one(wcs, target)
    width = int(image.get("NAXIS1", 0) or 0)
    height = int(image.get("NAXIS2", 0) or 0)
    if not is_inside_image(pixel_x, pixel_y, width, height):
        raise ValueError(f"target is outside image footprint at pixel ({pixel_x:.2f}, {pixel_y:.2f})")

    date_obs = str(image.get("DATE-OBS", primary.get("DATE-OBS", "")) or "")
    mjd_obs = _parse_mjd(date_obs, str(image.get("MJD-OBS", primary.get("MJD-OBS", "")) or ""))
    release = str(image.get("RELEASE", primary.get("RELEASE", collection.upper())) or collection.upper())
    processing = str(
        image.get("VERSION", image.get("PROCVER", primary.get("VERSION", "unknown")))
        or "unknown"
    )
    wavelength = str(
        image.get("WAVELENGTH", image.get("BANDPASS", _value(table_row, "energy_bandpassname")))
        or "not in header"
    )
    obsid = str(image.get("OBSID", primary.get("OBSID", _value(table_row, "obs_id", "obsid"))) or "")
    detector = str(image.get("DETECTOR", primary.get("DETECTOR", "")) or "")
    return {
        "filename": filename,
        "source_url": url,
        "release": release,
        "processing_version": processing,
        "obsid": obsid,
        "date_obs": date_obs,
        "mjd_obs": mjd_obs,
        "detector": detector,
        "wavelength": wavelength,
        "pixel_x": pixel_x,
        "pixel_y": pixel_y,
        "width": width,
        "height": height,
        "collection": collection,
        "archive_result": True,
    }


def search_level2_footprints(
    target: Any,
    ra_deg: float,
    dec_deg: float,
    radius_deg: float = 0.1,
    max_results: int = 8,
    releases: tuple[str, ...] = ("DR1", "QR3"),
    timeout: float = 8,
) -> dict[str, Any]:
    """Search selected SIA releases and verify bounded results against FITS WCS.

    The returned dictionary is safe to cache and includes diagnostics when the
    service is unavailable. A SIA row is not accepted until its actual FITS
    IMAGE WCS contains the requested coordinate.
    """
    if not (0 < radius_deg <= 1.0):
        raise ValueError("search radius must be between 0 and 1 degree")
    if max_results < 1 or max_results > 24:
        raise ValueError("max_results must be between 1 and 24")
    release_collections = {
        "DR1": "spherex_dr1",
        "QR3": "spherex_qr3",
    }
    if not releases or any(release not in release_collections for release in releases):
        raise ValueError("releases must contain DR1 and/or QR3")

    session = requests.Session()
    session.headers.update({"User-Agent": "orbitalQ-SPHEREx-MVP/1.0"})
    started_at = time.monotonic()
    time_budget = max(30.0, timeout * 3)
    tables = []
    service_errors = []
    per_release_limit = max(1, max_results // len(releases))
    for release in releases:
        params = {
            "COLLECTION": release_collections[release],
            "POS": f"circle {ra_deg:.9f} {dec_deg:.9f} {radius_deg:.6f}",
            "MAXREC": str(per_release_limit),
        }
        try:
            response = session.get(IRSA_SIA_URL, params=params, timeout=timeout)
            response.raise_for_status()
            table = Table.read(BytesIO(response.content), format="votable")
            tables.append((release_collections[release], response, table, per_release_limit))
        except Exception as exc:
            service_errors.append(f"{release}: {exc}")
    if not tables:
        return {
            "ok": False,
            "service": IRSA_SIA_URL,
            "message": "Level 2 archive search unavailable: " + "; ".join(service_errors),
            "matches": [],
            "rejected": [],
        }

    matches = []
    checked = 0
    rejected = [f"Search service unavailable for {error}" for error in service_errors]
    partial = bool(service_errors)
    remaining = max_results
    per_collection = max(1, (max_results + len(tables) - 1) // len(tables))
    for collection, response, table, result_limit in tables:
        if remaining <= 0:
            partial = True
            break
        rows = table[:min(per_collection, remaining)]
        if len(table) >= result_limit:
            partial = True
            rejected.append(
                f"{collection}: SIA result limit reached; additional candidates may remain."
            )
        for row in rows:
            if time.monotonic() - started_at >= time_budget:
                partial = True
                rejected.append(
                    "Search time budget reached; remaining candidates were not verified."
                )
                break
            checked += 1
            raw_url = _value(row, "access_url", "accessurl", "url", "uri")
            remaining -= 1
            if not raw_url:
                rejected.append(f"{collection}: SIA row had no access URL")
                continue
            url = resolve_archive_url(raw_url)
            filename = (
                PurePosixPath(url.split("?", 1)[0]).name
                or _value(row, "obs_id", "obsid", default="observation.fits")
            )
            try:
                if not is_supported_spherex_url(url):
                    raise ValueError(
                        f"unsupported archive host: {urlsplit(url).hostname or 'unknown'}"
                    )
                primary, image = read_level2_headers(
                    url, session, timeout=min(timeout, 10)
                )
                matches.append(
                    _candidate_from_headers(
                        url=url,
                        filename=filename,
                        collection=collection,
                        table_row=row,
                        primary=primary,
                        image=image,
                        target=target,
                    )
                )
            except Exception as exc:
                partial = True
                rejected.append(f"{filename}: {exc}")
        if time.monotonic() - started_at >= time_budget:
            break

    message = (
        f"Verified {len(matches)} images from {checked} checked candidates "
        f"({sum(len(table) for _, _, table, _ in tables)} returned by SIA; releases: {' / '.join(releases)})."
    )
    if partial:
        message += " Search was incomplete; no conclusion about unverified coverage is possible."
    return {
        "ok": True,
        "service": [service_response.url for _, service_response, _, _ in tables],
        "message": message,
        "candidate_count": sum(len(table) for _, _, table, _ in tables),
        "matches": matches,
        "rejected": rejected,
        "partial": partial,
    }
