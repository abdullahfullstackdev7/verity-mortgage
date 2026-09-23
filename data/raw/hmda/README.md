# data/raw/hmda

This folder holds manually-exported HMDA Modified LAR CSV files. It is
intentionally empty in version control — CSVs placed here are gitignored
(see the repo root `.gitignore`).

See `scripts/download_hmda.py` for the manual export steps and the
required naming convention (`hmda_lar_<year>_<state>.csv`).

Keep files in this folder untouched after download; all cleaning happens
in `scripts/clean_hmda.py` and writes only to `data/processed/`.
