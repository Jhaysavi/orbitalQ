# Study scripts and research results

This directory contains exploratory SPHEREx work preserved from the project’s
investigation. It is intentionally separate from the application and from
automated unit tests.

## Scripts

Run scripts from the repository root, for example:

```bash
.venv/bin/python study/scripts/sample_dr1_period_dates.py
.venv/bin/python study/scripts/compare_spherex_sequence_headers.py
```

The scripts resolve their project paths from their own location and write
generated tables to `study/results/`. Some scripts query public IRSA or AWS
endpoints and may fail when a service is unavailable. Such a failure is an
archive-access result, not evidence that the target has no observations.

The inventory scripts can be expensive and are not part of application startup.
Do not run an archive-wide scan casually. Prefer a bounded target or header
sample and retain the original object keys and release metadata.

## Results and local data

`study/results/` contains small, reviewable tables and saved endpoint
responses. Generated inventories and FITS files are local-only and ignored by
Git. They are not synthetic data; they are generated from the official archive
and must retain their provenance when reused.

For the method and scientific limitations, see
[docs/scientific-methods.md](../docs/scientific-methods.md).
