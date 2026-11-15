# ORBITAL EYE — Milestone 01

This starter retrieves real SPHEREx cutouts from NASA/IPAC IRSA using the official TAP workflow.

## Requirements
- Windows 10/11
- Python 3.10 or newer (64-bit recommended)
- VS Code with the Python extension
- Internet access

## 1. Open the existing repository
Copy these files/folders into the root of your existing ORBITAL EYE repository.
Do not overwrite existing project files with the same names without checking them first.

## 2. Create and activate a virtual environment (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation in this terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-milestone-01.txt
```

## 4. Run the WISE 0855 test

```powershell
python validate_spherex.py --target "WISE 0855" --ra 133.795129 --dec -7.245147 --bandpass SPHEREx-D2 --size 0.03 --max-downloads 3
```

The coordinates are the challenge coordinates converted from sexagesimal to decimal degrees.

## 5. Expected output

- `data/inventory/WISE_0855_inventory.csv` — all matching TAP rows for the selected detector.
- `data/inventory/WISE_0855_manifest.json` — provenance and FITS inspection metadata for downloaded cutouts.
- `data/cutouts/*.fits` — actual multi-extension SPHEREx FITS cutouts.
- `data/previews/*.png` — display-only PNG previews derived from the FITS IMAGE extension.

## 6. Important science notes

- The script searches the SPHEREx DR1 and QR3 metadata tables via IRSA TAP.
- It uses one detector bandpass (SPHEREx-D2) to keep the first retrieval small and comparable.
- It selects up to three rows spread across the returned chronological inventory.
- A returned image only means the requested coordinate falls inside that observation's footprint. It does not establish that WISE 0855 itself was detected.
- The challenge coordinate has no reference epoch specified here. High-proper-motion analysis requires epoch-aware coordinate propagation.
- Do not compare or subtract images scientifically until calibration compatibility, WCS registration, PSF matching, flags and uncertainties have been checked.

## Official references

- https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/
- https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/
- https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/
