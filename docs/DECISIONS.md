# Decisions

Dated record of research decisions and their rationale. Newest date first.
Entries are append-only: to reverse a decision, add a new entry that supersedes it.
Rationale must never cite test-set results.

---

## Open decisions (blocking or pending)

Do not resolve these by assumption. Each needs an explicit, dated decision entry.
Evidence: `docs/initial_dataset_inventory.md`.

| ID | Question | Owner | Blocks |
|---|---|---|---|
| OPEN-01 | `user03_legacy` is a seconds-truncated copy of `user06_auxiliary` for 2025-10-06…10-12 (99.99–100 % of User03 rows found in User06). Same person, mislabelled folder, or derived export? Which ID survives? | data provider | any use of User03/User06 |
| OPEN-02 | Device of `user02/mat_22480/_prefix_mismatch/sm22482_0824.txt` and `…_0825.txt`. Evidence favours 22482 (filename prefix, JSON root key `smartmat_22482`, the only missing dates in `mat_22482`). | data provider | use of those 2 files |
| OPEN-03 | Physical setup of User02's mats 22480/22482: they overlap for ~505 h and both register occupancy in 66.8 % of jointly recorded minutes, with different temperature/humidity. Same bed (body regions)? Different locations? How to use two concurrent streams (separate, one, fused)? | provider + PI | User02 in primary cohort |
| OPEN-04 | Device IDs of User01, User07, User02 legacy, User03, User06. Recording periods hand over day-to-day (User01 → User07 → User02), suggesting reused mats. Subject and device may be confounded. | data provider | RQ1 interpretation |
| OPEN-05 | Move the raw package into `data/raw/` or keep it at `스마트 매트 데이터 정리/`? | PI | nothing (path is configurable) |
| OPEN-06 | Session definition (files ≠ sessions: files overlap and some span 30–57 h). | PI | splits |
| OPEN-07 | De-duplication policy for ~204 k identical rows shared by adjacent files, and for repeated rows/timestamps within files. | PI | interim tables |
| OPEN-08 | Timestamp policy: year inference for MM-DD rows, legacy minute-resolution rows, timezone, and the out-of-order steps. | PI | interim tables |
| OPEN-09 | Handling of temp/humid sentinel zeros (chunk starts) and glitch values (−254, 256, 262). | PI | targets |
| OPEN-10 | Target definition under heater control: the T/H sensor measures a heater-controlled microclimate. Is heater state a covariate, a stratifier, or excluded? | PI | RQ1–RQ3 |
| OPEN-11 | User01 pressure-sensor replacement on 2026-01-25: treat as distribution shift boundary? Effect on the chronological adaptation protocol. | PI | RQ2 |
| OPEN-12 | Adopt "`.` before P1 is a delimiter" for User06 files 1003–1011 in preprocessing (strong evidence; see inventory §8.3). | PI | User06 use |
| OPEN-13 | Whether and how auxiliary subjects enter training pools. | PI | RQ1 |
| OPEN-14 | Metadata date inconsistencies (e.g. heating start written as 2026-11-18, log-format change as 2026-12-17; data suggest 2025). | data provider | covariate timeline |
| OPEN-15 | Admissibility of firmware movement labels (UM/DM/LM/RM/NM) as model inputs / movement-derived features. | PI | RQ3 |
| OPEN-16 | Final primary cohort. Three candidates give only three LOSO folds; statistical plan must reflect this. | PI | RQ1 |
| OPEN-17 | Pressure-scale differences between subjects/periods (User01 saturates at 4095; User02 max 3731; User07 max 4023): normalisation strategy that respects L3/L11. | PI | preprocessing |
| OPEN-18 | Public release: absolute dates or relative day indices. | PI + provider | release |

---

## 2026-09-12

### D-001 Canonical, tool-independent documentation
- Decision: research rules live only in `docs/` (`CONVENTIONS`, `RESEARCH_PROTOCOL`, `DATA_POLICY`,
  `DECISIONS`, `EXPERIMENT_PROTOCOL`). `AGENTS.md` is a short entry point; `CLAUDE.md` is a thin
  adapter pointing to `AGENTS.md`. No rules are duplicated in tool-specific files.
- Rationale: one source of truth, independent of any AI tool or editor.

### D-002 Data provider confirmation on use, release and consent
- Data provider confirmed that raw data may be used and publicly released for research.
- Sensitive information had already been removed.
- Participant consent had been obtained.
- Public releases should still use anonymous subject IDs.
- Note (added after inventory): `user01/metadata/*.xlsx` still contains detailed demographic and health
  fields. It is classified `restricted_metadata` and excluded from any release (DATA_POLICY §5).
  This does not contradict the provider's statement but is handled conservatively.

### D-003 User02 device mapping
- Decision: `subject_id = User02`, `device_id ∈ {22480, 22482}`. The two IDs are devices of one
  person, never separate subjects.
- Rationale: confirmed by the data provider; also stated in the provider's package README.
- Enforcement: `configs/subject_mapping.yaml`, `tests/test_subject_mapping.py`.

### D-004 Dataset roles
- Decision: primary candidates = User01, User02 (new mat logs), User07; auxiliary = User02 legacy CSV,
  User03 legacy, User06; restricted metadata = `user01/metadata`.
- Rationale: provided by the PI; legacy sources differ in timestamp policy and firmware.
- Status: candidates, not a frozen cohort (OPEN-16).

### D-005 Raw package left in place
- Decision: the delivered package stays at `스마트 매트 데이터 정리/`; it was not moved or copied into
  `data/raw/`. `configs/paths.yaml:raw_root` points to it; both locations are write-protected and
  git-ignored. The manifest stores paths relative to `raw_root`, so a later move changes one config line.
- Rationale: the delivered folder is the source of truth; relocating it is a decision for the PI (OPEN-05).

### D-006 Prefix-mismatch files quarantined
- Decision: `user02/mat_22480/_prefix_mismatch/*` get `device_id = unresolved`,
  `dataset_role = quarantined`. Subject remains User02.
- Rationale: provider already isolated them; content evidence points to 22482 but is not confirmation
  (OPEN-02). Silent reassignment is not allowed.

### D-007 Audit-only parsing interpretations (non-binding for preprocessing)
- The P0 audit parser (`src/data/raw_parser.py`) reads files line by line (the JSON-like files are not
  valid JSON), infers the year of `MM-DD` rows from the enclosing JSON log key, else the next key in the
  file, else `year_hint` in `configs/subject_mapping.yaml` (User01 phase_b 2025, phase_c 2026,
  User07 2026), and treats `.` between timestamp and P1 as a delimiter.
- These choices are used only for inventory statistics. Preprocessing must adopt them explicitly
  (OPEN-08, OPEN-12).

### D-008 Restricted metadata
- Decision: `user01/metadata/meta_legacy_package.xlsx` and `meta_longitudinal.xlsx` are
  `restricted_metadata`: not model input, not copied or summarised field-by-field outside raw, not
  released. `*.xlsx` is git-ignored repository-wide.
- Usable facts (operational study log, not personal data): pressure-sensor replacement 2026-01-25,
  heating season start, log-format change, event-code legend.

### D-009 Git initialised, nothing committed
- Decision: `git init` was run so `.gitignore` rules can be verified by tests. No commit has been made.
