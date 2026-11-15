"""Build a standalone ORBITAL EYE viewer from real SPHEREx retrieval manifests."""

import argparse
import base64
import io
import json
import re
import math
from pathlib import Path
from urllib.parse import urlsplit

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
from matplotlib import image
from matplotlib.colors import AsinhNorm
import numpy as np
from reproject import reproject_interp

ROOT = Path(__file__).resolve().parent

# Approximate catalog overlays for visual inspection. The model omits parallax.
TARGETS = {
    "barnard": {
        "ra": 269.452075, "dec": 4.693389, "epoch": 2000.0,
        "pm_ra": -0.801551, "pm_dec": 10.362394, "bands": ["D1", "D2"],
        "source": "https://simbad.harvard.edu/simbad/sim-id?Ident=Barnard%27s+star",
    },
    "wise_0855": {
        "ra": (8 + 55 / 60 + 8.433 / 3600) * 15,
        "dec": -(7 + 14 / 60 + 39.49 / 3600),
        "epoch_mjd": 56986.817, "pm_ra": -8.1, "pm_dec": 0.7,
        "bands": ["D5", "D6"],
        "source": "https://doi.org/10.1051/0004-6361/201628662",
    },
}


def expected_position(target, date):
    epoch = Time(target["epoch_mjd"], format="mjd") if "epoch_mjd" in target else Time(target["epoch"], format="jyear")
    years = (date - epoch).to_value(u.yr)
    origin = SkyCoord(target["ra"] * u.deg, target["dec"] * u.deg)
    return origin.spherical_offsets_by(
        target["pm_ra"] * years * u.arcsec, target["pm_dec"] * years * u.arcsec
    )


def remote_source(value):
    url = urlsplit(value)
    if url.scheme != "https" or url.netloc.lower() != "irsa.ipac.caltech.edu":
        raise ValueError("Expected an original HTTPS FITS URL from NASA/IPAC IRSA.")
    return value


def read_fits(path):
    with fits.open(path, memmap=False) as hdus:
        hdu = hdus["IMAGE"]
        pixels = np.asarray(hdu.data, dtype=float)
        if pixels.ndim != 2:
            raise ValueError(f"{path.name} does not contain a 2D IMAGE extension.")
        wcs = WCS(hdu.header, fobj=hdus).celestial
        if not wcs.has_celestial:
            raise ValueError(f"{path.name} has no celestial WCS.")
        unit = hdu.header.get("BUNIT", "").strip()
        if not unit:
            raise ValueError(f"{path.name} has no BUNIT.")
        return pixels, wcs, unit, str(hdu.header.get("OBSID", path.name))


def export_case(key, manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = TARGETS[key]
    band = manifest["bandpass"]
    if band not in {f"SPHEREx-{name}" for name in target["bands"]}:
        raise ValueError(f"{key}: choose a detector from {', '.join(target['bands'])}.")
    products = sorted(
        manifest["downloaded_products"],
        key=lambda product: float(product["observation_time_from_tap"]),
    )
    if len({float(product["observation_time_from_tap"]) for product in products}) < 2:
        raise ValueError(f"{key}: at least two distinct observation times are required.")
    reference = None
    shared_mask = None
    arrays, frames = [], []
    for product in products:
        if product["bandpass_from_tap"] != band:
            raise ValueError(f"{key}: the observation band does not match the manifest.")
        path = (ROOT / product["fits_file"]).resolve()
        path.relative_to(ROOT / "data" / "cutouts")
        pixels, source_wcs, unit, obsid = read_fits(path)
        if reference is None:
            reference = source_wcs, pixels.shape, unit
        wcs, shape, reference_unit = reference
        if unit != reference_unit:
            raise ValueError(f"{key}: the FITS files use different brightness units.")
        aligned, footprint = reproject_interp((pixels, source_wcs), wcs, shape_out=shape)
        valid = (footprint > 0) & np.isfinite(aligned)
        shared_mask = valid if shared_mask is None else shared_mask & valid
        mjd = float(product["observation_time_from_tap"])
        date = Time(mjd, format="mjd", scale="utc")
        position = expected_position(target, date)
        x, y = wcs.world_to_pixel(position)
        inside = math.isfinite(x) and math.isfinite(y) and 0 <= x < shape[1] and 0 <= y < shape[0]
        marker = [float((x + .5) / shape[1]), float(1 - (y + .5) / shape[0])] if inside else None
        frames.append({
            "date": date.isot + " UTC", "obsid": obsid, "mjd": mjd, "marker": marker,
            "fits": remote_source(product["source_cutout_url"]),
        })
        arrays.append(aligned)

    if not shared_mask.any():
        raise ValueError(f"{key}: the observation frames have no common valid coverage.")
    values = np.concatenate([array[shared_mask] for array in arrays])
    low, high = np.percentile(values, [1, 99.8])
    if high <= low:
        raise ValueError(f"{key}: the shared image has insufficient brightness range.")
    norm = AsinhNorm(linear_width=(high - low) / 20, vmin=low, vmax=high, clip=True)
    for frame, array in zip(frames, arrays):
        if frame["marker"]:
            x, y = frame["marker"]
            col = min(shape[1] - 1, int(x * shape[1]))
            row = min(shape[0] - 1, int((1 - y) * shape[0]))
            if not shared_mask[row, col]:
                frame["marker"] = None
        buffer = io.BytesIO()
        image.imsave(buffer, np.ma.array(norm(array), mask=~shared_mask),
                     origin="lower", cmap="inferno", vmin=0, vmax=1, format="png")
        frame["image"] = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "key": key, "name": manifest["target"], "detector": band, "source": target["source"],
        "frames": frames, "unit": reference_unit, "min": float(low), "max": float(high),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--barnard", type=Path, required=True, help="Barnard FITS manifest")
    parser.add_argument("--wise-0855", type=Path, help="Optional WISE 0855 FITS manifest")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "index.html")
    args = parser.parse_args()
    try:
        cases = [export_case("barnard", args.barnard)]
        if args.wise_0855:
            cases.append(export_case("wise_0855", args.wise_0855))
    except (KeyError, TypeError, ValueError, OSError) as error:
        parser.error(str(error))
    payload = json.dumps(cases, ensure_ascii=True, allow_nan=False).replace("<", r"\u003c")
    template = (ROOT / "dist" / "index.html").read_text(encoding="utf-8")
    page, replacements = re.subn(
        r'(<script id="case-data" type="application/json">).*?(</script>)',
        lambda match: match[1] + payload + match[2],
        template,
        count=1,
        flags=re.DOTALL,
    )
    if replacements != 1:
        parser.error("The static viewer is missing its case-data script.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(page, encoding="utf-8")
    temporary.replace(args.output)
    print(f"Viewer generated: {args.output.resolve()}")


if __name__ == "__main__":
    main()
