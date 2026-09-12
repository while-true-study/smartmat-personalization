# Conventions

Code, repository layout, experiment artifacts and naming.
Data rules: `docs/DATA_POLICY.md`. Evaluation rules: `docs/RESEARCH_PROTOCOL.md`.

---

## 1. Repository layout

```
README.md, AGENTS.md, CLAUDE.md   entry points (AGENTS/CLAUDE only point to docs/)
docs/                             canonical documentation (this folder)
configs/                          YAML configuration; the only place paths and mappings are defined
  paths.yaml                      raw_root, protected roots, output locations
  subject_mapping.yaml            subject / device / source / dataset-role mapping
data/
  raw/                            reserved raw location (see DATA_POLICY §1); read-only
  interim/                        derived, not yet model-ready (manifest, parsed/de-duplicated tables)
    manifest/                     raw_file_manifest.csv (+ .meta.json) — committed to Git
  processed/                      model-ready tables produced by a frozen protocol version
  splits/                         split definitions (created before windowing; RESEARCH_PROTOCOL L1)
src/
  data/                           raw access, provenance, parsing, audit helpers
  features/  models/  training/  evaluation/
scripts/                          thin command-line entry points that call src/
tests/                            pytest suite; must pass before results are produced
outputs/
  qa/  eda/  metrics/  predictions/  checkpoints/  figures/
paper/
  manuscript/  tables/  figures/  publication material only (anonymous IDs only)
```

The supplied raw package `스마트 매트 데이터 정리/` sits at the repository root until OPEN-05 is decided.

## 2. Code

- Python 3.12; dependencies pinned in `requirements.txt`. Run from the repository root.
- Logic lives in `src/`; `scripts/*.py` only parse arguments and call `src/`.
- **All file writes go through `src/data/io_guard.py`** (`open_for_write`, `write_text`, `write_csv`,
  `write_json`, `assert_writable`). Direct `open(..., "w")`, `Path.write_*`, `to_csv`, `os.remove`,
  `shutil.move` etc. are rejected by `tests/test_no_raw_modification.py`. If you need a new writer
  (e.g. parquet), add it to `io_guard.py`.
- Raw files are read only through `io_guard.read_bytes` (or helpers built on it).
- No hard-coded data paths in code; use `src/data/paths.py`.
- Subject/device identity only through `src/data/subject_mapping.py`; never parse subject IDs from
  folder names ad hoc.
- Randomness: every entry point takes a `--seed`; the seed is recorded with the run.
- Tests: `python -m pytest`. Add a test with any rule you add to `docs/`.
- Notebooks are allowed for exploration only; they must not write outside `outputs/eda/` and are not
  a source of reported results.

## 3. Naming

| Entity | Format | Example |
|---|---|---|
| subject_id | `User` + two digits | `User02` |
| device_id | physical mat ID as string, or `unknown` / `unresolved` / `not_applicable` | `22482` |
| source_id | as in `configs/subject_mapping.yaml` | `user02_mat_22482` |
| file_id | `rf_` + 10 hex of SHA-1(source_relpath) | `rf_3fa1c09b2e` |
| session_id | reserved: `<subject_id>_<device_id>_<YYYYMMDD>` of session start; definition pending (OPEN-06) | `User02_22480_20260719` |
| split_id | `<protocol_version>_<scheme>` | `v0.1_loso` |
| run_id | `<YYYYMMDD-HHMMSS>_<short-name>` | `20261001-142233_loso-baseline` |

Column names are `snake_case`. Canonical sensor columns in derived tables:
`ts_local, p1, p2, p3, p4, p5, p6, temp_c, humid_pct, movement_raw, control_raw`, plus the provenance
columns listed in `DATA_POLICY.md` §2.

Timestamps are stored as ISO-8601 local time without offset (the raw data carry no timezone; local
time is assumed, OPEN-08). Year-inferred timestamps keep a `year_source` column.

## 4. Configuration

- YAML only. Experiment configs go to `configs/experiments/<protocol_version>/`.
- A config is immutable once a reported run used it; changes create a new file.

## 5. Experiment artifacts

Each run writes to `outputs/<kind>/<run_id>/` and includes:

- `config.yaml` (resolved), `run_meta.json` (git commit, dirty flag, manifest SHA-256, split-file
  SHA-256, seed, Python/package versions, start/end time),
- `leakage_check.json` (RESEARCH_PROTOCOL L12) — a run without a passing check is invalid,
- `metrics.csv` with columns `run_id, fold, subject_id, target, metric, value, n_windows`,
- `predictions.parquet|csv` with `subject_id, device_id, session_id, window_start, window_end, target,
  y_true, y_pred` and provenance keys.

Outputs are not committed. Numbers used in the paper are exported to `paper/tables/` by a script,
never typed by hand.

## 6. Documentation and Git

- `docs/` holds the only definition of each rule; other files link to it rather than restating it.
- Every research decision gets a dated entry in `docs/DECISIONS.md`.
- Never commit raw or derived data, restricted metadata or credentials. The raw manifest is the only
  data-adjacent file under version control.
- Commit messages: imperative mood, reference the decision ID when relevant (e.g. `D-006`).
