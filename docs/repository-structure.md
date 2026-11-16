# Repository structure

The repository keeps the application path short and makes the distinction
between software tests and scientific investigation explicit.

The runtime path is `app.py` → `ui/` → `core/`. The static deployment path is
`scripts/build-vercel.mjs` → `build_viewer.py` → `dist/`. The research path is
independent: `study/scripts/` produces reviewable outputs under
`study/results/` and is never imported by the application at startup.

## Maintained source

- `app.py` is the Streamlit entry point.
- `core/` contains reusable, testable logic. It does not perform archive-wide
  scans or write research results.
- `config/targets.json` contains only reviewed target presets. Missing
  coordinates are left missing rather than guessed.
- `tests/` contains deterministic unit tests. A file belongs here only when it
  can run as a repeatable software test without requiring a live archive.

## Study and archive work

`study/scripts/` contains exploratory work such as S3 inventory enumeration,
IRSA endpoint checks, header comparisons, proper-motion checks and target
coverage experiments. These scripts may require network access and can be
slow; they are not application startup dependencies.

`study/results/` contains generated tables and saved responses from those
studies. Large inventories and FITS products remain local and are ignored by
Git. A result is meaningful only together with its source URL/object key,
release, processing version and retrieval date where available.

The committed CSV and HTML results are retained as a research record, not as
runtime fixtures. They should not be presented as a complete archive census
unless their scope and retrieval date are stated.

## Runtime data

`data/cutouts/`, `data/previews/`, `data/inventory/`, `data/manifests/` and
`data/cache/` are local runtime locations. Keep small `.gitkeep` files and
reviewable manifests in Git; keep downloaded FITS, caches and bulk inventories
out of Git.

## Adding a new study

1. Put the executable experiment in `study/scripts/`.
2. Resolve paths from `Path(__file__)` rather than the caller's working
   directory.
3. Write generated output under `study/results/` or the appropriate `data/`
   directory.
4. Record the archive URL/object key, release, processing version, OBSID and
   observation metadata.
5. Add a deterministic test under `tests/` only for reusable logic extracted
   from the study.
