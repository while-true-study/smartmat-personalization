# data/raw

- **Local only.** The raw smart-mat dataset is kept on the researchers' machines and is not part of this
  repository. Its location is set by `raw_root` in `configs/paths.yaml`.
- **Excluded from Git.** Everything under `data/raw/` (and the raw package location) is git-ignored;
  this README is the only tracked file here.
- **Never modified.** Raw files are never edited, overwritten, renamed, moved or deleted. Code reads
  them only through `src/data/io_guard.py`, which refuses writes to raw locations. Integrity is checked
  against `data/interim/manifest/raw_file_manifest.csv` (SHA-256 per file).
- **Derived data go elsewhere.** All cleaned or derived data are written as new files under
  `data/interim/` or `data/processed/`.

References:
- Subject / device mapping and dataset roles: `docs/DATA_POLICY.md` §3–§4 and `configs/subject_mapping.yaml`
- Dataset inventory: `docs/initial_dataset_inventory.md`
