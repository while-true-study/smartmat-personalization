# P0-A9 — Pressure Channel Quality & Consistency Audit

| | |
|---|---|
| Phase / analysis | P0 — Dataset Audit & Data Freeze / A9 (`docs/P0_DATASET_AUDIT_PLAN.md`) |
| Date | 2026-09-13 |
| Code | `src/data/pressure_quality.py` (analysis), `scripts/audit_pressure_quality.py`; reuses the A5 audit view (`upload_copy_mask`), A7 timelines and candidate sessions, A8 run helpers (`flagged_runs`, `constant_runs`, `session_ids`) |
| Tests | `tests/test_pressure_quality.py` (synthetic values and log text only) |
| Command | `python scripts/audit_pressure_quality.py` (≈ 1.5 min) |
| Artifacts | `outputs/qa/p0/pressure_quality/` — `pressure_channel_summary.csv`, `pressure_boundary_summary.csv`, `constant_run_summary.csv`, `constant_channel_runs.csv`, `frame_constant_runs.csv`, `pressure_cross_channel.csv`, `pressure_distribution_by_period.csv`, `pressure_delta_summary.csv`, `pressure_schema_summary.csv`, `pressure_schema_by_source.csv`, `pressure_policy_impact.csv`, `pressure_group_summary.csv`, `pressure_flag_schema.csv`, `excluded_sources.csv`, `pressure_quality_run_meta.json` (regenerable, not committed) |

Evidence only. No pressure value was clipped, normalised, imputed, resampled or deleted, and no channel or row
was removed. Absent channels would stay absent (never read as 0). 4095 is reported as a *candidate* boundary
value of the 12-bit range, not as a confirmed saturation code. Candidate sessions (proposed D-015) are context
labels only.

**Cohort (D-017).** A9 is the first analysis that applies the User06 exclusion. It reads only analysis-eligible
sources (`analysis_source_ids()`: `primary_candidate` or `auxiliary`, and not `quality_status: invalid`). The
User06 source (`excluded_invalid`, provider-confirmed setting issue), the quarantined 22480 prefix-mismatch files
and the restricted metadata are not loaded; the script stops if a User06 group appears, and lists the excluded
sources with reason and decision in `excluded_sources.csv`. Main groups: User01, User02/22480, User02/22482,
User07. Reference only: the auxiliary legacy sources User02 legacy and User03 legacy (minute resolution; no
time-based runs or |Δ| statistics). Historical A1–A8 results are unchanged.

## 1. Purpose

The six pressure channels P1–P6 are the model inputs. Before P0 closes, A9 describes per channel, subject/device
and period: value ranges, zeros, values at the top of the 12-bit range, constant runs, cross-channel structure,
scale shifts and the raw schema, and asks which pressure input-quality rules could be frozen on raw evidence
(OPEN-17, OPEN-11).

## 2. Channel coverage

Timeline = A5/A7 audit view (identical upload-chunk copies excluded; nothing else).

| | User01 | 22480 | 22482 | User07 |
|---|---|---|---|---|
| Rows | 2,152,204 | 398,464 | 594,316 | 991,075 |
| Candidate sessions / hours | 157 / 1,816.0 | 47 / 332.0 | 58 / 505.9 | 102 / 836.8 |
| Channels present per row | 6 in every row | 6 | 6 | 6 |
| Rows with a missing channel / non-standard layout | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Values < 0, > 4095 or non-integer | 0 | 0 | 0 | 0 |
| All-zero frames (all six = 0) | 3.95 % | 2.58 % | 7.13 % | 3.13 % |
| Rows with ≥ 1 channel at 4095 | 264,427 (12.3 %) | 17 | 0 | 0 |

Per channel (all rows; `pressure_channel_summary.csv`, which also has p01, mean, unique values and the share of
unchanged consecutive values, overall and per User01 phase). p01 is 0 in every channel of every group.

| Zero share | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|
| User01 | 73.0 % | 47.1 % | 31.7 % | 82.1 % | 51.1 % | 51.9 % |
| 22480 | 77.6 % | 38.6 % | 28.1 % | 82.6 % | 36.8 % | 34.5 % |
| 22482 | 65.3 % | 43.9 % | 54.1 % | 45.8 % | 44.7 % | 54.0 % |
| User07 | 79.5 % | 40.8 % | 27.6 % | 80.4 % | 33.5 % | 31.9 % |

| Median / p99 / max | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|
| User01 | 0 / 2,617 / 4,095 | 20 / 4,009 / 4,095 | 1,277 / 4,095 / 4,095 | 0 / 3,381 / 4,095 | 0 / 3,948 / 4,095 | 0 / 4,095 / 4,095 |
| 22480 | 0 / 827 / 3,021 | 136 / 1,831 / 4,095 | 489 / 1,945 / 2,793 | 0 / 505 / 3,104 | 101 / 1,951 / 3,491 | 141 / 1,634 / 2,906 |
| 22482 | 0 / 1,869 / 3,111 | 20 / 1,634 / 3,647 | 0 / 1,789 / 3,484 | 11 / 1,925 / 3,637 | 31 / 2,041 / 3,661 | 0 / 1,912 / 3,731 |
| User07 | 0 / 1,247 / 3,817 | 74 / 1,843 / 3,945 | 588 / 2,121 / 3,114 | 0 / 588 / 3,705 | 185 / 2,088 / 4,023 | 269 / 1,951 / 3,637 |

- Every channel of every group is populated and varies (1,501–4,061 distinct values per channel). No channel is
  dead or permanently constant.
- On User01, 22480 and User07, P1 and P4 are the least loaded channels (zero 73–83 %); P3 carries most load.
  22482 is loaded more evenly.
- Cross-channel structure (`pressure_cross_channel.csv`, loaded rows):

| | User01 | 22480 | 22482 | User07 |
|---|---|---|---|---|
| Pressure sum, median / p95 | 3,817 / 8,945 | 1,764 / 3,467 | 1,940 / 3,876 | 2,037 / 3,784 |
| Active channels, mean | 2.74 | 3.10 | 3.15 | 3.16 |
| Only one channel active | 20.7 % | 4.4 % | 12.6 % | 4.3 % |
| Dominant channel (largest value) | P3 45.8 % | P3 44.2 % | P5 29.8 % | P3 42.1 % |
| Mass share P1…P6 | .05 .22 .40 .03 .15 .16 | .02 .25 .35 .01 .18 .18 | .14 .17 .13 .19 .25 .13 | .02 .20 .34 .02 .20 .22 |
| corr P1–P4 / P2–P5 / P3–P6 | 0.07 / 0.15 / 0.19 | 0.02 / 0.32 / 0.44 | 0.45 / 0.59 / 0.43 | 0.05 / 0.23 / 0.41 |

  The highest positive correlations on the three current mats are the pairs P1–P4, P2–P5 and P3–P6; adjacent
  pairs (P2–P3, P5–P6) are negative. This is compatible with two rows of three sensors, but the physical layout
  is not documented (§9).

## 3. Zero and boundary values

**Zero.** The minimum of every channel is 0.
- All-zero frames are 2.6–7.1 % of rows.
- On the current mats single-channel zero runs are short: 22480 none ≥ 5 min (longest 267 s); 22482 and User07
  one run each just over 5 min.
- User01 has long zero runs on unloaded channels (up to 3.2 h, §4).
- 22482's longest is one all-zero hour: 2026-08-31 15:48–16:48, a daytime recording that ends the old-layout
  rows of `sm22482_0831` before the firmware switch at 20:56 (§6).

**4095 (candidate boundary).** `pressure_boundary_summary.csv`; runs = consecutive rows at 4095 within 6 s.

| Group | Channel | Cells | % of rows | Runs | Longest run | Sessions / dates |
|---|---|---|---|---|---|---|
| User01 | P1 | 2,659 | 0.12 | 180 | 187 rows (518 s) | 32 / 34 |
| User01 | P2 | 12,722 | 0.59 | 3,692 | 786 rows (1,589 s) | 89 / 90 |
| User01 | P3 | 214,415 | 9.96 | 25,466 | 783 rows (1,686 s) | 90 / 90 |
| User01 | P4 | 3,441 | 0.16 | 747 | 116 rows (336 s) | 67 / 70 |
| User01 | P5 | 8,656 | 0.40 | 2,207 | 138 rows (409 s) | 54 / 54 |
| User01 | P6 | 33,708 | 1.57 | 5,334 | 806 rows (2,356 s) | 83 / 81 |
| 22480 | P2 | 17 | 0.004 | 4 | 10 rows (29 s) | 1 / 1 |
| 22482, User07 | — | 0 | 0 | — | max 3,731 / 4,023 | — |

- On User01, 4095 is a pile-up at the ceiling rather than the end of a smooth tail. 275,601 cells are at 4095,
  789 cells at 4094 and 7,280 between 4090 and 4094. This is consistent with clipping at the top of the range.
  It is not asserted as saturation.
- 99.99 % of User01's 4095 cells lie before the 2026-01-25 sensor change (§5).
- In the other groups, each channel's maximum occurs exactly once. There is no second plateau.
- The most frequent interior value is 1 in every primary channel: 0.2–0.8 % of rows, runs of at most 4 rows. This
  is a noise floor, not a stuck code.
- Reference sources (minute resolution; runs chained across 60 s steps):
  - User02 legacy P5 is at 4095 in **50.8 %** of rows (36,242), with runs up to 2,639 rows (≈ 112 min) on 7 of
    8 dates.
  - User03 legacy P3, P4 and P5 are at 4095 in 7–10 % of rows.
  - These are quality caveats for the auxiliary pool (OPEN-13).

## 4. Constant and stuck patterns

Runs of identical consecutive values per channel (a gap > 60 s ends a run), classified by what the other channels
do (`constant_run_summary.csv`, `constant_channel_runs.csv`, `frame_constant_runs.csv`). Share = run hours /
candidate-session hours.

| Category (≥ 1 min / ≥ 5 min / ≥ 30 min / ≥ 1 h) | User01 | 22480 | 22482 | User07 |
|---|---|---|---|---|
| Zero, other channels active (unloaded channel) | P4: 9,635 / 1,951 / 20 / 3 runs; 566 h (31 %) at ≥ 1 min | P4: 2,336 / 0 / 0 / 0; 54 h (16 %) | P1: 3,897 / 1 / 0 / 0; 94 h (19 %) | P4: 3,341 / 0 / 0 / 0; 72 h (9 %) |
| Zero, all channels zero (empty-mat candidate) | 16–42 runs per channel, ≤ 1.1 h; 0–2 runs ≥ 5 min | none | 1 run of 59.9 min (all channels) | none |
| Non-zero, one channel constant while others change | P3: 2,174 / 263 / 1 / 0 (105 h, 5.8 %); P6: 290 / 28 / 2 / 0; P1, P2, P4, P5: 12–90 runs ≥ 1 min | **none** | **none** | **none** |
| Non-zero, whole frame identical (frame-freeze candidate) | 936 runs ≥ 1 min (29.1 h), 19 ≥ 5 min (3.6 h), 0 ≥ 30 min | **none** | **none** | **none** |

- **All non-zero constant runs are 4095 plateaus.** Every non-zero constant run ≥ 1 min in the four primary groups
  is on User01 at value 4095, in both non-zero categories. 928 of the 936 identical-frame runs contain a 4095
  channel, and their median frame has one active channel: one channel is at the ceiling while the others read 0.
- The three one-channel runs ≥ 30 min are all at 4095: P6 39.3 min (2025-11-05), P3 33.8 min (2025-11-13) and
  P6 30.1 min (2025-12-01).
- There is no constant run at an interior value and no frozen frame on 22480, 22482 or User07. A9 therefore
  finds no evidence of a stuck channel. The constant non-zero patterns are boundary plateaus of User01's sensor
  before the change.
- "Zero while others are active" is the normal state of an unloaded channel. It is not a fault. User01's runs
  of this kind are much longer (≥ 1 h runs exist) than on the other mats. The cause is not determined; A10 will
  compare it before/after the sensor change.
- All-channel zero is the only all-channel constant state outside User01's plateaus. Mixed states (some channels
  at 4095, others zero or changing) are the User01 pattern above.

**Consecutive differences** (`pressure_delta_summary.csv`, |Δ| between rows ≤ 5 s apart; descriptive, no outlier
rule):

| | User01 | 22480 | 22482 | User07 |
|---|---|---|---|---|
| Channel median |Δ| | 0–10 | 0–26 | 0–7 | 0–26 |
| Channel p99 |Δ| | 415–1,632 | 360–739 | 284–448 | 355–695 |
| Steps with |Δ| ≥ 3,000 (all channels) | 21,281 | 19 | 66 | 76 |
| Isolated in-and-out spikes (≥ 3,000 up and back) | 4,455 | 6 | 23 | 18 |
| Pressure sum: median / p99 / p99.9 / max |Δ| | 75 / 2,782 / 5,767 / 13,602 | 90 / 1,194 / 2,405 / 4,976 | 58 / 931 / 2,548 / 6,664 | 94 / 1,310 / 2,597 / 5,831 |

User01's large steps are 0 ↔ 4095 transitions of the old sensor. Elsewhere, near full-range steps are rare
(< 1 per 10,000 row steps). Same-second observations (A5) are kept as separate rows; nothing is averaged.

## 5. Scale and domain shifts

`pressure_distribution_by_period.csv` gives, per source/phase, month, ISO week and day: loaded share, pressure
sum median/p95, mean active channels, and per-channel p95, median when active, active share, mass share and 4095
count. Known provider events are marked in the week/day rows.

**User01 sensor change (baseline evidence for A10 only).** On 2026-01-25 the morning recording ends at 08:xx and
the next starts at 17:xx. Split at that daytime gap:

| | Before | After |
|---|---|---|
| Rows | 1,198,692 | 953,512 |
| Rows with ≥ 1 channel at 4095 | 264,409 (22.1 %) | **18** (0.002 %) |
| Pressure sum median / p95 (loaded rows) | 4,420 / 10,157 | 2,976 / 5,022 |
| Mean active channels | 2.07 | 3.55 |
| P3 p95 / median when active | 4,095 / 3,835 | 1,941 / 1,179 |
| Loaded share | 94.2 % | 98.4 % |

- The hourly counts of 4095 rows stay high until the last row of the morning recording. They are zero from the
  first evening row onward. The hardware change is visible as a step, not a drift. It coincides with the provider
  note.
- A10 has to quantify the step. It also has to check the other documented changes: the log-format change on
  2025-12-17 and the heating-season start. The User01 phases (a/b/c) differ mainly through this change (phase_c
  starts before it).

**User02/22482 P1 (new, not documented).**
- From the night of 2026-08-19/20, P1 nearly stops responding:
  - active share 0.49 → 0.13;
  - median when active 759 → 26;
  - p99 2,007 → 371.
- In the same period, P6's active share falls from 0.57 to 0.28.
- The weekly pressure-sum median drops from 2,234 to 1,403.
- P2–P5 keep their ranges.
- User02's other mat (22480) shows no drop over the same dates (P1 active share 0.19 → 0.30).
- The cause is unknown: mat moved, posture change, or a channel fault. Recorded as OPEN-19.

**Other groups.**
- 22480: stable scale across July–September (pressure sum median 1,743 / 1,771 / 1,750 by month).
- User07: gradual decline of the pressure sum median from April to June (2,262 → 1,762), then 1,916 in July. No
  step.
- Between devices, the pressure sum differs roughly two-fold: User01 (old sensor) vs the current mats. The
  per-channel profiles also differ (§2). Scale handling stays OPEN-17 (P2).

## 6. Schema

`pressure_schema_by_source.csv` / `pressure_schema_summary.csv` (raw rows per file, before de-duplication).

| Source | Files | Rows | 6-channel layout | With device column | From | Mixed files |
|---|---|---|---|---|---|---|
| user01_phase_a / b / c | 6 / 57 / 88 | 56,244 / 792,627 / 1,399,949 | all | 0 | — | 0 |
| user02_mat_22480 | 45 | 431,471 | 384,065 | 47,406 | 2026-08-29 | 0 (switch between files) |
| user02_mat_22482 | 49 | 635,126 | 506,099 | 129,027 | 2026-08-31 | 1 (`sm22482_0831`) |
| user07 | 100 | 1,008,456 | all | 0 | — | 0 |
| user02_legacy_csv / user03_legacy (reference) | 7 / 7 | 71,370 / 107,256 | all (CSV, `FSR1(A0)…FSR6(A5)`) | 0 | — | 0 |

- Expected channels: 6. Observed: 6 in every row of every source.
- 0 rows have a missing channel. 0 rows have a non-standard layout.
- `sm22482_0831` holds 3,000 rows in the old layout (08:09–16:48) and 12,002 rows with the device column
  (20:56 onward). The switch is between two recordings, not within one.
- 22480 switches between files: `sm22480_0829` starts with the device column.
- Values in the device column always equal the folder device (inventory §6).
- Legacy CSVs name the channels `FSR1(A0)…FSR6(A5)`. The mapping P_k ↔ FSR_k is by position and undocumented
  (inventory §6).
- Parser safeguard added with A9: a row with an unrecognised layout (e.g. 5 values + T/H) is recorded as
  `nonstandard`, and none of its values is assigned to P1–P6/T/H. A temperature can no longer be read as P6. The
  delivered data contain no such row, so earlier results are unaffected.

## 7. Flag candidates

Proposed columns for the canonical interim dataset (`pressure_flag_schema.csv`; proposal only, nothing applied):

| Column | Definition | Role |
|---|---|---|
| `pressure_schema` | `p6` / `p6_with_device_column` / `nonstandard` (raw line layout) | provenance; `nonstandard` = invalid input |
| `pressure_channels_present` | number of channels in the raw row; absent channels never filled | validity (< 6 = invalid input) |
| `pressure_impossible_encoding` | any channel < 0, > 4095 or non-integer | validity |
| `pressure_all_zero` | all six channels = 0 | context (empty mat / unloaded) |
| `pressure_boundary_4095_channels` | number of channels at 4095 | context (candidate boundary) |
| `pressure_frame_constant_run_s` | length of the identical non-zero frame run | context, not validity |
| `pressure_same_second_group` | same-second group id (shared with target flags) | context |
| `source_period` | provider-documented period label (User01 phase, before/after 2026-01-25) | context, not a correction |

Only the first three are validity rules. They are defined on raw encoding alone and change 0 rows today. The
others describe the data without deciding anything.

## 8. Policy sensitivity and P0 impact

`pressure_policy_impact.csv` — hypothetical unusable-row masks. Nothing is removed.

| Policy | User01 | 22480 | 22482 | User07 | Primary total |
|---|---|---|---|---|---|
| A: schema-invalid (missing channel / non-standard layout) | 0 | 0 | 0 | 0 | 0 |
| B: A + impossible encoding (< 0, > 4095, non-integer) | 0 | 0 | 0 | 0 | 0 |
| C: B + stuck heuristic (one channel constant non-zero ≥ 30 min, or frame identical ≥ 5 min) | 7,129 rows (0.33 %), 9 of 157 sessions | 0 | 0 | 0 | 7,129 (0.17 %) |

- A and B are safe to freeze. They remove nothing from the current data and guard the canonical builder
  against layout or encoding errors in future deliveries.
- **C must not be frozen.** Every row it would flag contains a 4095 channel. C does not detect stuck hardware; it
  selectively removes User01's heaviest-load moments before the sensor change. That is a subject- and
  period-specific selection, and it would bias the pressure distribution of exactly the condition OPEN-11/OPEN-17
  must handle. The "stuck" thresholds are heuristics without a raw-encoding basis.
- Proposed as D-018 (Proposed): A + B as the pressure input-validity rule. 4095 is kept as a value and flagged
  as a candidate boundary. Missing channels are never filled.
- Not decided in P0:
  - capping, clipping or exclusion of 4095 plateaus;
  - scaling or normalisation across subjects/devices (OPEN-17, P2, training data only);
  - whether User01 before/after 2026-01-25 are separate domains (OPEN-11, A10 → P2);
  - handling of the 22482 P1 shift (OPEN-19);
  - channel removal or channel selection;
  - suitability of the legacy auxiliary sources (OPEN-13).

## 9. Unresolved

1. **4095 semantics:** ADC clipping or a firmware cap? Is the same range used by the new sensor (OPEN-17)?
   Provider question.
2. **22482 P1 from 2026-08-20** (and the P6 drop): was the mat moved, replaced or damaged? Needed before 22482
   late-August data serve as test or adaptation data (OPEN-19).
3. **Physical channel layout.** The P_k positions on the mat, and the legacy `FSR_k` ↔ P_k mapping, are not
   documented. The correlation pattern suggests paired positions (1–4, 2–5, 3–6) but does not establish them
   (OPEN-20).
4. **User01's long zero runs** on unloaded channels (≥ 1 h) versus about 5 min at most on the current mats. The cause
   (sensor, sensitivity or posture) is left to A10.
5. **Legacy auxiliary quality:** User02 legacy P5 at 4095 half of the time; User03 legacy P3–P5 at 4095 7–10 %.
   Relevant before any auxiliary use (OPEN-13).
6. The User01 before/after comparison here is baseline evidence at one split point. Windows, other change dates
   and T/H effects are A10's scope.
