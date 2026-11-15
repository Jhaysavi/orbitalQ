#!/usr/bin/env python3
"""
orbitalQ — ESA Gaia DR3 Proper Motion & Epoch Propagation Module
================================================================
Queries the European Space Agency (ESA) Gaia DR3 Archive via `astroquery.gaia`
(TAP+ / ADQL) to retrieve positions, parallaxes, and proper motions (`pmra`, `pmdec`)
around a target sky coordinate, and propagates stellar positions to any SPHEREx
observation epoch using `astropy.coordinates.SkyCoord.apply_space_motion`.

Data source: European Space Agency (ESA) Gaia Archive (2026 Space Apps Partner).
Reference: https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astroquery.gaia import Gaia


def query_gaia_dr3_cone(
    ra_deg: float,
    dec_deg: float,
    radius_arcmin: float = 2.5,
    max_sources: int = 50,
) -> list[dict[str, Any]]:
    """Run a synchronous ADQL cone search against ESA Gaia DR3 (`gaiadr3.gaia_source`)."""
    radius_deg = radius_arcmin / 60.0
    adql = f"""
    SELECT TOP {max_sources}
        source_id,
        ra,
        dec,
        parallax,
        pmra,
        pmdec,
        phot_g_mean_mag,
        bp_rp
    FROM gaiadr3.gaia_source
    WHERE 1 = CONTAINS(
        POINT('ICRS', ra, dec),
        CIRCLE('ICRS', {ra_deg}, {dec_deg}, {radius_deg})
    )
    AND phot_g_mean_mag IS NOT NULL
    ORDER BY phot_g_mean_mag ASC
    """
    job = Gaia.launch_job(adql)
    table = job.get_results()

    sources: list[dict[str, Any]] = []
    for row in table:
        pmra = float(row["pmra"]) if row["pmra"] is not None and not getattr(row["pmra"], "mask", False) else 0.0
        pmdec = float(row["pmdec"]) if row["pmdec"] is not None and not getattr(row["pmdec"], "mask", False) else 0.0
        plx = float(row["parallax"]) if row["parallax"] is not None and not getattr(row["parallax"], "mask", False) else None
        sources.append(
            {
                "source_id": str(row["source_id"]),
                "ra_j2016": float(row["ra"]),
                "dec_j2016": float(row["dec"]),
                "parallax_mas": plx,
                "pmra_mas_yr": pmra,
                "pmdec_mas_yr": pmdec,
                "g_mag": float(row["phot_g_mean_mag"]),
            }
        )
    return sources


def propagate_to_epoch(
    sources: list[dict[str, Any]],
    target_iso_date: str,
) -> list[dict[str, Any]]:
    """Propagate Gaia DR3 (J2016.0) coordinates to a target SPHEREx observation date."""
    gaia_epoch = Time("2016-01-01T00:00:00", scale="tcb")
    target_epoch = Time(target_iso_date)

    propagated: list[dict[str, Any]] = []
    for src in sources:
        # Use measured parallax if positive, otherwise default to distant background (0.1 mas)
        plx_val = src["parallax_mas"] if (src["parallax_mas"] and src["parallax_mas"] > 0) else 0.1
        c = SkyCoord(
            ra=src["ra_j2016"] * u.deg,
            dec=src["dec_j2016"] * u.deg,
            distance=(1000.0 / plx_val) * u.pc,
            pm_ra_cosdec=src["pmra_mas_yr"] * u.mas / u.yr,
            pm_dec=src["pmdec_mas_yr"] * u.mas / u.yr,
            obstime=gaia_epoch,
            frame="icrs",
        )
        c_new = c.apply_space_motion(new_obstime=target_epoch)
        total_pm = (src["pmra_mas_yr"] ** 2 + src["pmdec_mas_yr"] ** 2) ** 0.5
        propagated.append(
            {
                **src,
                "target_epoch": target_iso_date,
                "ra_propagated": round(float(c_new.ra.deg), 7),
                "dec_propagated": round(float(c_new.dec.deg), 7),
                "total_pm_mas_yr": round(total_pm, 2),
            }
        )
    return propagated


def main() -> None:
    parser = argparse.ArgumentParser(description="Query ESA Gaia DR3 and propagate coordinates to SPHEREx epochs.")
    parser.add_argument("--ra", type=float, default=269.452075, help="RA in degrees (default: Barnard's Star).")
    parser.add_argument("--dec", type=float, default=4.693391, help="Dec in degrees (default: Barnard's Star).")
    parser.add_argument("--radius", type=float, default=2.5, help="Search radius in arcmin.")
    parser.add_argument("--epoch", type=str, default="2026-06-15", help="Target ISO observation date.")
    parser.add_argument("--out", type=str, default="data/gaia_overlay.json", help="Output JSON file path.")
    args = parser.parse_args()

    print(f"Querying ESA Gaia DR3 around RA={args.ra:.5f}, Dec={args.dec:.5f} (r={args.radius}')...")
    raw_sources = query_gaia_dr3_cone(args.ra, args.dec, radius_arcmin=args.radius)
    propagated = propagate_to_epoch(raw_sources, target_iso_date=args.epoch)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "ESA Gaia DR3 Archive (gaiadr3.gaia_source)",
        "reference_epoch": "J2016.0",
        "propagated_epoch": args.epoch,
        "count": len(propagated),
        "sources": propagated,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved {len(propagated)} Gaia DR3 sources propagated to {args.epoch} -> {out_path}")


if __name__ == "__main__":
    main()
