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
| OPEN-01 | **Closed 2026-09-13 by D-017:** provider confirmed the User06 source is invalid (setting issue). User06 source `excluded_invalid` (raw kept); User03 legacy stays auxiliary; subjects not merged. History: **Identity answered:** User03 ≠ User06 (PI, 2026-09-12; D-013). **Still open: measurement provenance** — why the rows of `user03_legacy` are contained in User06's recordings of 2025-10-06…10-13, and to which subject those measurements belong. Until then the overlapping recording is provisionally quarantined from primary evaluation (D-013). Original question: `user03_legacy` is a seconds-truncated copy of `user06_auxiliary` for 2025-10-06…10-12 (99.99–100 % of User03 rows found in User06). **A1 evidence (2026-09-12):** 100 % of User03 rows (minute-level) and 100 % of its 5-row value sequences occur in User06; offsets 0–59 s; each User03 file is a contiguous excerpt of one User06 night file; ordered runs up to 13,180 sequences. Overlap is inconsistent with independent subject recordings; identity still unconfirmed. No other subject pair shares any data. | data provider | P0 | any use of User03/User06 | `docs/issues/P0-01_user03-user06-provenance.md`; `docs/P0_A1_PROVENANCE_REPORT.md` §4; `outputs/qa/p0/provenance/` |
| OPEN-02 | Device of `user02/mat_22480/_prefix_mismatch/sm22482_0824.txt` and `…_0825.txt`. Evidence favours 22482 (filename prefix, JSON root key `smartmat_22482`, the only dates with a 22480 file but no 22482 file). A1: the two files share no rows with either device's files (not duplicates). **A2 evidence (2026-09-12):** they fill 22482's timeline seamlessly (start 30 min after 22482's last row, end 3 s before its next row), record simultaneously with 22480's own stream for 7.0 h, and match 22482's humidity regime (22480 − quarantined: −2 °C / −16 %RH vs typical 22480 − 22482: −2 / −19). Strong, consistent evidence for 22482; attribution still `unresolved` pending provider confirmation. A5: the gap between the two quarantined files (1,804 s) and their start relative to 22482 (1,806 s) follow 22482's lost-upload-chunk pattern (n × 1,800 s + a few s). | data provider | P0 | use of those 2 files | `docs/issues/P0-02_user02-dual-device-protocol.md`; `docs/P0_A1_PROVENANCE_REPORT.md` §5; `docs/P0_A2_USER02_DEVICE_REPORT.md` §9; `docs/P0_A5_DUPLICATE_OVERLAP_REPORT.md` §6 |
| OPEN-03 | Physical setup of User02's mats 22480/22482: they overlap for ~505 h and both register occupancy in 66.8 % of jointly recorded minutes, with different temperature/humidity. Same bed (body regions)? Different locations? How to use two concurrent streams (separate, one, fused)? A1: 46 co-recorded dates, 0 shared rows or sequences — concurrent but distinct streams. **A2 evidence (2026-09-12):** 253 h simultaneous recording (76 % of 22480's time); no pressure coupling (|r| ≤ 0.03 for all descriptors, no lag peak within ±30 s, movement-event coincidence at chance level, no clock offset found within ±12 h); occupancy agreement at chance under all 14 definitions (κ −0.07…0.00, "both active" 18–90 % depending on threshold); persistent T/H offset (22480 − 22482: −2 °C, −19 %RH; humidity lower on 46/46 dates); different channel-load patterns. Physical placement and the use policy for the two streams remain unresolved. | provider + PI | P0 | User02 in primary cohort | `docs/issues/P0-02_user02-dual-device-protocol.md`; `docs/P0_A1_PROVENANCE_REPORT.md` §5; `docs/P0_A2_USER02_DEVICE_REPORT.md` |
| OPEN-04 | Device IDs of User01, User07, User02 legacy, User03, User06. Recording periods hand over day-to-day (User01 → User07 → User02), suggesting reused mats. Subject and device may be confounded. | data provider | P0 | RQ1 interpretation | — |
| OPEN-05 | Move the raw package into `data/raw/` or keep it at `스마트 매트 데이터 정리/`? | PI | P0 | nothing (path is configurable) | — |
| OPEN-06 | Session definition (files ≠ sessions: files overlap and some span 30–57 h). **A5 evidence (2026-09-12):** confirmed quantitatively. Files hold parts of two nights (internal gap > 2 h in User01 12, 22480 3, 22482 29, User07 3 files). 22482 nights are split across files at 06:1x–09:1x with recording continuing 2–5 s later (10 boundaries), and 13 cuts lost exactly 1–3 upload chunks (n × 1,800 s + 3–8 s). 18 primary-group boundaries overlap through repeated chunks. For User01/22480/User07 most boundaries (139/150, 41/44, 97/99) fall in > 2 h gaps. No gap threshold chosen; pending A7. **A7 evidence (2026-09-12):**
- Sampling is 3 s nominal (p99 5 s) on all primary timelines.
- Gaps are bimodal: ≤ 5 min or > 2 h, with only 1–19 gaps per timeline between them.
- User01/User07 have a recurring ≈ 2-min pause (120–140 s), unrelated to upload chunks.
- Thresholds < 5 min fragment nights. 5–90 min is a plateau (≈ 1 session per night) for User01, 22480 and User07.
- 22482 has no plateau because 13 gaps are exactly 1–3 lost upload chunks at morning file cuts (mat mostly occupied on both sides). Bridging them gives 1.12–1.24 sessions per night.
- Session lengths are quantised in 30-min chunks.
- Timeline A vs de-duplicated view: identical session structure.
Candidate policy proposed as D-015 (Proposed); not accepted. | PI | P0 | splits | `docs/P0_A5_DUPLICATE_OVERLAP_REPORT.md` §6; `docs/P0_A7_TEMPORAL_GAP_REPORT.md`; D-015 |
| OPEN-07 | De-duplication policy for ~204 k identical rows shared by adjacent files, and for repeated rows/timestamps within files. **A5 evidence (2026-09-12):** in the primary groups all file overlaps are exact duplicate blocks (18 pairs; all 300 repeated chunk keys identical). Repeated copies never disagree (0 between-file conflicts). Cross-file exact copies: 187,190 rows (4.33 %), plus one 600-row chunk repeated inside `sm22482_0816`. Separately, 10,997 same-second timestamps carry two *different* readings inside one file (not duplicates), 272 adjacent same-second rows are identical, and 4 rows differ only in event text. Proposal: D-014 (Proposed). A7 note: removing copied blocks row for row removes 187,814 rows in the primary groups. That is 24 more than A1 + 600, because 24 same-second identical pairs were copied along with their chunk; the originals remain. | PI | P0 | interim tables | `docs/P0_A5_DUPLICATE_OVERLAP_REPORT.md`; `docs/P0_A7_TEMPORAL_GAP_REPORT.md` §1; D-014 |
| OPEN-08 | Timestamp policy: year inference for MM-DD rows, legacy minute-resolution rows, timezone, and the out-of-order steps. | PI | P0 | interim tables | — |
| OPEN-09 | Handling of temp/humid sentinel zeros (chunk starts) and glitch values (−254, 256, 262). **A8 evidence (2026-09-13):**<br>• Invalid-candidate targets are 0.10 % of primary rows (4,132 of 4,136,059); no missing or non-finite values.<br>• Joint zeros (T = H = 0) arise from two mechanisms: single-row start sentinels at a recording/chunk start (125 / 51 / 61 / 118 rows in User01 / 22480 / 22482 / User07), and dropout episodes. 86 % of all zero rows fall in two episodes: User01 2025-12-28 daytime, and 22482 night 2026-08-08/09.<br>• All 147 extreme values (T −254, 171–256; H 135–262) are in that 22482 night.<br>• No abrupt jump or spike exists between valid observations within 5 s (max 1–2 °C, p99.9 1 %RH).<br>• The 148 same-second target conflicts are ±1 quantisation steps (119) or zero-vs-reading (29).<br>Flagging proposed as D-016 (Proposed); episode-level exclusion, clipping, interpolation and jump thresholds are not decided. | PI | P0 | targets | `docs/P0_A8_TARGET_QUALITY_REPORT.md`; D-016 |
| OPEN-10 | Target definition under heater control: the T/H sensor measures a heater-controlled microclimate. Is heater state a covariate, a stratifier, or excluded? **A8 note (2026-09-13):** long constant-temperature runs (≥ 1 h cover 84 % of 22480 and 80 % of User07 recording time; 22480 is at 28–30 °C in 96 % of rows) while humidity keeps moving. This is consistent with 1 °C quantisation of a stable or regulated microclimate, not a frozen sensor. The cause and whether regulated periods are meaningful targets remain open. | PI | P2 (informed by P0/P1) | RQ1–RQ3 | `docs/P0_A8_TARGET_QUALITY_REPORT.md` §5 |
| OPEN-11 | User01 pressure-sensor replacement on 2026-01-25: treat as distribution shift boundary? Effect on the chronological adaptation protocol. **A9 baseline evidence (2026-09-13):** a step, not a drift, between the morning and evening recordings of 2026-01-25. Rows with a channel at 4095: 22.1 % before, 18 rows (0.002 %) after. Pressure-sum median 4,420 → 2,976, p95 10,157 → 5,022. Mean active channels 2.07 → 3.55. The full before/after comparison is A10. **A10 evidence (2026-09-13):**<br>• The change sits in the 9.4 h recording gap 2026-01-25 08:07:26 → 17:31:21. It is the strongest change point of the User01 series (core consensus rank 1 for nights and sessions at w = 3 and 7).<br>• Nights ±14: the 4095 share drops from 16.0 % to 0, p95 from 10,889 to 5,355 and the median from 6,087 to 3,361; active channels rise from 2.72 to 3.66. Cliff's δ = ±1 with complete separation; placebo windows show no separation.<br>• The step fits better than a line. Duration, clock time, temperature, humidity and sampling are continuous across the gap.<br>• High values compress (P2/P3/P5 about ⅓ when active), while P1/P5/P6 respond more often.<br>**The boundary question is answered by D-019** (`sensor_phase` s1/s2, provenance only). Still open for P2: phase-aware preprocessing, scaling and evaluation, and whether adaptation/test spans may cross the boundary. | PI | P2 (handling) | RQ2 | `docs/P0_A10_USER01_SENSOR_PHASE_REPORT.md`; D-019 |
| OPEN-12 | **Moot after D-017** (User06 source excluded; relevant only if it were ever re-admitted). Adopt "`.` before P1 is a delimiter" for User06 files 1003–1011 in preprocessing (strong evidence; see inventory §8.3). A1: under this reading User06 rows align exactly with User03 rows, which have a separate `FSR1` column. | PI | — | nothing (source excluded) | `docs/P0_A1_PROVENANCE_REPORT.md` §4.4; D-017 |
| OPEN-13 | Whether and how auxiliary subjects enter training pools. After D-017 the auxiliary pool is User02 legacy and User03 legacy, both minute-resolution. User03 legacy rows are the same measurements as part of the invalid User06 recording; whether the setting issue also affects them is unconfirmed. A9 (2026-09-13): User02 legacy P5 is at 4095 in 50.8 % of rows (runs up to ≈ 112 min); User03 legacy P3–P5 at 4095 in 7–10 % of rows. | PI | P0 | RQ1 | D-017; `docs/P0_A9_PRESSURE_QUALITY_REPORT.md` §3 |
| OPEN-14 | Metadata date inconsistencies (e.g. heating start written as 2026-11-18, log-format change as 2026-12-17; data suggest 2025). | data provider | P0 | covariate timeline | — |
| OPEN-15 | Admissibility of firmware movement labels (UM/DM/LM/RM/NM) as model inputs / movement-derived features. | PI | P2 | RQ3 | — |
| OPEN-16 | Final primary cohort. Three candidates give only three LOSO folds; statistical plan must reflect this. Provisional primary cohort: User01, User02, User07 (D-013, restated in D-017). | PI | P0 | RQ1 | — |
| OPEN-17 | Pressure-scale differences between subjects/periods (User01 saturates at 4095; User02 max 3731; User07 max 4023): normalisation strategy that respects L3/L11. **A9 evidence (2026-09-13):**<br>• All sources have six populated channels. There are no missing channels, no non-standard layouts and no out-of-range or non-integer values.<br>• 4095 is a pile-up at the ceiling (275,601 cells vs 789 at 4094). 99.99 % of these cells are in User01 before the sensor change. 22480 has 17 cells; 22482 and User07 have none.<br>• Every non-zero constant run ≥ 1 min is a 4095 plateau. There is no interior-value stuck channel and no frozen frame on the current mats.<br>• Pressure-sum medians: User01 3,817 (old sensor ≈ 4,420, new ≈ 2,976) vs 1,764–2,037 on the current mats. Channel profiles differ (22482 more even).<br>Proposed input-validity rule D-018; 4095 handling and scaling stay open (P2, training data only). | PI | P2 | preprocessing | `docs/P0_A9_PRESSURE_QUALITY_REPORT.md`; D-018 |
| OPEN-18 | Public release: absolute dates or relative day indices. | PI + provider | P7 | release | — |
| OPEN-19 | User02/22482 channel P1 from 2026-08-20 (A9): active share 0.49 → 0.13, median when active 759 → 26, p99 2,007 → 371. P6 active share 0.57 → 0.28 over the same dates. P2–P5 unchanged; the other mat (22480) shows no such drop. Was the mat moved, replaced or damaged? Use of 22482 data after that date as test/adaptation data depends on it. | data provider + PI | P0 (question), P2 (handling) | User02 splits | `docs/P0_A9_PRESSURE_QUALITY_REPORT.md` §5 |
| OPEN-20 | Physical layout of P1–P6 on the mat and the legacy `FSR_k` ↔ P_k mapping (positional assumption). A9: the strongest positive correlations are P1–P4, P2–P5, P3–P6 on all current mats. This is compatible with, but not proof of, paired positions. Needed before any spatial or channel-selection feature. | data provider | P0 (question), P2 | spatial features | `docs/P0_A9_PRESSURE_QUALITY_REPORT.md` §2, §6 |
| OPEN-21 | Other User01 acquisition changes inside `sensor_phase` s1 (A10):<br>• **2025-12-17**, the documented log-format change (first compressed log): active channels 1.51 → 2.49 and dominant-channel switches 29 → 92 /h, both with complete separation over ±7 nights. The 4095 share is unchanged.<br>• **2026-01-03…07**: a temporary 2 s sampling regime, with the 4095 share dipping for about a week.<br>• From **2026-01-08**: 3 s sampling with wider jitter.<br>• **2025-12-25**: an undocumented +49 % pressure-sum level shift.<br>Did firmware/logging changes alter pressure reporting? Should acquisition-period labels (log format, sampling regime) be carried as further provenance fields? Not merged into `sensor_phase`. | data provider + PI | P0 (question), P2 (handling) | RQ2 spans within User01 | `docs/P0_A10_USER01_SENSOR_PHASE_REPORT.md` §6, §8 |

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
Status: Accepted (as candidates; cohort not frozen). The User06 role is superseded by D-017 (`excluded_invalid`).
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
Status: Superseded by D-017 (User03/User06 part; the provisional primary cohort is restated in D-017)
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

## D-014 — Remove repeated upload-chunk copies when building the canonical interim dataset
Date: 2026-09-12
Status: **Proposed** (not accepted; to be decided together with OPEN-06/08/09 at P0 exit)
Context: Adjacent raw files repeat upload chunks, and one chunk is repeated inside a file. A decision is needed
before the canonical interim dataset can be built (OPEN-07).
Decision (proposed):
- Within one subject + device group, keep one copy of each row that belongs to a repeated block: exact duplicates
  (timestamp, P1–P6, temp, humid, event) that occur in another file, and the 600-row block repeated inside
  `sm22482_0816`. Keep provenance of all copies (file, line) in the interim manifest.
- Do **not** remove or merge same-second rows with different values, adjacent identical same-second rows, or rows
  differing only in event text. These stay open.
- Never de-duplicate across devices or subjects.
Evidence: `docs/P0_A5_DUPLICATE_OVERLAP_REPORT.md`. Every primary-group file overlap is an exact duplicate block;
all 300 repeated chunk keys have identical content; 0 between-file value conflicts. Impact: 187,190 + 600 rows
(4.3 %) of 4,323,873 primary-group rows.
Consequence: If accepted, no information is lost (copies are identical). Same-second conflicts (10,997), their
alignment and resampling remain for P2. Minute-resolution legacy sources are out of scope of this proposal.

## D-015 — Candidate session boundary: gap > 30 min, with lost upload chunks bridged
Date: 2026-09-12
Status: **Proposed** (not accepted; decide at P0 exit together with D-014, after provider input on upload mechanics)
Context: Sessions cannot be files or calendar days (A5, A7). A rule is needed to group each per-device timeline
into recording sessions without altering data. The rule must not depend on any model result; none exists yet.
Decision (proposed):
- Build sessions per subject + device on the de-duplicated timeline (D-014 view).
- A new session starts after a gap > 30 min.
- A gap of exactly 1–3 upload chunks (n × 1,800 s ± 10 s, n ≤ 3) is recorded as a missing interval inside the
  session, not as a break.
- Session membership is a label only. No timestamp, row or gap is changed.
- Within-session gaps (≈ 2-min pauses, 6–15 s sample losses, bridged missing chunks) must be handled explicitly
  by the windowing rule (P2).
Evidence: `docs/P0_A7_TEMPORAL_GAP_REPORT.md`.
- 5–90 min is a plateau for User01/22480/User07.
- The ≈ 2-min pauses rule out thresholds < 5 min.
- 13/13 chunk-aligned 22482 gaps sit at file cuts with recording continuing on both sides in most cases.
- Resulting sessions per night: 1.04 / 1.04 / 1.16 / 1.02.
- The exact value is insensitive within ±15 min (≤ 5 sessions change per timeline).
Consequence: If accepted, 22482 nights stay whole across export losses (58 instead of 71 sessions). Genuine
non-aligned interruptions > 30 min remain breaks. Isolated single-chunk recordings, the split grouping level
(session vs night) and windowing across within-session gaps stay open for P2.

## D-016 — Flag known target sentinel and glitch patterns as invalid targets (values kept)
Date: 2026-09-13
Status: **Proposed** (not accepted; decide at P0 exit with D-014/D-015)
Context: Temperature and humidity are the regression targets. A8 found a small set of values that cannot be
physical readings of an indoor sleeping microclimate, with clear, repeated patterns.
Decision (proposed):
- In the canonical interim dataset, mark the target as invalid, per channel, with a cause-preserving state:
  - the joint zero pattern T = 0 and H = 0 (`target_zero_sentinel`), in both channels;
  - values outside the candidate plausibility band (T < −10 or > 60 °C; H > 100 %RH), together with a zero in the
    other channel of the same row (`target_extreme_glitch`). Currently only the 22482 night 2026-08-08/09.
- Raw values are never replaced, clipped, interpolated or deleted. Rows keep their provenance and their
  pressure data.
- Also stored as context, not as validity: zero-run class (start sentinel / dropout run), chunk position,
  |Δ| to the previous valid value with its Δt, constant-run length, and same-second group id
  (`quality_flag_schema.csv`).
Evidence: `docs/P0_A8_TARGET_QUALITY_REPORT.md` §3–§7.
- 4,132 rows (0.10 %) of the primary groups; no other value lies outside the band.
- The patterns are exact and repeated.
- Their neighbours show normal readings.
Consequence: If accepted, models and metrics exclude flagged targets in a traceable way.
Not covered by this proposal:
- excluding whole dropout/glitch episodes;
- jump or outlier thresholds;
- treatment of the ±1 same-second pairs;
- interpolation, clipping or smoothing (P2).
The candidate band is a descriptive parameter and must not be tightened after model results are seen.

## D-017 — User06 source excluded as invalid (provider-confirmed); User03 kept as auxiliary
Date: 2026-09-13
Status: Accepted (supersedes D-013)
Context: A1 showed that `user03_legacy` is, row for row, a contiguous excerpt of the `user06_auxiliary`
recordings (100 % of User03 rows at minute resolution and of its value sequences). D-013 kept User03 ≠ User06
and provisionally quarantined the overlapping recording. The data provider has since confirmed that the User06
data are wrong because of a setting problem at the time, and that the User06 source should be left out.
Decision:
- User03 and User06 remain two distinct subjects. They are not merged.
- The current `user06_auxiliary` source is classified `excluded_invalid` (`quality_status: invalid`,
  `exclusion_reason: provider_confirmed_setting_issue`, `configs/subject_mapping.yaml`).
- The User06 source is excluded from every downstream analysis, from model training and evaluation, and from
  any canonical or public analysis dataset. Excluded sources are listed, with reason and decision ID, in the
  future release manifest (P7).
- The raw archive is **not** modified or deleted. Analytical exclusion, never physical deletion.
- `user03_legacy` keeps its `auxiliary` role, with its existing limitations (minute resolution; auxiliary use needs
  its own decision, OPEN-13).
- Historical audit results (inventory, A1–A8) are not rewritten. They document the data as delivered. Analyses
  from A9 onward apply this exclusion.
Evidence: `docs/P0_A1_PROVENANCE_REPORT.md` §4; provider confirmation relayed by the PI on 2026-09-13.
Consequence:
- Provisional primary cohort unchanged: User01, User02, User07.
- User03 legacy: auxiliary. User06 current source: `excluded_invalid`. User06 has no valid source (cohort
  `no_valid_source`).
- OPEN-01 is closed.
- The committed raw manifest now carries `dataset_role = excluded_invalid` for the 11 User06 files; only those
  11 cells changed, checksums are unchanged. Re-running historical audit scripts reproduces their numbers; only
  role labels of User06 rows differ. Verified on 2026-09-13 by re-running A1, A2, A5, A7 and A8 against saved
  outputs: every value is identical except 27 role cells in A1 `cross_subject_provenance_by_source.csv` and 1 in
  A5 `duplicate_summary.csv` (User06 `auxiliary` → `excluded_invalid`).
- Caveat for any future use of User03 legacy: its rows are the same measurements as part of the invalid User06
  recording. D-017 attributes them to User03, but the provider has not said whether the setting problem also
  affects them. This must be addressed before User03 legacy is used (OPEN-13).

## D-018 — Pressure input-validity rule: raw layout and encoding only (values kept)
Date: 2026-09-13
Status: **Proposed** (not accepted; decide at P0 exit with D-014/D-015/D-016)
Context: P1–P6 are the model inputs. A9 checked channel presence, layout, encoding, zeros, the 4095 ceiling,
constant runs and scale on the analysis-eligible sources.
Decision (proposed):
- In the canonical interim dataset, a row's pressure input is **invalid** only if:
  - the raw line layout is not a recognised six-channel layout (`pressure_schema = nonstandard`), or fewer
    than six channels are present (`pressure_channels_present < 6`); absent channels are never filled with 0;
  - or any channel is < 0, > 4095 or non-integer (`pressure_impossible_encoding`).
- 4095 is kept as a value and flagged with the number of channels at 4095. It is not treated as missing,
  capped or excluded.
- All-zero frames, constant-run length, same-second group and the provider period label (e.g. User01 before/after
  2026-01-25) are stored as context columns. They are not validity flags.
- Raw values are never replaced, clipped, normalised, imputed or deleted. Channels are not removed.
Evidence: `docs/P0_A9_PRESSURE_QUALITY_REPORT.md` §2, §6–§8.
- The rule changes 0 rows of the current data (policies A and B). It guards the canonical builder against layout
  and encoding errors.
- A stuck heuristic (policy C) would flag 7,129 User01 rows. All of them are 4095 plateaus of the old sensor,
  not frozen hardware, so a heuristic is not proposed.
Consequence: If accepted, pressure validity is decided by raw evidence only. Not covered by this proposal (P2,
fitted on training data only where applicable):
- saturation handling;
- scaling/normalisation (OPEN-17);
- the User01 sensor-change boundary (OPEN-11);
- the 22482 P1 shift (OPEN-19);
- channel selection or spatial features (OPEN-20).

## D-019 — User01 `sensor_phase` provenance label (boundary 2026-01-25)
Date: 2026-09-13
Status: Accepted (provenance label only; handling open, OPEN-11)
Context: The provider documents a pressure-sensor replacement for User01 on 2026-01-25. A10 tested this boundary
against the data without assuming it (`docs/P0_A10_USER01_SENSOR_PHASE_REPORT.md`).
Decision:
- The canonical interim dataset carries a provenance column `sensor_phase`.
- For User01:
  - `s1` = rows up to 2026-01-25 08:07:26, the last row before the recording gap;
  - `s2` = rows from 2026-01-25 17:31:21, the first row after it.
  - No row lies in between.
- All other subject/device timelines are `s1` (no documented sensor change). Changing that needs its own decision
  (e.g. OPEN-19).
- The label changes no value. It implies no normalisation, clipping, rescaling, exclusion or phase-specific model.
- The boundary is fixed now, before any model exists. It must not be moved in response to model results.
- `s1/s2` are distinct from the provider's `phase_a/b/c` source folders. `s1` spans phase_a, phase_b and phase_c
  up to the gap.
Evidence: A10 §2–§8.
- The boundary is a single recording gap on the documented date. The file after it is the provider's
  "sensor changed" file.
- It is the strongest change point of the User01 series. The core consensus ranks it first for nights and
  sessions at w = 3 and 7, with a large margin.
- Nights ±14: the 4095 share, pressure-sum p95 and active channels are completely separated (Cliff's δ = ±1).
  Placebo windows show no separation.
- It is a step rather than a drift (one-step R² 0.79–0.99 vs line 0.59–0.76).
- 4095 disappears immediately: 22.1 % of rows before, 18 isolated cells after, the first 50 h later.
- Duration, clock time, temperature, humidity, sampling and a scale-free movement proxy are continuous across the
  gap.
Consequence:
- Later phases can report, stratify or constrain by `sensor_phase` without redefining it.
- Decided in P2 (OPEN-11, OPEN-17):
  - phase-aware preprocessing or scaling;
  - whether User01 adaptation/test spans may cross the boundary;
  - per-phase reporting in LOSO.
- Other acquisition changes inside `s1` (2025-12-17 log-format/activity change, the early-January sampling
  episode) are not part of this label (OPEN-21).
