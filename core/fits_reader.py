"""Reading genuine SPHEREx Level 2 MEF FITS files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlsplit

import aiohttp
import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS

from .coordinates import cutout_bounds, is_inside_image, pixel_scale_arcsec, world_to_pixel_one


@dataclass
class Level2Observation:
    filename: str
    source_url: str
    image: np.ndarray
    flags: np.ndarray | None
    variance: np.ndarray | None
    pixel_x: float
    pixel_y: float
    cutout_pixel_x: float
    cutout_pixel_y: float
    date_obs: str
    mjd_obs: float
    obsid: str
    detector: str
    bunit: str
    release: str
    release_source: str
    processing_version: str
    wavelength: str
    reference_epoch: str
    header_keys: dict[str, str]
    pixel_scale_x_arcsec: float
    pixel_scale_y_arcsec: float
    extension_issues: dict[str, str]


def _header_value(image_header, primary_header, key: str, default=""):
    value = image_header.get(key, primary_header.get(key, default))
    return default if value is None else value


def _float_or_nan(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _release_metadata(image_header, primary_header, source_url: str, fileobj) -> tuple[str, str]:
    release = _header_value(image_header, primary_header, "RELEASE", "")
    if str(release).strip():
        return str(release).strip(), "FITS header"
    source = source_url or (str(fileobj) if isinstance(fileobj, str) else "")
    try:
        path = urlsplit(source).path.lower()
    except ValueError:
        path = ""
    for release_name in ("dr1", "qr3"):
        if f"/{release_name}/level2/" in path:
            return release_name.upper(), "public archive URL"
    return "not in header", "unavailable"


def wavelength_label(hdul: fits.HDUList, image_header, primary_header) -> str:
    """Use archive/header wavelength metadata without inventing a value."""
    for key in ("WAVELENGTH", "WAVELEN", "LAMBDA", "BANDPASS", "BANDPASSNAME"):
        value = _header_value(image_header, primary_header, key, "")
        if str(value).strip():
            return str(value).strip()
    for key in ("WAVEMIN", "WAVEMAX", "WAVE_MIN", "WAVE_MAX"):
        value = _header_value(image_header, primary_header, key, "")
        if str(value).strip():
            return "header wavelength range present"
    if "WCS-WAVE" in hdul:
        return "WCS-WAVE table present (inspect per pixel)"
    return "not in header"


def read_level2(fileobj: BinaryIO | str | Path, target, cutout_size: int, filename: str, source_url: str = "") -> Level2Observation:
    """Read one local/uploaded or remote Level 2 MEF and extract a WCS cutout.

    Remote URLs use Astropy's fsspec-backed FITS sections so only the headers
    and requested image/quality cutout ranges are fetched when the server
    supports HTTP range requests.
    """
    is_remote = isinstance(fileobj, str) and fileobj.startswith(("http://", "https://"))
    open_kwargs = {"memmap": False}
    if is_remote:
        open_kwargs.update({
            "use_fsspec": True,
            "fsspec_kwargs": {
                "block_size": 65536,
                "client_kwargs": {"timeout": aiohttp.ClientTimeout(total=30)},
            },
        })
    with fits.open(fileobj, **open_kwargs) as hdul:
        if "IMAGE" not in hdul:
            raise ValueError("No IMAGE extension found")
        image_hdu = hdul["IMAGE"]
        image_header = image_hdu.header
        primary_header = hdul[0].header
        if int(image_header.get("NAXIS", 0) or 0) != 2:
            raise ValueError("IMAGE extension is not a two-dimensional image")
        height = int(image_header.get("NAXIS2", 0) or 0)
        width = int(image_header.get("NAXIS1", 0) or 0)
        if width <= 0 or height <= 0:
            raise ValueError("IMAGE extension has invalid dimensions")
        celestial_wcs = WCS(image_header).celestial
        x, y = world_to_pixel_one(celestial_wcs, target)
        if not is_inside_image(x, y, width, height):
            raise ValueError(
                f"target is outside image footprint at pixel ({x:.2f}, {y:.2f})"
            )
        x0, x1, y0, y1 = cutout_bounds(x, y, width, height, cutout_size)

        if is_remote:
            image = np.asarray(image_hdu.section[y0:y1, x0:x1], dtype=float)
        else:
            if image_hdu.data is None or np.asarray(image_hdu.data).ndim != 2:
                raise ValueError("IMAGE extension is not a two-dimensional image")
            image = np.asarray(image_hdu.data[y0:y1, x0:x1], dtype=float)

        extension_issues = {}

        def section(name: str, dtype=float):
            if name not in hdul:
                extension_issues[name] = "extension is missing"
                return None
            hdu = hdul[name]
            ext_height = int(hdu.header.get("NAXIS2", 0) or 0)
            ext_width = int(hdu.header.get("NAXIS1", 0) or 0)
            if (ext_width, ext_height) != (width, height):
                extension_issues[name] = (
                    f"dimensions {ext_width}×{ext_height} do not match "
                    f"IMAGE dimensions {width}×{height}"
                )
                return None
            if is_remote:
                return np.asarray(hdu.section[y0:y1, x0:x1], dtype=dtype)
            if hdu.data is None:
                extension_issues[name] = "extension contains no image data"
                return None
            data = np.asarray(hdu.data)
            return data[y0:y1, x0:x1].astype(dtype, copy=False)

        date_value = _header_value(image_header, primary_header, "DATE-OBS", "")
        date_obs = str(date_value) if date_value else ""
        mjd_value = _header_value(image_header, primary_header, "MJD-OBS", "")
        mjd_obs = _float_or_nan(mjd_value)
        if not np.isfinite(mjd_obs) and date_obs:
            try:
                mjd_obs = float(Time(date_obs, scale="utc").mjd)
            except (TypeError, ValueError):
                pass
        scale_x, scale_y = pixel_scale_arcsec(celestial_wcs)
        release, release_source = _release_metadata(
            image_header, primary_header, source_url, fileobj
        )
        header_keys = {
            "ORIGIN": str(_header_value(image_header, primary_header, "ORIGIN", "")),
            "FILENAME": filename,
            "SOURCE_URL": source_url,
            "RELEASE_SOURCE": release_source,
        }
        return Level2Observation(
            filename=filename,
            source_url=source_url,
            image=image,
            flags=section("FLAGS", float),
            variance=section("VARIANCE", float),
            pixel_x=x,
            pixel_y=y,
            cutout_pixel_x=x - x0,
            cutout_pixel_y=y - y0,
            date_obs=date_obs,
            mjd_obs=mjd_obs,
            obsid=str(_header_value(image_header, primary_header, "OBSID", "")),
            detector=str(_header_value(image_header, primary_header, "DETECTOR", "")),
            bunit=str(_header_value(image_header, primary_header, "BUNIT", "unknown")),
            release=release,
            release_source=release_source,
            processing_version=str(_header_value(image_header, primary_header, "VERSION", "unknown")),
            wavelength=wavelength_label(hdul, image_header, primary_header),
            reference_epoch=str(_header_value(image_header, primary_header, "EQUINOX", "unknown")),
            header_keys=header_keys,
            pixel_scale_x_arcsec=scale_x,
            pixel_scale_y_arcsec=scale_y,
            extension_issues=extension_issues,
        )
