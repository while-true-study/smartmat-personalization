# Decisions

Single source of truth for research decisions and their rationale.

Rules:
- Entries are listed in ID order (chronological) and are append-only. To change a decision, add a new
  entry and set the old one's status to `Superseded by D-XXX`; never rewrite its content.
- Status values: `Proposed`, `Accepted`, `Rejected`, `Superseded by D-XXX`.
- Rationale must never cite test-set results. If a decision is taken after any experimental result was
  seen, the entry must say so and name the results (RESEARCH_PROTOCOL §6).
- Format of every entry:

```
## D-XXX — Decision title
Date:
Status:
Context:
Decision:
Evidence:
Consequence:
```

---

## Open decisions

Do not resolve these by assumption. Each is closed by a decision entry below.
Evidence: `docs/initial_dataset_inventory.md`. Analyses planned for P0: `docs/P0_DATASET_AUDIT_PLAN.md`.

| ID | Question | Owner | Resolve in | Blocks | Tracking |
|---|---|---|---|---|---|
| OPEN-01 | **Identity answered:** User03 ≠ User06 (PI, 2026-09-12; D-013). **Still open: measurement provenance** — why the rows of `user03_legacy` are contained in User06's recordings of 2025-10-06…10-13, and to which subject those measurements belong. Until then the overlapping recording is provisionally quarantined from primary evaluation (D-013). Original question: `user03_legacy` is a seconds-truncated copy of `user06_auxiliary` for 2025-10-06…10-12 (99.99–100 % of User03 rows found in User06). **A1 evidence (2026-09-12):** 100 % of User03 rows (minute-level) and 100 % of its 5-row value sequences occur in User06; offsets 0–59 s; each User03 file is a contiguous excerpt of one User06 night file; ordered runs up to 13,180 sequences. Overlap is inconsistent with independent subject recordings; identity still unconfirmed. No other subject pair shares any data. | data provider | P0 | any use of User03/User06 | `docs/issues/P0-01_user03-user06-provenance.md`; `docs/P0_A1_PROVENANCE_REPORT.md` §4; `outputs/qa/p0/provenance/` |
| OPEN-02 | Device of `user02/mat_22480/_prefix_mismatch/sm22482_0824.txt` and `…_0825.txt`. Evidence favours 22482 (filename prefix, JSON root key `smartmat_22482`, the only dates with a 22480 file but no 22482 file). A1: the two files share no rows with either device's files (not duplicates). **A2 evidence (2026-09-12):** they fill 22482's timeline seamlessly (start 30 min after 22482's last row, end 3 s before its next row), record simultaneously with 22480's own stream for 7.0 h, and match 22482's humidity regime (22480 − quarantined: −2 °C / −16 %RH vs typical 22480 − 22482: −2 / −19). Strong, consistent evidence for 22482; attribution still `unresolved` pending provider confirmation. | data provider | P0 | use of those 2 files | `docs/issues/P0-02_user02-dual-device-protocol.md`; `docs/P0_A1_PROVENANCE_REPORT.md` §5; `docs/P0_A2_USER02_DEVICE_REPORT.md` §9 |
| OPEN-03 | Physical setup of User02's mats 22480/22482: they overlap for ~505 h and both register occupancy in 66.8 % of jointly recorded minutes, with different temperature/humidity. Same bed (body regions)? Different locations? How to use two concurrent streams (separate, one, fused)? A1: 46 co-recorded dates, 0 shared rows or sequences — concurrent but distinct streams. **A2 evidence (2026-09-12):** 253 h simultaneous recording (76 % of 22480's time); no pressure coupling (|r| ≤ 0.03 for all descriptors, no lag peak within ±30 s, movement-event coincidence at chance level, no clock offset found within ±12 h); occupancy agreement at chance under all 14 definitions (κ −0.07…0.00, "both active" 18–90 % depending on threshold); persistent T/H offset (22480 − 22482: −2 °C, −19 %RH; humidity lower on 46/46 dates); different channel-load patterns. Physical placement and the use policy for the two streams remain unresolved. | provider + PI | P0 | User02 in primary cohort | `docs/issues/P0-02_user02-dual-device-protocol.md`; `docs/P0_A1_PROVENANCE_REPORT.md` §5; `docs/P0_A2_USER02_DEVICE_REPORT.md` |
| OPEN-04 | Device IDs of User01, User07, User02 legacy, User03, User06. Recording periods hand over day-to-day (User01 → User07 → User02), suggesting reused mats. Subject and device may be confounded. | data provider | P0 | RQ1 interpretation | — |
| OPEN-05 | Move the raw package into `data/raw/` or keep it at `스마트 매트 데이터 정리/`? | PI | P0 | nothing (path is configurable) | — |
| OPEN-06 | Session definition (files ≠ sessions: files overlap and some span 30–57 h). | PI | P0 | splits | — |
| OPEN-07 | De-duplication policy for ~204 k identical rows shared by adjacent files, and for repeated rows/timestamps within files. | PI | P0 | interim tables | — |
| OPEN-08 | Timestamp policy: year inference for MM-DD rows, legacy minute-resolution rows, timezone, and the out-of-order steps. | PI | P0 | interim tables | — |
| OPEN-09 | Handling of temp/humid sentinel zeros (chunk starts) and glitch values (−254, 256, 262). | PI | P0 | targets | — |
| OPEN-10 | Target definition under heater control: the T/H sensor measures a heater-controlled microclimate. Is heater state a covariate, a stratifier, or excluded? | PI | P2 (informed by P0/P1) | RQ1–RQ3 | — |
| OPEN-11 | User01 pressure-sensor replacement on 2026-01-25: treat as distribution shift boundary? Effect on the chronological adaptation protocol. | PI | P0 analysis, P2 decision | RQ2 | — |
| OPEN-12 | Adopt "`.` before P1 is a delimiter" for User06 files 1003–1011 in preprocessing (strong evidence; see inventory §8.3). A1: under this reading User06 rows align exactly with User03 rows, which have a separate `FSR1` column. | PI | P0 | User06 use | `docs/P0_A1_PROVENANCE_REPORT.md` §4.4 |
| OPEN-13 | Whether and how auxiliary subjects enter training pools. | PI | P0 | RQ1 | — |
| OPEN-14 | Metadata date inconsistencies (e.g. heating start written as 2026-11-18, log-format change as 2026-12-17; data suggest 2025). | data provider | P0 | covariate timeline | — |
| OPEN-15 | Admissibility of firmware movement labels (UM/DM/LM/RM/NM) as model inputs / movement-derived features. | PI | P2 | RQ3 | — |
| OPEN-16 | Final primary cohort. Three candidates give only three LOSO folds; statistical plan must reflect this. Provisional primary cohort: User01, User02, User07 (D-013). | PI | P0 | RQ1 | — |
| OPEN-17 | Pressure-scale differences between subjects/periods (User01 saturates at 4095; User02 max 3731; User07 max 4023): normalisation strategy that respects L3/L11. | PI | P2 | preprocessing | — |
| OPEN-18 | Public release: absolute dates or relative day indices. | PI + provider | P7 | release | — |

---

## D-001 — Canonical, tool-independent documentation
Date: 2026-09-12
Status: Accepted
Context: Research rules must not depend on a particular AI tool or editor.
Decision: Research rules live only in `docs/` (`CONVENTIONS`, `RESEARCH_PROTOCOL`, `DATA_POLICY`,
`DECISIONS`, `EXPERIMENT_PROTOCOL`). `AGENTS.md` is a short entry point; `CLAUDE.md` is a thin adapter
pointing to `AGENTS.md`. No rules are duplicated in tool-specific files.
Evidence: —
Consequence: One source of truth; tool-specific files only link to `docs/`.

## D-002 — Data provider confirmation on use, release and consent
Date: 2026-09-12
Status: Accepted
Context: The repository is intended to be public and to support a public data release.
Decision:
- Data provider confirmed that raw data may be used and publicly released for research.
- Sensitive information had already been removed.
- Participant consent had been obtained.
- Public releases should still use anonymous subject IDs.
Evidence: Provider statement relayed by the PI on 2026-09-12.
Consequence: Release is permitted in principle. Note (added after inventory): `user01/metadata/*.xlsx`
still contains detailed demographic and health fields. It is classified `restricted_metadata` and
excluded from any release (DATA_POLICY §5, D-008). This does not contradict the provider's statement
but is handled conservatively.

## D-003 — User02 device mapping
Date: 2026-09-12
Status: Accepted
Context: User02's newer logs come from two physical mats, 22480 and 22482.
Decision: `subject_id = User02`, `device_id ∈ {22480, 22482}`. The two IDs are devices of one person,
never separate subjects.
Evidence: Confirmed by the data provider; also stated in the provider's package README.
Consequence: Enforced by `configs/subject_mapping.yaml` and `tests/test_subject_mapping.py`. How the
two concurrent streams are used remains open (OPEN-03).

## D-004 — Dataset roles
Date: 2026-09-12
Status: Accepted (as candidates; cohort not frozen)
Context: Sources differ in firmware, timestamp policy and completeness.
Decision: Primary candidates = User01, User02 (new mat logs), User07; auxiliary = User02 legacy CSV,
User03 legacy, User06; restricted metadata = `user01/metadata`.
Evidence: Provided by the PI; legacy sources differ in timestamp policy and firmware.
Consequence: Candidates only; the frozen cohort is decided in P0 (OPEN-16).

## D-005 — Raw package left in place
Date: 2026-09-12
Status: Accepted
Context: The delivered raw folder is the source of truth.
Decision: The delivered package stays at `스마트 매트 데이터 정리/`; it was not moved or copied into
`data/raw/`. `configs/paths.yaml:raw_root` points to it; both locations are write-protected and
git-ignored.
Evidence: —
Consequence: The manifest stores paths relative to `raw_root`, so a later move changes one config line.
Relocation remains a PI decision (OPEN-05).

## D-006 — Prefix-mismatch files quarantined
Date: 2026-09-12
Status: Accepted
Context: Two files in the 22480 archive carry the `sm22482_` prefix.
Decision: `user02/mat_22480/_prefix_mismatch/*` get `device_id = unresolved`,
`dataset_role = quarantined`. Subject remains User02.
Evidence: Provider already isolated them; content evidence points to 22482 (inventory §8.1) but is not
confirmation.
Consequence: Excluded from all analyses until OPEN-02 is resolved. Silent reassignment is not allowed.

## D-007 — Audit-only parsing interpretations (non-binding for preprocessing)
Date: 2026-09-12
Status: Accepted (audit scope only)
Context: The inventory needed dated rows from several raw format families.
Decision: The P0 audit parser (`src/data/raw_parser.py`) reads files line by line (the JSON-like files
are not valid JSON), infers the year of `MM-DD` rows from the enclosing JSON log key, else the next key
in the file, else `year_hint` in `configs/subject_mapping.yaml` (User01 phase_b 2025, phase_c 2026,
User07 2026), and treats `.` between timestamp and P1 as a delimiter.
Evidence: inventory §5 and §8.3.
Consequence: Used only for inventory statistics. Preprocessing must adopt them explicitly (OPEN-08, OPEN-12).

## D-008 — Restricted metadata
Date: 2026-09-12
Status: Accepted
Context: `user01/metadata/meta_legacy_package.xlsx` and `meta_longitudinal.xlsx` contain demographic
and health information.
Decision: Both are `restricted_metadata`: not model input, not copied or summarised field-by-field
outside raw, not released. `*.xlsx` is git-ignored repository-wide.
Evidence: Inventory §9 (contents deliberately not reproduced).
Consequence: Only operational study-log facts may be used (pressure-sensor replacement 2026-01-25,
heating season start, log-format change, event-code legend).

## D-009 — Git initialised
Date: 2026-09-12
Status: Accepted
Context: `.gitignore` rules needed to be verifiable by tests.
Decision: `git init` was run. At the time of this entry no commit had been made.
Evidence: —
Consequence: The first commit (`1794418`, "Initial research repository setup") was later pushed to
`origin/main` on 2026-09-12 (see D-010).

## D-010 — Phased research lifecycle and Git workflow
Date: 2026-09-12
Status: Accepted
Context: The repository is public and serves as the companion record of an MDPI paper. Decisions about
data, splits and protocol must be traceable to the phase in which they were made, and results must be
linkable to the code and data that produced them.
Decision:
- The study follows nine fixed phases P0–P8 with exit criteria and freeze tags
  (`RESEARCH_PROTOCOL.md` §5).
- Git mechanics: one branch per phase created only after the previous phase is merged, PR per phase
  as research record (`.github/pull_request_template.md`), annotated freeze tags only at
  `p0-data-freeze`, `p2-protocol-freeze`, `p3-loso-baseline`, `p5-personalization`, `v1.0-paper`,
  single-line research-step commit messages without AI attribution (`CONVENTIONS.md` §6).
- Decision entries use the Date/Status/Context/Decision/Evidence/Consequence format. D-001–D-009 were
  converted to this format on 2026-09-12 without changing their content.
Evidence: PI instruction, 2026-09-12. First commit `1794418` on `main`.
Consequence: `main` holds only completed phases. No P1+ branch or tag exists until P0 is merged.

## D-011 — Track `data/raw/README.md`
Date: 2026-09-12
Status: Accepted
Context: The first commit excluded `data/raw/README.md` under a conservative "nothing under data/raw"
staging rule, so the public repository did not show where raw data belong or how they are protected.
Decision: `data/raw/README.md` is the only tracked file under `data/raw/`. It contains no raw filenames
or identifiers. All other paths under `data/raw/` stay git-ignored.
Evidence: `.gitignore` (`/data/raw/*`, `!/data/raw/README.md`); `tests/test_no_raw_modification.py`
(`test_no_raw_file_is_tracked`) allows exactly this file.
Consequence: Raw data remain local-only.

## D-012 — Start P0; no strict cohort before provenance issues are resolved
Date: 2026-09-12
Status: Accepted
Context: The inventory found identity and provenance conflicts (OPEN-01–OPEN-04), overlapping files,
sentinels/glitches, a sensor replacement and period/season confounding.
Decision: P0 (Dataset Audit & Data Freeze) starts on `research/p0-data-freeze` following
`docs/P0_DATASET_AUDIT_PLAN.md`. The strict cohort is not decided until the P0 blocking items are
resolved. During P0 no model training, window generation, resampling, interpolation, normalisation,
split generation, feature extraction or hyperparameter search is performed.
Evidence: `docs/initial_dataset_inventory.md` §7–§10.
Consequence: P0 ends with the cohort decision and the `p0-data-freeze` tag after merge into `main`.

## D-013 — User03 ≠ User06; provisional quarantine of their overlapping recording; provisional primary cohort
Date: 2026-09-12
Status: Accepted (provisional — to be superseded once the data provider clarifies the measurement provenance)
Context: P0-A1 found that 100 % of `user03_legacy` sensor rows (107,256, minute resolution) and 100 % of its
value sequences are contained in `user06_auxiliary` recordings of the nights 2025-10-06 → 10-13. The PI
relayed that User03 and User06 are different people.
Decision:
- User03 and User06 remain two distinct subjects (User03 ≠ User06). They are not merged.
- Whether the overlapping measurements are independent is unresolved. The overlap covers all of `user03_legacy`
  and the User06 nights 2025-10-06 → 10-13 that contain it.
- Until the provider clarifies the provenance, this overlapping recording is **provisionally quarantined**:
  it is not used in primary evaluation. Any other use (e.g. an auxiliary training pool) needs its own decision
  (OPEN-13). Neither subject is deleted or finally excluded. User06's non-overlapping recordings keep their
  auxiliary role.
- User01, User02 and User07 form the **provisional primary cohort**. P0 continues on that basis.
Evidence: `docs/P0_A1_PROVENANCE_REPORT.md` §4; `outputs/qa/p0/provenance/`; PI statement of 2026-09-12 that
User03 and User06 are different users.
Consequence: OPEN-01 is narrowed to measurement provenance. `configs/subject_mapping.yaml` is unchanged
(roles stay `auxiliary`); the quarantine will be encoded in the cohort definition when the cohort is frozen at
P0 exit. OPEN-16 (final cohort) stays open.
