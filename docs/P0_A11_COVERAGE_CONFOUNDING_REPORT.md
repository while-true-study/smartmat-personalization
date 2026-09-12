# P0-A11 — Subject / Device / Temporal Coverage & Confounding Audit

| | |
|---|---|
| Phase / analysis | P0 — Dataset Audit & Data Freeze / A11 (`docs/P0_DATASET_AUDIT_PLAN.md`) |
| Date | 2026-09-13 |
| Code | `src/data/coverage.py` (analysis), `scripts/audit_dataset_coverage.py`; reuses the A5 audit view, the A8 target states, the D-018 validity masks (A9), `sensor_phase_spec` (D-019, `configs/subject_mapping.yaml`) and `assign_phase` (A10) |
| Tests | `tests/test_coverage.py` (synthetic timestamps and manifest rows only) |
| Command | `python scripts/audit_dataset_coverage.py` (≈ 1 min) |
| Artifacts | `outputs/qa/p0/coverage/` — `canonical_coverage.csv`, `monthly_subject_coverage.csv`, `monthly_active_hours_matrix.csv`, `subject_temporal_overlap.csv`, `device_subject_matrix.csv`, `confounding_matrix.csv`, `primary_cohort_eligibility.csv`, `schema_firmware_events.csv`, `figures/coverage_timeline.png`, `coverage_run_meta.json` (regenerable, not committed) |

Descriptive only. No canonical dataset, split, window or model was created, and nothing was removed.

**Definitions.**
- Active recording hours = clock minutes with at least one row, divided by 60. This works the same for 3 s logs,
  minute-resolution legacy rows and unions of two concurrent mats.
- Audit-valid row: in the audit view (identical upload-chunk copies excluded), with a valid pressure frame
  (D-018) and both targets valid (A8/D-016). These rules are applied in memory; D-016 and D-018 are still proposals.
- Usable day: at least 60 audit-valid minutes.
- Missing metadata is written as `unknown` and never inferred.

## 1. Dataset coverage

Sources (`canonical_coverage.csv`). Analysis-eligible sources were read; excluded ones are listed with their
status but were not loaded.

| Subject | Source | Role | Device | Sensor phase | Raw rows | Audit-view rows | Dates |
|---|---|---|---|---|---|---|---|
| User01 | user01_phase_a | primary_candidate | unknown | s1 | 56,244 | 56,244 | 2025-08-25 → 09-01 |
| User01 | user01_phase_b | primary_candidate | unknown | s1 | 792,627 | 783,435 | 2025-11-05 → 2026-01-01 |
| User01 | user01_phase_c | primary_candidate | unknown | s1 / s2 | 381,211 / 1,018,738 | 359,013 / 953,512 | 2026-01-01 → 01-25 / 01-25 → 04-02 |
| User02 | user02_mat_22480 | primary_candidate | 22480 | s1 | 431,471 | 398,464 | 2026-07-19 → 09-05 |
| User02 | user02_mat_22482 | primary_candidate | 22482 | s1 | 635,126 | 594,316 | 2026-07-19 → 09-11 |
| User07 | user07 | primary_candidate | unknown | s1 | 1,008,456 | 991,075 | 2026-04-03 → 07-19 |
| User02 | user02_legacy_csv | auxiliary | unknown | s1 | 71,370 | 71,370 | 2025-10-05 → 10-13 (minute resolution) |
| User03 | user03_legacy | auxiliary | unknown | s1 | 107,256 | 107,256 | 2025-10-06 → 10-13 (minute resolution) |
| User06 | user06_auxiliary | **excluded_invalid** (D-017) | unknown | not analysed | — | — | — |
| User02 | user02_mat_22480_prefix_mismatch | **quarantined** (D-006) | unresolved | not analysed | — | — | — |
| User01 | user01_metadata | restricted_metadata (D-008) | not applicable | not analysed | — | — | — |

The auxiliary pool in the configuration has two sources, User02 legacy and User03 legacy (OPEN-13). User02 legacy
is auxiliary data of the primary subject User02, not another subject.

Domains (subject, sensor phase, mat):

| Domain | First → last row | Recording / usable days | Nights | Active hours | Audit-valid rows | T / H coverage | Dominant step |
|---|---|---|---|---|---|---|---|
| **User01** | 2025-08-25 22:21 → 2026-04-02 06:40 | 157 / 157 | 151 | 1,784.4 | 2,149,792 of 2,152,204 | 99.89 % | 3 s (2 s in phase_a) |
| User01/s1 | → 2026-01-25 08:07 | 90 / 90 | 86 | 988.0 | 1,196,357 | 99.81 % | 2 s / 3 s / 2 s episode |
| User01/s2 | 2026-01-25 17:31 → | 68 / 68 | 65 | 796.4 | 953,435 | 99.99 % | 3 s |
| **User02** (both mats) | 2026-07-19 19:41 → 2026-09-11 06:20 | 54 / 53 | 51 | 576.0 | 991,206 of 992,780 | 99.84 % | 3 s |
| User02/22480 | 2026-07-19 → 09-05 | 48 / 47 | 45 | 332.8 | 398,406 | 99.99 % | 3 s |
| User02/22482 | 2026-07-19 → 09-11 | 52 / 52 | 50 | 496.6 | 592,800 | 99.75 % | 3 s |
| **User07** | 2026-04-03 19:00 → 2026-07-19 05:11 | 107 / 106 | 100 | 832.8 | 990,929 of 991,075 | 99.99 % | 3 s |
| User02 legacy (aux) | 2025-10-05 → 10-13 | 8 / 7 | 7 | 50.3 | 71,370 | 100 % | minute |
| User03 legacy (aux) | 2025-10-06 → 10-13 | 8 / 8 | 7 | 85.1 | 107,236 | 99.98 % | minute |

Active hours per month (`monthly_active_hours_matrix.csv`; recording days and valid-target rows in
`monthly_subject_coverage.csv`):

| | 25-08 | 25-09 | 25-10 | 25-11 | 25-12 | 26-01 | 26-02 | 26-03 | 26-04 | 26-05 | 26-06 | 26-07 | 26-08 | 26-09 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| User01 | 30 | 2 | · | 294 | 376 | 367 (s1 287, s2 80) | 328 | 370 | 18 | · | · | · | · | · |
| User07 | · | · | · | · | · | · | · | · | 247 | 226 | 212 | 148 | · | · |
| User02 | · | · | · | · | · | · | · | · | · | · | · | 99 | 362 | 114 |
| aux (U02 / U03 legacy) | · | · | 50 / 85 | · | · | · | · | · | · | · | · | · | · | · |

QA figure `figures/coverage_timeline.png` shows recorded days per subject, mat and sensor phase, with seasons,
schema and sampling boundaries, the D-019 line and the 22482 anomaly marker.

## 2. Temporal overlap

Overlap is counted on days and minutes that were actually recorded, not on intersecting date ranges
(`subject_temporal_overlap.csv`):

| Pair | Shared recorded days | Shared ISO weeks | Shared months | Shared recording hours | Gap between the two |
|---|---|---|---|---|---|
| User01 ↔ User02 | 0 | 0 | 0 | 0 | 108.5 days |
| User01 ↔ User07 | 0 | 1 (2026-W14) | 1 (2026-04) | 0 | 36.3 h hand-over (04-02 06:40 → 04-03 19:00) |
| User02 ↔ User07 | 1 (2026-07-19) | 1 (2026-W29) | 1 (2026-07) | 0 | 14.5 h hand-over (07-19 05:11 → 19:41) |
| User02/22480 ↔ User02/22482 | 46 | 8 | 3 | 253.4 | — (2 days only 22480, 6 only 22482) |
| User02 legacy ↔ User03 legacy (aux) | 7 | 2 | 1 | 37.6 | — |

- **No two primary subjects were ever recorded at the same time.**
  - They follow one another: User01, then User07, then User02, with hand-overs of 36 h and 14.5 h.
  - The only shared "day" (2026-07-19) is User07's last morning and User02's first evening.
  - The only shared months are the two hand-over months.
- A held-out subject is therefore always also a held-out period.

## 3. Device and domain coverage

**Device evidence** (`device_subject_matrix.csv`, collected while parsing):

| Source | Configured device | Filename | JSON root key | Device column in rows |
|---|---|---|---|---|
| User01 phase_a/b/c | unknown | none | none | none |
| User07 | unknown | none | none | none |
| User02 legacy, User03 legacy | unknown | none | none | none |
| User02 mat 22480 | 22480 | 45 files | 45 files | 47,406 rows (from 2026-08-29) |
| User02 mat 22482 | 22482 | 49 files | 49 files | 129,027 rows (from 2026-08-31) |

- A hardware ID is recorded only for the two User02 mats, and each maps to User02 only.
- **Whether a physical mat was reused across User01, User07 and User02 cannot be checked with the current
  metadata (OPEN-04 stays unresolved).**
  - The hand-over gaps (36 h, 14.5 h) are consistent with a mat moving between participants, but they are not
    evidence.
  - No ID was invented for sources without one.

**User01 sensor phases.**

| | s1 | s2 |
|---|---|---|
| Rows / nights / active h | 1,198,692 / 86 / 988.0 | 953,512 / 65 / 796.4 |
| Months | 2025-08…09, 11…12, 2026-01 (287 h) | 2026-01 (80 h), 02, 03, 04 (18 h) |
| Seasons | summer 30 h, autumn 296 h, winter 663 h | winter 408 h, spring 388 h |
| Sampling | 2 s (phase_a), 3 s, 2 s 2026-01-03…07 | 3 s |
| Log container | plain → compressed quasi-JSON (night of 2025-12-17); plain again 2026-01-07 | quasi-JSON |
| T/H coverage | 99.81 % | 99.99 % |

- Each phase has more than 60 nights, so User01 overall, User01/s1 and User01/s2 can each be reported as a domain
  slice.
- s1 is internally heterogeneous (OPEN-21). s2 alone is the cleaner slice.
- A phase is not a subject.

**User02 mats.**

| | 22480 | 22482 |
|---|---|---|
| Recorded dates | 48 (07-19 → 09-05) | 52 (07-19 → 09-11) |
| Active hours | 332.8 | 496.6 |
| Shared dates / concurrent hours | 46 / 253.4 | 46 / 253.4 |
| Exclusive dates | 2 | 6 |
| Schema transition (device column) | 2026-08-29, between files | 2026-08-31, inside `sm22482_0831` |
| Known issue | — | P1 anomaly from 2026-08-20 (OPEN-19) |

Subject-level evaluation keeps both mats under User02. Which mat or mats feed a model is not decided here.

**22482 P1 anomaly (A9) in coverage terms.**
- 22482 recorded 202.0 h in 22 nights from 2026-08-20. That is 41 % of its hours; 64.9 h of them are also
  covered by 22480.
- Without that slice, User02 still has 438.8 h in 45 nights, well above every structural threshold (§4).
- **It is not a blocking issue for the cohort. It is a device-period quality issue:** the canonical dataset must
  be able to flag it before P0 closes.
- Its start time and affected channels need a provider answer. Failing that, a short characterisation audit
  (A9b, below).
- *Update 2026-09-13 (A9b, D-022):*
  - The shift is P1-only, abrupt and persistent. It is fully present from 2026-08-20 21:37:33, after a transition
    recording on the night 2026-08-19.
  - It is flagged by `channel_quality_phase` / `channel_quality_flag`. With the A9b boundary the shifted slice is
    192.0 h in 21 nights; User02 without it keeps 447.7 h in 45 nights. OPEN-19 is closed as class B.
  - The P6 decline is a separate change from 2026-08-25 (OPEN-03).
  - The event row below (status `unresolved_anomaly`) is kept as A11 recorded it.

**Timeline events** (`schema_firmware_events.csv`). Each status stays separate:

| Date | Domain | Status | Event | Provenance field |
|---|---|---|---|---|
| 2025-11-05 | User01 | observed_sampling_regime_change | 2 s → 3 s, after a 2-month gap | sampling_regime |
| 2025-11-18 | User01 | documented_metadata_event | heating-season start (year inferred, OPEN-14) | — |
| 2025-12-17 | User01 | observed_distribution_shift | active channels 1.51 → 2.49 (OPEN-21) | — (cause open) |
| 2025-12-17/18 | User01 | observed_schema_boundary | log container plain → quasi-JSON | log_container |
| 2025-12-25 | User01 | observed_distribution_shift | pressure-sum level +49 % | — (cause open) |
| 2025-12-28 | User01 | target_quality_episode | T/H dropout runs (A8) | target flag |
| 2026-01-03 / 01-07 / 01-08 | User01 | observed_sampling_regime_change / observed_schema_boundary | 2 s episode; plain lines on 01-07; back to 3 s and quasi-JSON | sampling_regime, log_container |
| **2026-01-25** | User01 | **confirmed_metadata_boundary** | sensor replacement, s1 → s2 (D-019) | sensor_phase |
| 2026-08-08 | 22482 | target_quality_episode | T/H zeros and glitches (A8) | target flag |
| 2026-08-20 | 22482 | **unresolved_anomaly** | P1 nearly silent, P6 halves (OPEN-19) | — (cause open) |
| 2026-08-29 / 08-31 | 22480 / 22482 | observed_schema_boundary | device_id column added | pressure_schema |

Boundaries that can be carried as provenance fields now:
- `sensor_phase` (confirmed);
- `pressure_schema` and `log_container` (observed in the raw layout);
- `sampling_regime` (observed per day).

Distribution shifts and anomalies stay labels of open questions until decided.

## 4. Primary cohort eligibility

Structural checks only, no model (`primary_cohort_eligibility.csv`). Thresholds are descriptive: at least 100
active hours and 20 nights; T/H coverage of at least 95 %; no shared recording hours with another primary
subject; at least 15 nights, so that 7 adaptation nights, a buffer and 7 test nights fit.

| Check | User01 | User02 | User07 |
|---|---|---|---|
| Recording volume | pass (1,784 h, 151 nights) | pass (576 h, 51 nights) | pass (833 h, 100 nights) |
| Target coverage | pass (99.89 %) | pass (99.84 %) | pass (99.99 %) |
| Provenance resolved (rows belong to one subject; A1) | pass | pass | pass |
| Separable without subject leakage (shared hours) | pass (0 h) | pass (0 h) | pass (0 h) |
| Future chronological data | pass | pass | pass |
| Personalization length | pass (s1 86 / s2 65 nights) | pass (51 nights; 45 without the 22482 anomaly slice) | pass |
| **Status** | **eligible_with_caveat** | **eligible_with_caveat** | **eligible_with_caveat** |

Caveats:
- **User01:**
  - two sensor phases (D-019, OPEN-11);
  - acquisition changes inside s1 (OPEN-21);
  - device unknown (OPEN-04);
  - the only primary subject recorded in winter.
- **User02:**
  - two concurrent mats, with setup and use policy open (OPEN-03);
  - 22482 P1 anomaly (OPEN-19);
  - 2 quarantined files (OPEN-02);
  - the shortest span (53 days).
- **User07:** device unknown (OPEN-04).

No subject is not eligible. No subject was added to make the cohort larger. Proposed: **D-020 (Accepted), canonical
P0 primary cohort = User01, User02, User07.**

## 5. Confounding structure

| | User01 | User07 | User02 |
|---|---|---|---|
| Calendar period | 2025-08 → 2026-04 | 2026-04 → 2026-07 | 2026-07 → 2026-09 |
| Seasons (active hours) | winter 1,071 · spring 388 · autumn 296 · summer 30 | spring 473 · summer 360 | summer 461 · autumn 114 |
| Device ID | unknown | unknown | 22480 + 22482 |
| Sensor phase | s1, s2 | s1 | s1 |
| Pressure schema / log container | 6 channels; plain → quasi-JSON | 6 channels; quasi-JSON | 6 channels → + device column; quasi-JSON |
| Sampling | 2 s, 3 s, 2 s episode | 3 s | 3 s |
| Pressure scale (A9) | high; 4095 accumulation in s1 | lower | lower |

- **Winter is observed only in User01:** 1,071 h, 60 % of its hours.
  - User07 has no season of its own (100 % of its hours fall in seasons another subject also covers).
  - User02 has no season of its own by season of year; its autumn 2026 is shared with no one.
- Share of each subject's hours in months where another primary subject was also recorded: User01 1 %, User02 17 %,
  User07 47 %. These are only the hand-over months, with no shared day or hour.
- Each leave-one-subject-out fold therefore removes a person together with a calendar period, a season mix, a
  firmware/logging state and (probably) a mat configuration.
- A difference between folds cannot be attributed to the person alone. It must be read as user + season/time +
  device/domain shift. Within-subject chronological evaluation is the only place where the person is held
  constant, and User01's sensor change still has to be separated there (D-019).

## 6. Allowed research claims

**Supported,** framed as "held-out subject = held-out subject-period-device domain":
- Generalisation to an unseen subject under a realistic temporal, seasonal and device/domain shift, with n = 3
  folds, each reported with its domain descriptors.
- Within-subject chronological personalization. For User01 it is reported per `sensor_phase`, or spans are kept
  within a phase.
- Descriptive evidence that a hardware change (User01 s1 → s2) shifts the pressure inputs, as a documented
  domain-shift case.

**Not supported:**
- Generalisation across a diverse population (3 subjects; auxiliary data are minute-resolution fragments).
- Isolation of a pure user-specific (physiological or behavioural) effect from season, time and device.
- Seasonal robustness, since winter comes from one subject only.
- Device invariance or cross-device generalisation (no hardware ID for 2 of 3 subjects; mat reuse unknown).
- Statistical significance of between-subject differences with 3 folds.

## 7. Remaining uncertainties

1. **OPEN-04:** mat identity and possible reuse for User01 and User07. Answerable only by the provider.
2. ~~**OPEN-19:** cause and exact start of the 22482 P1 anomaly.~~ Resolved for P0 by A9b and D-022 (flagged,
   class B, non-blocking). Only the physical cause remains a provider question.
3. **OPEN-03:** physical setup of the two User02 mats. The interim dataset can keep both as device streams; the use
   policy is P2.
4. **OPEN-21:** the acquisition changes inside User01 s1.
5. **OPEN-14:** metadata dates (heating start). Heating state is not observable in the data, so it cannot be
   placed on the timeline reliably.
6. The auxiliary sources cover 8 days in October 2025. User03 legacy is valid User03 data (D-021); whether auxiliary
   data are used is OPEN-13.
