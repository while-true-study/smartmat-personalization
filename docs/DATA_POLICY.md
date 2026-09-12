# Data Policy

Canonical rules for raw data, subject/device identity, dataset roles and privacy.
Machine-readable counterpart: `configs/subject_mapping.yaml` (mapping) and `configs/paths.yaml` (locations).
Changes to this document require a dated entry in `docs/DECISIONS.md`.

---

## 1. Raw data is the source of truth and is immutable

| Item | Value |
|---|---|
| Raw package (as delivered) | `스마트 매트 데이터 정리/` (repository root) |
| Raw sensor tree | `스마트 매트 데이터 정리/raw/` = `raw_root` in `configs/paths.yaml` |
| Reserved raw location | `data/raw/` (currently holds only a README; see DECISIONS D-005) |
| Checksum manifest | `data/interim/manifest/raw_file_manifest.csv` (SHA-256 per file) |

Rules (non-negotiable):

1. Files under any `protected_roots` path (`configs/paths.yaml`) are **never modified, deleted, renamed,
   moved or overwritten** — by code, by hand, or by tools. This includes changing file attributes.
2. Code opens raw files only through `src/data/io_guard.read_bytes` and writes only through
   `src/data/io_guard` helpers, which refuse any path inside a protected root.
   `tests/test_no_raw_modification.py` enforces this statically and at runtime.
3. Raw data is never committed to Git (`.gitignore`). Only the checksum manifest is committed.
4. All cleaned, reorganised or derived data is written as **new files** under `data/interim/`
   or `data/processed/`. Nothing is written back to raw.
5. Before any processing run, raw files must match the manifest (`scripts/build_manifest.py`
   and `scripts/audit_dataset.py` both check this and stop on mismatch). A mismatch is a
   data-integrity incident: stop, do not regenerate the manifest, record it in `DECISIONS.md`.
6. Newly delivered raw files are added only with `scripts/build_manifest.py --accept-added`
   after a `DECISIONS.md` entry describing the delivery.

## 2. Provenance

Every derived record must be traceable back to raw. Derived tables carry at least:

`file_id`, `source_relpath`, `source_line_no`, `source_id`, `subject_id`, `device_id`

- `source_relpath` is relative to `raw_root`, so provenance survives relocation of the package.
- `file_id` is `rf_` + first 10 hex digits of SHA-1(`source_relpath`) (`src/data/manifest.py`).
- The raw file's SHA-256 is looked up from the manifest; derived artifacts record the manifest's own
  SHA-256 so a result can be tied to an exact raw snapshot.
- Provider-supplied notes in raw filenames (e.g. "누락부분있음" = "part missing") are kept in the
  manifest column `filename_annotation` and must be considered by preprocessing.

## 3. Subject and device identity

**A device ID is never a subject ID.** Device IDs are provenance metadata only.

| subject_id | Source(s) under `raw_root` | device_id | Notes |
|---|---|---|---|
| User01 | `user01/phase_a`, `phase_b`, `phase_c` | unknown | Longitudinal. Phase names were anonymised by the provider. |
| User02 | `user02/mat_22480` | `22480` | Physical mat 22480 |
| User02 | `user02/mat_22482` | `22482` | Physical mat 22482 |
| User02 | `user02/mat_22480/_prefix_mismatch` | unresolved (22480 or 22482) | Quarantined; see §4 |
| User02 | `user02/legacy_csv` | unknown | Legacy CSV export, 2025-10 |
| User03 | `user03_legacy` | unknown | Legacy CSV export; valid auxiliary source (D-017, D-021) |
| User06 | `user06_auxiliary` | unknown | Distinct subject; this source is `excluded_invalid` (provider-confirmed setting issue, D-017). Raw kept. |
| User07 | `user07` | unknown | Folder name was anonymised by the provider |

User02 rule (confirmed by the data provider, DECISIONS D-003):

```
subject_id = User02
device_id  ∈ {22480, 22482}
```

22480 and 22482 are two devices of the same person. They must never be treated as two subjects,
never be split across train/test as if independent, and never be counted as two subjects in any
table or statistic. `tests/test_subject_mapping.py` enforces the mapping.

Identity questions (do not resolve by assumption; see `DECISIONS.md`):
- OPEN-01 — **closed by D-017.** `user03_legacy` rows are contained in `user06_auxiliary`. User03 and User06 are
  different people, and the provider confirmed the User06 source is invalid. It is excluded from analysis; the
  raw files are kept. User03 legacy is valid User03 data and stays auxiliary (D-021).
- OPEN-02: device attribution of the two `_prefix_mismatch` files.
- OPEN-03: the two User02 mats recorded simultaneously for about 505 h.
- OPEN-04: device IDs of every other source are unknown. A11 found no ID in any other file, so mat reuse cannot be
  checked. Sources without an ID stay `unknown`; an ID is never invented.

Sensor phases (D-019) are provenance labels per subject timeline, configured in `configs/subject_mapping.yaml`
(`sensor_phases`). User01 has `s1` and `s2`; every other timeline is `s1`. A phase is never a subject.

Channel-quality phases (D-022) are provenance labels per device timeline, configured in
`configs/subject_mapping.yaml` (`channel_quality_phases`).
- 22482 has `normal`, `p1_transition` and `p1_response_shift`; every other timeline is `normal`.
- The column `channel_quality_flag` names the affected channel (`p1`).
- Flagged values are never changed, removed or imputed. Their use is decided in P2.

## 4. Dataset roles

| Role | Sources | Meaning |
|---|---|---|
| `primary_candidate` | User01 (all phases), User02 `mat_22480`, User02 `mat_22482`, User07 | Main-experiment pool. Cohort membership fixed by D-020 (User01, User02, User07); how these sources are used is fixed with `EXPERIMENT_PROTOCOL.md`. |
| `auxiliary` | User02 `legacy_csv`, User03 `legacy` | Kept separate from the main pool. Usable only under an explicit protocol (e.g. extra training subjects, robustness checks), never as test data for the main claims unless decided. |
| `quarantined` | `user02/mat_22480/_prefix_mismatch/*` | Provenance conflict. Excluded from every analysis until resolved. The subject (User02) is certain; only the device is not. |
| `excluded_invalid` | `user06_auxiliary` (D-017) | Source confirmed invalid (`quality_status: invalid`, with `exclusion_reason`). Excluded from every analysis, model training/evaluation and public dataset. **Analytical exclusion only**: the raw files stay in the archive, unchanged, for provenance. |
| `restricted_metadata` | `user01/metadata/*.xlsx` | Participant metadata. Never model input, never copied, never released (§5). |

Roles are subject-level for leakage purposes: when a subject is held out, **all** of that subject's
sources (including auxiliary legacy data) are excluded from training (`RESEARCH_PROTOCOL.md`, L6).

Code selects analysable sources only through `src/data/subject_mapping.analysis_source_ids()`
(roles `primary_candidate` and `auxiliary`, not `invalid`). No analysis may read an excluded source,
except audits that explicitly document the delivered data (inventory, provenance).

## 5. Privacy and release

Provider confirmation (DECISIONS D-002): the raw data may be used and publicly released for
research, sensitive information was removed, and participant consent was obtained.

Regardless, the following apply to everything that leaves the private workspace
(paper, supplementary files, public repository, figures, talks):

1. Use only anonymous subject IDs (`User01`, `User02`, `User07`, ...). No names, initials, original
   folder names, or device-owner information.
2. **Restricted metadata.** `user01/metadata/*.xlsx` contains demographic and detailed health
   information (conditions, medications, dated medical events). It is classified restricted:
   - not used as model input or for stratification without a `DECISIONS.md` entry,
   - not quoted, summarised per-field, or copied into `docs/`, `outputs/`, `paper/`, or Git,
   - excluded from any public release even though provider consent exists (re-identification risk).
   Non-sensitive operational notes in that file (sensor replacement date, heating-season start,
   log-format change, event-code legend) may be used and cited as study-log facts.
3. **Identifiers inside device logs.** Some raw log lines contain messenger recipient IDs
   (e.g. `chatIDs=<10 digits>` in User06 logs). Device/serial log lines are never carried into
   processed data; audit outputs redact long digit runs (`src/data/raw_parser.redact`).
4. Public data releases are built as a separate, derived release subset with its own manifest.
   The private raw package is never published as-is (provider README, "Before publication").
   - Sources that are not analysis-eligible (`excluded_invalid`, `quarantined`, `restricted_metadata`) are not
     part of the canonical public analysis dataset. **The User06 source is not released as analysis data.**
   - The release manifest lists every excluded source with `source_id`, `exclusion_reason`,
     `exclusion_confirmed_by` and `exclusion_decision`. The fields come from `configs/subject_mapping.yaml`
     via `src/data/subject_mapping.excluded_sources()`. This documents what was left out and why, without
     publishing it.
5. Exact calendar dates combined with health events can re-identify a person. Whether public
   releases use absolute dates or relative day indices is an open decision (OPEN-18).
