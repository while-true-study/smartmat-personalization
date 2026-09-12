# P0 — Dataset Audit & Data Freeze: Final Report

| | |
|---|---|
| Phase | P0 (`docs/RESEARCH_PROTOCOL.md` §5), branch `research/p0-data-freeze` |
| Closed | 2026-09-13 (closure gate: `docs/P0_DATASET_AUDIT_PLAN.md`; merge and tag `p0-data-freeze` pending PI review) |
| Frozen dataset | canonical_v1: `data/interim/canonical_v1/` (local); manifests `data/interim/manifest/canonical_v1_*` (committed) |
| Content hashes | primary `26b970a4edce2bd5…`, auxiliary `a0457edabbd9c1d4…`, duplicate provenance `b39ed4d2fe73aa8f…`; config `a5c09e425f09…`; raw manifest `f5a27acc59cc…` |
| Detail | analysis reports `docs/P0_A1…A11_*.md`, `docs/P0_A9B_*.md`; decisions `docs/DECISIONS.md` |

This report summarises conclusions only. The numbers come from the analysis reports and the canonical_v1 build.
Historical audit results are not rewritten to match the final policies.

## 1. Purpose of P0

- Understand the delivered raw data.
- Settle provenance, subject/device identity and data quality.
- Fix the cohort.
- Freeze every data-level policy that does not depend on a model.
- Build one reproducible canonical interim dataset that all later phases read instead of raw.

No model, window, split, resampling or normalisation was produced in P0.

## 2. Dataset inventory

- 377 delivered files: 373 sensor logs, 2 restricted participant-metadata workbooks, the provider's README and
  manifest.
- 4,688,889 parsable sensor rows.
- Five subject IDs (User01, User02, User03, User06, User07). Device IDs are recorded only for User02's two mats
  (22480, 22482).
- Four raw format families:
  - plain full timestamps;
  - plain `MM-DD` rows;
  - quasi-JSON upload chunks;
  - legacy minute-resolution CSV.
- Current logs sample every 3 s; User01's first phase samples every 2 s.
- Raw files are read-only and checked against a committed SHA-256 manifest before every run. They were never
  modified (`docs/initial_dataset_inventory.md`).

## 3. Canonical cohort

| Role | Sources | Canonical use | Decision |
|---|---|---|---|
| **Primary** | User01 (phase_a/b/c), User02 mats 22480 and 22482 (one subject, two device streams), User07 | the only rows for primary LOSO, personalization and metrics | D-020, D-023, D-027 |
| **Auxiliary** | User02 legacy CSV, User03 legacy CSV (valid; minute resolution) | kept apart in `auxiliary.parquet`; secondary/sensitivity protocols only | D-021, D-023 |
| **Excluded (invalid)** | User06 source | not in canonical_v1; raw kept | D-017 |
| **Quarantined** | 2 prefix-mismatch files (device unresolved; 22482 indicated) | not in canonical_v1 | D-006, D-023 |
| **Restricted** | User01 participant metadata | never data | D-008 |

## 4. Main data-quality findings

| Analysis | Finding | Handling |
|---|---|---|
| A1 provenance | User03 legacy rows were contained in the User06 recording. No other pair of subjects shares any row. The provider confirmed that the User06 data were wrong; User03 is valid. | User06 excluded; User03 auxiliary |
| A2 User02 mats | 22480 and 22482 record concurrently (253 h) but are uncoupled, with a persistent T/H offset. | separate device streams, one subject |
| A5 duplicates | Adjacent exports repeat whole upload chunks, always exactly. That is 187,814 copy rows (4.3 %) in primary. 11,249 same-second groups remain as separate observations, most of
them with differing readings. | exact copies removed; same-second rows kept |
| A7 time | 3 s sampling; gaps are either short or > 2 h. On 22482, 1–3 upload chunks are lost at morning file cuts. | sessions at gaps > 30 min, 22482 chunk gaps bridged and flagged |
| A8 targets | 0.10 % invalid targets: joint-zero sentinels plus one 22482 glitch night. No abrupt jumps. | flags, values kept |
| A9 pressure | Six complete channels everywhere, no impossible value, no stuck channel. 4095 accumulates only in User01 before its sensor change. | structural validity; 4095 flagged, kept |
| A9b 22482 | P1 response collapses from 2026-08-20 (P1-only, abrupt, persistent). A later P6/load shift after 08-25 looks like load moving between the mats. | `channel_quality_phase` flag |
| A10 User01 | The sensor replacement on 2026-01-25 is the strongest change point: a step (4095 22 % → 0 %, pressure-sum p95 −51 %) while T/H and behaviour stay continuous. Other acquisition changes lie inside s1. | `sensor_phase` s1/s2 |
| A11 coverage | No two primary subjects were recorded at the same time. Winter is observed only in User01. Mat reuse cannot be checked. | claims limited (§9) |

## 5. Excluded and quarantined data

| Source | Files | Raw rows | Reason | In canonical_v1 |
|---|---|---|---|---|
| User06 (`user06_auxiliary`) | 11 | 164,185 | provider-confirmed setting issue (D-017) | no (raw kept) |
| prefix-mismatch (`user02_mat_22480_prefix_mismatch`) | 2 | 22,205 | device attribution unresolved (D-006) | no |
| User01 metadata | 2 | — | restricted participant data (D-008) | never |

Their rows are counted for reconciliation only; no value is kept.

## 6. Frozen, preprocessing-independent policies

| Policy | Rule | Decision |
|---|---|---|
| De-duplication | Remove only repeated upload/export copies (blocks ≥ 10 fully identical rows) within one subject + device stream. Never across devices or subjects; never same-second rows with different values; not for minute-resolution sources. Every raw occurrence stays traceable. | D-014 |
| Sessions | A new session starts after a gap > 30 min. A gap of n × 1,800 s ± 10 s (n ≤ 3) at a 22482 file boundary stays inside the session and is flagged. Session membership never licenses a window across a gap. | D-024 |
| Timestamps | Keep the raw string. Parsed values are naive local times with no timezone (`local_unspecified`). Resolution `second` or `minute`, with no invented seconds. The year is inferred only from deterministic source context, recorded in `timestamp_year_source`. | D-026 |
| Targets | Invalid if missing, 0 or outside −10…60 °C / 0…100 %RH. Cause flags: `zero_sentinel`, `extreme_glitch`, `zero_value`. Values are never changed; same-second ±1 observations are kept. | D-025 |
| Pressure | Valid = known 6-channel layout, all present, integers in 0…4095. 4095 stays valid and is counted. Missing channels are never filled. | D-018 |
| User01 sensor phase | `s1` ≤ 2026-01-25 08:07:26; `s2` ≥ 17:31:21; other timelines `not_applicable`. | D-019, D-028 |
| 22482 channel quality | `normal` ≤ 2026-08-19 08:56:10; `p1_transition` for the recording 2026-08-19 19:58:23 → 08-20 09:58:32; `p1_response_shift` ≥ 2026-08-20 21:37:33; flag `p1`. | D-022 |
| User02 devices | Two device streams of one subject. No merge, fusion or deletion. | D-027 |
| Auxiliary | Kept apart; not in primary LOSO, personalization or metrics. | D-023 |

## 7. Canonical v1

The row schema has 46 columns (D-028):
- identity and roles;
- raw and parsed timestamp with resolution, format, year source and timezone status;
- `sensor_phase`, `channel_quality_phase` and `channel_quality_flag`;
- `P1`–`P6`, temperature and humidity (raw integers);
- target and pressure validity with cause flags, the upper-bound count, all-zero and constant-frame context;
- redacted event text and log container;
- `session_id`, `gap_before_s` and `session_bridged_gap`;
- raw `source_file`, `source_row` and `chunk_key`;
- same-second group ID, size and order;
- `duplicate_group_id` and `duplicate_count`.

`duplicate_provenance.parquet` lists every raw occurrence of every de-duplicated row.

| Stream | Raw rows | Copies removed | Canonical rows | Sessions | Invalid targets | Rows with a 4095 channel |
|---|---|---|---|---|---|---|
| User01 | 2,248,820 | 96,616 | 2,152,204 (s1 1,198,692 · s2 953,512) | 157 | 2,412 | 264,427 |
| User02 / 22480 | 431,471 | 33,007 | 398,464 | 47 | 58 | 17 |
| User02 / 22482 | 635,126 | 40,810 | 594,316 (normal 347,707 · transition 16,804 · shift 229,805) | 58 (13 bridged gaps) | 1,516 | 0 |
| User07 | 1,008,456 | 17,381 | 991,075 | 102 | 146 | 0 |
| **Primary** | 4,323,873 | 187,814 | **4,136,059** | 364 | 4,132 | 264,444 |
| User02 legacy (aux) | 71,370 | 0 | 71,370 | 7 | 0 | 36,375 |
| User03 legacy (aux) | 107,256 | 0 | 107,256 | 7 | 20 | 25,932 |

- Pressure-invalid rows: 0 in every stream.
- **Reconciliation:** 4,688,889 raw sensor rows − 164,185 excluded − 22,205 quarantined − 178,626 auxiliary (kept
  apart) − 187,814 primary copies = 4,136,059 primary canonical rows. The build fails on any discrepancy, per
  stream, per slice and per file.
- **Reproducibility:** two consecutive builds gave identical content hashes, Parquet bytes and manifests.

## 8. Coverage and confounding

- The three primary subjects follow one another in time: User01 2025-08 → 2026-04, User07 2026-04 → 07, User02
  2026-07 → 09. There are 0 shared recording hours; hand-overs take 36 h and 14.5 h.
- Winter comes only from User01.
- User01 contains a hardware change (s1/s2).
- 22482 contains a P1 response shift.
- Hardware IDs exist only for User02, so mat reuse across subjects cannot be checked.
- Every LOSO fold therefore removes a person together with a period, a season mix and a device/firmware
  configuration. All three subjects are structurally eligible, with caveats (A11).

## 9. Allowed and unsupported claims

**Supported:**
- Generalisation to an unseen subject under realistic temporal, seasonal and device shift. Each fold is a held-out
  subject-period-device domain; n = 3.
- Within-subject chronological personalization, reported with User01's sensor phase and 22482's channel-quality
  phase.
- The User01 sensor change as a documented domain-shift case.

**Unsupported:**
- Population-level generalisation.
- A pure user-specific effect separated from season, time and device.
- Seasonal robustness.
- Device invariance.
- Statistical significance of between-subject differences with 3 folds.

## 10. Remaining limitations (non-blocking)

- OPEN-04: mat identity.
- OPEN-14: metadata dates.
- OPEN-20: channel layout.
- OPEN-21: other User01 acquisition changes inside s1.
- The cause of the 22482 P1 shift and the later 22482 load shift (OPEN-03): provider questions.
- Auxiliary data cover 8 days of minute-resolution recordings. A13 (legacy timestamp reliability) is needed only
  if a secondary protocol uses them.
- Absolute dates in public releases are OPEN-18 (P7).

## 11. Handoff to P1/P2

- P1 (domain-shift EDA) and P2 (protocol) read canonical_v1 only.
- P1 reports distributions by subject, device stream, sensor phase, channel-quality phase and season, including
  the remaining A12 parts (hour of day, heater episodes).
- P2 decides:
  - windowing and continuity across within-session gaps;
  - how User02's two streams are used;
  - handling of 4095, of User01 s1/s2 and of 22482 P1;
  - scaling fitted on training data only;
  - target-episode handling;
  - admissibility of movement labels;
  - the statistical plan for three folds.
- Any change to a P0 rule creates canonical_v2 through a new decision; canonical_v1 is never edited.
