# P0-A10 — User01 Sensor Phase / Change-Point Audit

| | |
|---|---|
| Phase / analysis | P0 — Dataset Audit & Data Freeze / A10 (`docs/P0_DATASET_AUDIT_PLAN.md`) |
| Date | 2026-09-13 |
| Code | `src/data/sensor_phase.py` (analysis), `scripts/audit_user01_sensor_phase.py`; reuses the A5 audit view (`upload_copy_mask`), A7 timelines and candidate sessions, A8 target validity (`channel_states`) and A9 helpers (`pressure_matrix`, `boundary_summary`) |
| Tests | `tests/test_sensor_phase.py` (synthetic series and arrays only) |
| Command | `python scripts/audit_user01_sensor_phase.py` (≈ 35 s) |
| Artifacts | `outputs/qa/p0/user01_phase/` — `session_pressure_summary.csv`, `change_point_candidates.csv`, `boundary_window_comparison.csv`, `distribution_shift.csv`, `channel_pre_post_summary.csv`, `saturation_summary.csv`, `sampling_regime.csv`, `phase_assignment.csv`, `figures/user01_night_timeseries.png`, `figures/user01_channel_pre_post.png`, `user01_phase_run_meta.json` (regenerable, not committed) |

Evidence only. No value was modified, clipped, replaced, normalised, rescaled, resampled or removed. A sensor
phase is a provenance label, not a correction.

**Data.**
- User01 only: sources `user01_phase_a/b/c`, 2,152,204 rows on the A5/A7 audit timeline (identical upload-chunk
  copies excluded in memory). User06 (D-017) and User03 legacy are not used.
- Analysis units:
  - candidate sessions (proposed D-015; labels only): 157;
  - recording nights (noon to noon): 151;
  - calendar days: 157.
- "Loaded rows" (all six channels present, at least one > 0) are used for the pressure sum, active-channel counts
  and per-channel statistics.
- Target values count only where valid under A8.

## 1. Purpose

The provider documents a pressure-sensor replacement for User01 on 2026-01-25 (restricted metadata; file
`phase_c/0125_센서변경.txt`, "sensor changed"). A9 saw a large before/after difference. A10 does not take the
date as given. It checks:
- where the change actually happens;
- how abrupt it is;
- which channels change;
- whether behaviour, targets or sampling change at the same time;
- whether a `sensor_phase` provenance label is justified.

## 2. Candidate boundary

- The data place the change inside one recording gap on the documented date:

| | Timestamp | File |
|---|---|---|
| Last row before | 2026-01-25 08:07:26 | `phase_c/0124.txt` |
| First row after | 2026-01-25 17:31:21 | `phase_c/0125_센서변경.txt` |
| Gap | 9.4 h, no rows inside | — |

- The last row with a channel at 4095 is at 08:03:34, 4 min before the gap. In the last two morning hours 50 %
  and 27 % of rows have a 4095 channel.
- From the first evening row, no 4095 value appears for 50 h (§5).
- In the rest of this report, "before" means rows up to 08:07:26 on 2026-01-25 and "after" means rows from
  17:31:21 on 2026-01-25.

| Candidate phase | Rows | Sessions | Nights | Provider source folders |
|---|---|---|---|---|
| before (`s1`) | 1,198,692 | 91 | 86 | phase_a, phase_b, phase_c (to 01-25) |
| after (`s2`) | 953,512 | 66 | 65 | phase_c (from 01-25) |

The provider's `phase_a/b/c` are collection folders, not sensor phases: `phase_c` contains both sensors.

## 3. Before/after evidence

Unit-level comparison of nights (`boundary_window_comparison.csv`). The unit, not the row, is the analysis unit.
δ = Cliff's delta: −1 or +1 means every night after is below or above every night before.

| Window (nights) | Pressure-sum median | Pressure-sum p95 | Rows with a 4095 channel | Active channels (mean) |
|---|---|---|---|---|
| ±1 | 6,101 → 4,666 | 10,772 → 6,567 | 15.0 % → 0 | 2.72 → 4.02 |
| ±3 | 6,101 → 3,736 (δ −1) | 11,091 → 5,856 (δ −1) | 16.1 % → 0 (δ −1) | 2.72 → 3.82 (δ +1) |
| ±7 | 6,390 → 3,364 (δ −0.92) | 11,091 → 5,840 (δ −1) | 16.1 % → 0 (δ −1) | 2.72 → 3.82 (δ +1) |
| ±14 | 6,087 → 3,361 (δ −0.97) | 10,889 → 5,355 (δ −1) | 16.0 % → 0 (δ −1) | 2.72 → 3.66 (δ +1) |
| whole periods (86 / 65 nights) | 4,101 → 3,024 (δ −0.96) | 9,354 → 4,792 (δ −1) | 20.7 % → 0 (δ −1) | 1.76 → 3.56 (δ +1) |
| placebo: 14 vs 14 nights before | 6,426 → 6,087 (δ −0.29) | δ −0.12 | δ −0.03 | δ +0.09 |
| placebo: 14 vs 14 nights after | 3,361 → 3,128 (δ −0.40) | δ −0.55 | 0 → 0 | δ +0.18 |

- **Complete separation in ±14 nights.**
  - p95: the highest night after (6,567) is below the lowest night before (9,426).
  - 4095 rows: highest after 0.04 % vs lowest before 10.3 %.
  - Active channels: highest before 2.85 vs lowest after 3.45.
- Candidate sessions give the same result (±3 sessions: δ = −1/−1/−1/+1).
- The same window placed elsewhere (placebo) shows small effects and no separation. So the difference is not a
  property of any 14-night comparison.
- Row-level distribution shift (`distribution_shift.csv`, pressure sum on loaded rows, ±14 nights):
  - Wasserstein 2,545 and KS 0.48 (201,654 vs 213,142 rows);
  - placebo: Wasserstein 189 / KS 0.03 before the boundary, 377 / 0.11 after it.
  - Row-level p-values are not used; with ~200,000 rows every difference would be "significant".
- The whole-period comparison mixes further changes inside the before period (§6). The local windows are the
  evidence for the boundary.

QA figure `figures/user01_night_timeseries.png` (regenerable, not committed) shows the pressure sum, the 4095
share, active channels and the sampling step per night, with 2026-01-25 marked.

## 4. Channel-level changes

±14 nights, loaded rows (`channel_pre_post_summary.csv`; also whole-period values). "Active" = channel > 0.

| Channel | Active share | Median when active | p95 | Share at 4095 | Share of pressure sum |
|---|---|---|---|---|---|
| P1 | 21 % → 48 % | 39 → 458 | 303 → 1,996 | 0.06 % → 0.002 % | 1.8 % → 10.5 % |
| P2 | 57 % → 70 % | 2,665 → 1,019 | 3,757 → 1,883 | 0.79 % → 0.0005 % | 21.8 % → 20.2 % |
| P3 | 69 % → 69 % | 3,708 → 1,259 | 4,095 → 2,067 | 11.5 % → 0 | 36.7 % → 23.2 % |
| P4 | 25 % → 22 % | 99 → 51 | 2,761 → 237 | 0.65 % → 0 | 4.2 % → 1.2 % |
| P5 | 57 % → 76 % | 3,123 → 896 | 4,014 → 1,861 | 2.9 % → 0.0005 % | 24.9 % → 19.4 % |
| P6 | 40 % → 83 % | 1,125 → 1,043 | 3,562 → 2,169 | 1.4 % → 0.0005 % | 10.7 % → 25.4 % |

How the four kinds of change look:
- **Overall scale:** the pressure sum drops by about 45 % (median) and 51 % (p95).
- **Saturation:** the accumulation at 4095 disappears in every channel (§5).
- **Level compression:** the heavily loaded channels P2, P3 and P5 read about one third of their former
  median-when-active, and their p95 roughly halves. P3's IQR shrinks from 3,864 to 1,485.
- **Contact distribution:** P1, P5 and P6 respond far more often (P6 40 % → 83 %). Mean active channels rise by
  about one. P4 stays mostly silent. P6's median-when-active is unchanged while its share of the sum doubles.
  All 77 of A9's User01 zero runs ≥ 30 min on unloaded channels (`constant_channel_runs.csv`) lie before the
  boundary.

This is not a single multiplicative factor. High values compress while low-load channels register more often. A10
does not infer sensor geometry, placement or the physical cause from this (OPEN-20).

QA figure `figures/user01_channel_pre_post.png` shows the ECDF of each channel's values when active, 14 nights
before vs after.

## 5. 4095 behaviour

Described as upper-bound accumulation consistent with clipping or saturation. It is not asserted as sensor
saturation. Source: `saturation_summary.csv`.

| | Before (`s1`) | After (`s2`) |
|---|---|---|
| Cells at 4095 | 275,583 | 18 |
| Rows with ≥ 1 channel at 4095 | 264,409 (22.1 %) | 18 (0.002 %) |
| Rows with 1 / 2 / 3 channels at 4095 | 253,378 / 10,888 / 143 | 18 / 0 / 0 |
| Sessions with any 4095 row | 91 of 91 (median 20.5 % of rows) | 9 of 66 (max 0.04 %) |
| By channel | P3 214,415 · P6 33,707 · P2 12,714 · P5 8,654 · P4 3,441 · P1 2,652 | P2 8 · P1 7 · P5 2 · P6 1 · P3 0 · P4 0 |
| Longest run | 806 rows / 2,356 s (P6); P3 783 rows / 1,686 s | 2 rows / 3 s |
| Accumulation vs values 4085–4094 | 171 × the mean count per value just below | isolated cells |

- **The disappearance is immediate.** Every hour up to the gap has 4095 rows (e.g. 50 % at 06:00). Every hour
  after it has none.
- The first later 4095 cell appears on 2026-01-27 at 19:27:56, about 50 h after the boundary. All 18 later cells
  are isolated single cells in 9 sessions.

## 6. Change-point analysis

**Method** (`change_point_candidates.csv`). The known date is not used; this is a time-series scan.
- For each unit series and every split between two consecutive units, compute d_w = (median of the w units
  after − median of the w units before) / robust unit-to-unit noise, for w = 1, 3, 7 and 14.
- The noise is 1.4826 × MAD of adjacent-unit differences / √2. A step is only one outlier among these
  differences, so it barely inflates the noise estimate.
- Splits are ranked per metric. A consensus ranks the mean rank of four core metrics: pressure-sum median,
  pressure-sum p95, 4095 row share and mean active channels.
- A window of w units sees the same step from every nearby split. Only the strongest split within ±w units is
  kept (non-maximum suppression).
- Abruptness is checked with a one-step fit vs a straight line over ±14 units.
- No library was added.

**Result.**
- **2026-01-25 is the strongest change point in the User01 series.** It is the first distinct candidate of the
  core consensus for nights and sessions at w = 3 and w = 7. At w = 14 the peak sits one unit later, which is the
  same event.
- Its margin is large:

| Units, window | 2026-01-25 (mean rank) | Next distinct candidate |
|---|---|---|
| Nights, w = 3 | 3.75 | 2025-12-25 (9.5), then 2025-12-18 (20.5) |
| Nights, w = 7 | 4.0 | 2025-12-25 (24.75) |
| Sessions, w = 3 | 4.75 | 2025-12-28 (10.25) |

- Using only adjacent units (w = 1), it ranks 2nd (sessions) or 3rd (nights). Ahead of it are single-unit jumps:
  2025-11-06, right after the 2-month collection gap, and 2025-12-25. It is the only candidate at the top for
  every window.
- Per metric (nights, w = 3):
  - The boundary is the top distinct candidate for pressure-sum p95 (d −10.0; largest elsewhere 7.3), active
    channels (d +9.3; elsewhere 8.3 on 2025-12-17), P2 p95 and P3 p95 (d −15.2; elsewhere 2.4).
  - The pressure-sum median (d −13.1) and the 4095 share (d −10.1) each have one larger single-metric shift
    elsewhere (2025-12-25 +19.3; 2025-11-06 +17.3). Neither of those is accompanied by the other metrics.
- **Step, not drift** (±14 nights, variance explained by one step vs a line):

| Metric | Step | Line |
|---|---|---|
| pressure-sum median | 0.79 | 0.63 |
| pressure-sum p95 | 0.96 | 0.76 |
| 4095 share | 0.94 | 0.68 |
| active channels | 0.93 | 0.59 |
| P3 p95 | 0.99 | 0.76 |

**Other changes inside the before period.** These are real and not merged into the sensor change. ±7 nights at
each candidate:

| Date | What it is | Largest effects (δ) | 4095 share |
|---|---|---|---|
| 2025-11-05 | start of phase_b after a 2-month gap; sampling 2 s → 3 s; season | humidity 69 → 35 %RH (−1.0), temp −2 °C | 44 % → 20 % (−0.86) |
| 2025-11-18 | heating-season start (metadata) | dominant-channel switches 29 → 48 /h (0.88) | no change (−0.35) |
| **2025-12-17** | **documented log-format change** (first compressed/quasi-JSON log) | **active channels 1.51 → 2.49 (+1.0, complete separation)**; dominant switches 29 → 92 /h (+1.0); sum median +13 % (0.94) | unchanged (0.02) |
| 2025-12-25 | none documented | sum median 4,619 → 6,868 (0.84); active channels 2.49 → 2.73 (0.88) | 0.39 |
| 2026-01-03…07 | temporary 2 s sampling (§8) | 4095 share 24 % → 8 % (−1.0) for about a week, then recovers; sum median −18 % | transient |

- The before period is therefore not homogeneous.
- 2025-12-17 is a second abrupt, acquisition-side candidate. It coincides with a documented firmware/log change
  and alters channel activity, not the upper bound. It is recorded as OPEN-21, not as a sensor phase.
- 2025-12-25 is unexplained.

## 7. Behavioural and T/H confounds

±14 nights, unit level:

| | Before | After | δ | Reading |
|---|---|---|---|---|
| Recording duration (h) | 12.25 | 12.51 | +0.31 | unchanged |
| Start / end clock time | 18:10 / 06:27 | 18:16 / 06:47 | ≤ 0.38 | unchanged |
| Temperature median (°C) | 27.0 | 27.5 | −0.01 | continuous |
| Humidity median (%RH) | 16.5 | 16.0 | −0.05 | continuous |
| Dominant-channel switches per occupied hour | 121 | 123 | +0.11 | unchanged (scale-free movement proxy) |
| All-zero share | 2.9 % | 1.2 % | −0.83 | threshold-dependent |
| Firmware "absent" (NM) label share | 6.9 % | 2.8 % | −0.81 | threshold-dependent |
| Active-set changes per occupied hour | 875 | 706 | −1.0 | sensor-dependent (more channels stay active) |

- **Recording duration and clock time do not explain the shift.** Restricted to 00:00–05:00, the pressure sum
  moves by the same amount: 5,895 → 3,324, Wasserstein 2,541, KS 0.47.
- **The targets are continuous across the boundary.** Change-point scores at the split are about 0 for
  temperature, humidity, duration and sampling, against their own largest changes of 3.8–10 elsewhere. T/H do
  shift a few weeks later (February: temp 27.5 → 24 °C, humidity 16 → 29 %RH in the next 14 nights), with the
  season, not at the boundary.
- **Limits.**
  - Movement labels (UM/DM/LM/RM/NM) are derived by the firmware from pressure-sum shifts and an occupancy
    threshold (inventory §6), so they depend on the sensor; label coverage is about 99 % on both sides.
  - The all-zero share and the active-set rate are threshold-dependent in the same way.
  - Only the scale-free dominant-switch rate is a reasonably sensor-independent proxy, and it does not change.
- Behaviour cannot be ruled out completely. A pressure-only step with unchanged duration, clock time, T/H and
  movement frequency is consistent with an acquisition-side change. That supports, but does not prove, the
  documented hardware replacement.

## 8. Sampling regime

`sampling_regime.csv` (steps ≤ 60 s):

| Period | Median step | Step shares |
|---|---|---|
| phase_a, 2025-08-25 → 09-01 | 2 s | 98 % at 2 s |
| 2025-11-05 → 2026-01-02 | 3 s | 2 s ≈ 20–27 %, 3 s ≈ 70–72 %, no 1 s |
| **2026-01-03 → 01-07** | **2 s (temporary)** | 87–91 % at 2 s on 01-04…01-06 |
| 2026-01-08 → 2026-04-02 | 3 s, wider jitter | 1 s ≈ 8 %, 2 s ≈ 13 %, 3 s ≈ 55 %, 4 s ≈ 14 %, 5 s ≈ 8 % |

- Sampling changes on 2025-11-05, 2026-01-03 and 2026-01-08. **None of these is the sensor boundary.**
- Across 2026-01-25 the median step (3 s) and the jitter profile are unchanged (e.g. 2 s share 14.0 % on 01-25
  vs 13.2 % on 01-26).
- The two phenomena are separate and are not merged.

## 9. Phase definition candidate

A10 meets the three criteria for an Accepted boundary:
- a clear timestamp interval;
- consistent change across several pressure statistics;
- an abrupt step compared with the surrounding sessions and placebo windows.

It is proposed as **D-019 (Accepted, provenance only)**:

| Field | Value |
|---|---|
| `sensor_phase` (User01) | `s1` for rows ≤ 2026-01-25 08:07:26; `s2` for rows ≥ 2026-01-25 17:31:21 |
| Boundary | the recording gap between these two rows; no row lies inside |
| Other subjects/devices | `s1`, meaning no documented sensor change. The 22482 P1 shift (OPEN-19) is not a phase |
| Naming | `s1/s2` avoids confusion with the provider's `phase_a/b/c` folders |

- The label changes no value. It must not be moved after model results are seen.
- Not decided here:
  - acquisition-period labels for 2025-12-17 and the 2 s episode (OPEN-21);
  - any normalisation, clipping or phase-specific model (P2).

## 10. Research impact

- **LOSO (RQ1).**
  - User01 carries two acquisition domains. Its pre/post difference is as large as the gap to the other subjects
    (pressure-sum median 4,420 / 2,976 vs 1,764–2,037 on the current mats; A9).
  - When User01 is the held-out subject, results should be reportable per `sensor_phase`.
  - When User01 is a training subject, any scaling fitted on training data (L3) will see both domains. How to
    treat this is a P2 decision (OPEN-11, OPEN-17).
- **Personalization (RQ2).** A chronological adaptation span in `s1` followed by a test span in `s2` would
  confound adaptation with the hardware change. Options belong to the P2 protocol and are not decided here:
  - keep both spans within one phase;
  - forbid spans that cross the boundary;
  - report the boundary as a stratifier.
- **Splits and windows.** Calendar days are unsuitable as units near the boundary: day 2026-01-25 contains both
  phases. Sessions and nights do not. The before period itself contains an activity change on 2025-12-17, which
  matters if an adaptation span lies there.

## 11. Unresolved

1. The physical nature of the replacement (sensor model, range or gain, placement), and whether 4095 is ADC
   clipping or a firmware cap (OPEN-17). Provider question.
2. **2025-12-17:** did the log-format/firmware change also change pressure reporting (threshold, filtering)?
   Active channels and switch rates change abruptly on that night (OPEN-21).
3. **2026-01-03…07:** why was sampling at 2 s, and why did the 4095 share dip during that week (OPEN-21)?
4. **2025-12-25:** an undocumented level shift in the pressure sum (+49 %). Cause unknown (behaviour, bedding).
5. **Stability of `s2`:** active channels drift from about 3.8 to about 3.2 between February and April, and the
   pressure sum declines slowly. This is gradual, not a step. Whether a new sensor "settles" is unknown.
6. The session and night definitions used here are candidates (D-015, proposed). The boundary itself does not
   depend on them: it is the same gap in every unit type.
