"""Reading genuine SPHEREx Level 2 MEF FITS files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from .coordinates import cutout_bounds, is_inside_image, world_to_pixel_one


@dataclass
class Level2Observation:
    filename: str
    source_url: str
    image: np.ndarray
    flags: np.ndarray | None
    variance: np.ndarray | None
    pixel_x: float
    pixel_y: float
    date_obs: str
    mjd_obs: float
    obsid: str
    detector: str
    bunit: str
    release: str
    processing_version: str
    wavelength: str
    reference_epoch: str
    header_keys: dict[str, str]


def _header_value(image_header, primary_header, key: str, default=""):
    value = image_header.get(key, primary_header.get(key, default))
    return default if value is None else value


def _float_or_nan(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


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


def read_level2(fileobj: BinaryIO, target, cutout_size: int, filename: str, source_url: str = "") -> Level2Observation:
    """Read one uploaded/cached Level 2 MEF and extract a WCS cutout."""
    with fits.open(fileobj, memmap=False) as hdul:
        if "IMAGE" not in hdul:
            raise ValueError("No IMAGE extension found")
        image_hdu = hdul["IMAGE"]
        if image_hdu.data is None or np.asarray(image_hdu.data).ndim != 2:
            raise ValueError("IMAGE extension is not a two-dimensional image")
        image = np.asarray(image_hdu.data, dtype=float)
        image_header = image_hdu.header
        primary_header = hdul[0].header
        x, y = world_to_pixel_one(WCS(image_header).celestial, target)
        height, width = image.shape
        if not is_inside_image(x, y, width, height):
            raise ValueError(f"target is outside image footprint at pixel ({x:.2f}, {y:.2f})")
        x0, x1, y0, y1 = cutout_bounds(x, y, width, height, cutout_size)

        def section(name: str, dtype=float):
            if name not in hdul or hdul[name].data is None:
                return None
            data = np.asarray(hdul[name].data)
            if data.shape != image.shape:
                return None
            return data[y0:y1, x0:x1].astype(dtype, copy=False)

        date_obs = str(_header_value(image_header, primary_header, "DATE-OBS", ""))
        mjd_obs = _float_or_nan(_header_value(image_header, primary_header, "MJD-OBS", ""))
        header_keys = {
            "ORIGIN": str(_header_value(image_header, primary_header, "ORIGIN", "")),
            "FILENAME": filename,
            "SOURCE_URL": source_url,
        }
        return Level2Observation(
            filename=filename,
            source_url=source_url,
            image=image[y0:y1, x0:x1],
            flags=section("FLAGS", np.int64),
            variance=section("VARIANCE", float),
            pixel_x=x,
            pixel_y=y,
            date_obs=date_obs,
            mjd_obs=mjd_obs,
            obsid=str(_header_value(image_header, primary_header, "OBSID", "")),
            detector=str(_header_value(image_header, primary_header, "DETECTOR", "")),
            bunit=str(_header_value(image_header, primary_header, "BUNIT", "unknown")),
            release=str(_header_value(image_header, primary_header, "RELEASE", "unknown")),
            processing_version=str(_header_value(image_header, primary_header, "VERSION", "unknown")),
            wavelength=wavelength_label(hdul, image_header, primary_header),
            reference_epoch=str(_header_value(image_header, primary_header, "EQUINOX", "unknown")),
            header_keys=header_keys,
        )
