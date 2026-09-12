# P0-A9b — User02 / 22482 P1 Channel Anomaly Audit

| | |
|---|---|
| Phase / analysis | P0 — Dataset Audit & Data Freeze / A9b (short follow-up to A9; `docs/P0_DATASET_AUDIT_PLAN.md`) |
| Date | 2026-09-13 |
| Code | `src/data/channel_anomaly.py`, `scripts/audit_user02_channel_anomaly.py`; reuses A10 change-point and effect-size functions (`sensor_phase.py`), the A9 pressure matrix, A8 target states, the A5 audit view and A7 candidate sessions |
| Tests | `tests/test_channel_anomaly.py` (synthetic arrays only) |
| Command | `python scripts/audit_user02_channel_anomaly.py` (≈ 15 s) |
| Artifacts | `outputs/qa/p0/user02_channel_anomaly/` — `unit_channel_summary.csv`, `change_point_candidates.csv`, `boundary_window_comparison.csv`, `channel_shift_classification.csv`, `hourly_onset.csv`, `schema_firmware_timeline.csv`, `impact_summary.csv`, `figures/channel_anomaly_timeseries.png`, run meta (regenerable, not committed) |

Evidence only. No row was deleted, no channel removed, and no value corrected, imputed, clipped or normalised.
User02's two mats stay one subject. 22480 serves only as a control for concurrent environmental change; A2
showed the two mats do not measure the same movements.

## 1. Change point

The A9 date (2026-08-20) was not used as input. Change points were ranked on 22482's nightly, per-session and
daily channel summaries, with the A10 method.
- Score: robust standardised median differences for windows 1, 3 and 7, with one candidate per event.
- Consensus: over five P1 metrics (active share, median when active, p95, share of the pressure sum, dominant
  share).
- Abruptness: a one-step fit vs a line.

| Units, window | Strongest P1 split (mean rank; metrics in top 3) | Next candidate |
|---|---|---|
| Nights, w = 3 | first night **2026-08-20** (2.4; 4 of 5) | 2026-08-14 (8.0) |
| Nights, w = 7 | night **2026-08-19** (1.4; 5 of 5) | 2026-08-07 (11.8) |
| Sessions, w = 3 / 7 | 2026-08-20 (3.4) / 2026-08-19 (1.4) | 2026-07-24 (6.4) / 2026-08-04 (12.4) |
| Days, w = 3 | 2026-08-21 (the day 08-20 contains both regimes) | — |

- With adjacent nights only (w = 1), the top candidate is 2026-07-26: a one-night swing after a 43 h gap, without
  persistence. The P1 boundary is the only candidate at the top for w ≥ 3.
- **Strongest change point: the recording of the night 2026-08-19 (19:58:23 → 2026-08-20 09:58:32).**
  - Hourly, the best single split of the P1 p95 is at 2026-08-20 02:00 (R² 0.71). After it, P1 still reaches a
    few hundred in some hours until 08:00.
  - From the next recording (2026-08-20 21:37:33), no hour in the hourly window (to 2026-08-22) exceeds a P1 p95
    of about 165. No later night has a P1 p95 above 87.
- In short, the change is abrupt between nights, with a transition of about 8 h inside one recording.

## 2. Before and after

Nights (`boundary_window_comparison.csv`; Cliff's δ on nightly values; −1 means every night after is below every
night before):

| P1 metric | ±1 night | ±3 nights | ±7 nights | Whole periods (29 / 21 nights) |
|---|---|---|---|---|
| Active share | 0.34 → 0.14 | 0.51 → 0.14 (δ −1) | 0.51 → 0.14 (δ −1) | 0.52 → 0.14 (δ −1) |
| Median when active | 267 → 29 | 861 → 29 (δ −1) | 741 → 26 (δ −1) | 743 → 27 (δ −1) |
| p95 | 1,143 → 63 | 1,578 → 63 (δ −1) | 1,350 → 63 (δ −1) | 1,563 → 59 (δ −1) |
| Share of the pressure sum | 9.1 % → 0.6 % | 19.6 % → 0.6 % (δ −1) | 16.9 % → 0.6 % (δ −1) | 19.6 % → 0.6 % (δ −1) |
| IQR when active | — | 833 → 95 (δ −1) | 833 → 90 (δ −1) | — |

- **Abrupt, not gradual.**
  - The nightly ranges separate completely. Over ±7 nights, the lowest night before (0.34, the transition night)
    is above the highest night after (0.16). Over the whole periods the values are 0.31 vs 0.165.
  - A step explains more than a line over ±10 nights: active share R² 0.83 vs 0.60; p95 0.89 vs 0.73; median
    0.80 vs 0.66.
- **No recovery.**
  - The last 7 nights (to 2026-09-10; last row 2026-09-11 06:20) have a P1 active share of 0.138. The first
    7 nights after the boundary have 0.141, and the 7 nights before have 0.506. Recovered fraction ≈ 0.
  - It persists to the end of the recording.
- P1 still reports small values after the change: 14 % of loaded rows are non-zero, with a median of about 25. It
  is not a zero-only channel.

## 3. Is it P1 alone?

Cliff's δ over ±7 nights for each channel (`channel_shift_classification.csv`; |δ| ≥ 0.8 counts as shifted):

| Basis | P1 | P2 | P3 | P4 | P5 | P6 | Label |
|---|---|---|---|---|---|---|---|
| Active share | −1.0 | −0.06 | +0.35 | −0.35 | +0.10 | −0.51 | **p1_only** |
| Median when active | −1.0 | +0.10 | −0.18 | −0.51 | +0.18 | −0.47 | **p1_only** |
| p95 | −1.0 | −0.31 | −0.47 | −0.31 | −0.27 | −0.10 | **p1_only** |
| Share of the pressure sum | −1.0 | +0.27 | +0.02 | −0.06 | +0.63 | −0.10 | **p1_only** |

- **The rest of the mat is stable.**
  - Pressure-sum median without P1: 1,780 → 1,718 (δ −0.14) over ±7 nights, and 1,486 → 1,531 (δ −0.02) over the
    whole periods.
  - Active channels without P1: 2.82 → 2.68 (δ −0.35).
- The total pressure sum (2,124 → 1,737, δ −0.63) and the total active-channel count (3.17 → 2.82, δ −0.92) fall
  by about P1's former contribution. **This is channel-specific evidence.**
- **P6 is a separate, later change, not part of this event.**
  - The strongest whole-mat split away from the P1 boundary is 2026-08-25, the first night after a 48 h 22482 gap.
    That gap is where the two quarantined files `sm22482_0824/0825` lie (OPEN-02).
  - Against the post-P1 nights before it, P6's active share falls from 0.63 to 0.23 (δ −1.0). The pressure-sum
    median falls from 2,031 to 1,324 (δ −0.86), and P2/P5 read lower (δ −0.93/−0.86).
  - Over the same nights, 22480's P1 activity and pressure sum rise (δ +0.88/+0.71).
  - This looks like load moving between the mats, not like a channel fault. It is recorded as an observed
    distribution shift (OPEN-03), with no flag. The label is therefore "P1 only", not "P1 + P6".

## 4. 22480 control

Same calendar split, 22480 nights:

| 22480 | ±3 nights δ | ±7 nights δ | Change-point d at the split (largest elsewhere) |
|---|---|---|---|
| Pressure-sum median | 0.00 | +0.45 | −0.13 (1.6) |
| Active channels | −0.11 | +0.39 | −0.38 (2.7) |
| Temperature | 0.00 | +0.04 | 0.0 (1.9) |
| Humidity | +0.44 | +0.49 | +1.09 (6.0) |
| P1 / P6 active share | +0.78 / −0.33 | +0.51 / −0.02 | +0.90 / −1.01 (12.0 / 3.6) |

- There is no abrupt environmental or subject-level shift on the other mat at the same time.
- 22482's own targets are also continuous across the split (temperature d 0.0, humidity d +0.57).

## 5. Schema and firmware timeline

`schema_firmware_timeline.csv`, relative to the first fully shifted night (2026-08-20 21:37:33):

| Change | When | Distance |
|---|---|---|
| device_id column added | 2026-08-31 20:56:34 | **+11.0 days (the anomaly starts before it)** |
| Log container | quasi-JSON throughout | none |
| Sampling regime | 3 s throughout | none |
| Control/event tokens | nothing begins or ends near the boundary. Nearest: AIHON/AIHOFF/AMODE/FOH on the night 08-08/09 (−12 days, A8 glitch night); SCHATIDS on 09-01 (+11 days) | — |
| Files | the transition lies inside `sm22482_0819`; the shifted regime starts with `sm22482_0820` | daily file boundary, no format change |

No schema or firmware change coincides with the anomaly. Temporal proximity is not read as cause in either
direction.

## 6. Occupancy confound

±7 nights, 22482:
- **Unchanged:**
  - all-zero share (δ −0.02);
  - other channels' activity (δ −0.35 without P1);
  - pressure sum without P1 (δ −0.14);
  - start time (δ +0.16);
  - dominant channel: no channel takes over (|δ| ≤ 0.39; P5 dominant share 0.25 → 0.39).
- **Somewhat shorter nights:** 11.5 → 10.5 h (δ −0.55), ending earlier (δ −0.76).
- A posture that avoids P1 for three weeks while every other channel keeps its load and activity is not excluded
  by the data. However, the pattern fits a change in P1's response better than a change in occupancy. P1 still
  registers small values in 14 % of rows but never its former range.
- Placement, posture and hardware cannot be told apart from the data. Provider question kept.

## 7. Impact

Configured phases (D-022), applied as labels only (`impact_summary.csv`):

| `channel_quality_phase` | Rows (share of 22482) | Nights | Hours (share of 22482 / User02) |
|---|---|---|---|
| normal (to 2026-08-19 08:56:10) | 347,707 (58.5 %) | 28 | 290.5 (58.5 % / 50.4 %) |
| p1_transition (2026-08-19 19:58:23 → 08-20 09:58:32) | 16,804 (2.8 %) | 1 | 14.0 (2.8 % / 2.4 %) |
| p1_response_shift (from 2026-08-20 21:37:33) | 229,805 (38.7 %) | 21 | 192.0 (38.7 % / 33.3 %) |

- 22480 covers 103.1 h in 16 nights of the shifted period. 63.8 h of the shifted 22482 hours are also covered
  by 22480.
- If the shifted slice were set aside (not done), User02 would keep:
  - 447.7 h in 45 nights (last row 2026-09-05 01:11, on 22480);
  - every A11 criterion met (≥ 100 h, ≥ 20 nights, room for chronological spans).
- **User02 stays primary-eligible (D-020 unaffected).**
- User02's last six days (2026-09-05 → 09-11) exist only on 22482 in the shifted phase. This matters for late
  chronological test spans.

## 8. Quality/provenance flag and conclusion

- **OPEN-19 → class B: non-blocking, but must be flagged.**
  - The observation is reproducible without the A9 date.
  - It is abrupt, persistent and specific to P1.
  - It is not explained by the other mat, the targets, schema/firmware changes or occupancy.
  - User02 stays eligible.
- Accepted as **D-022**, configured in `configs/subject_mapping.yaml` (`channel_quality_phases`):

| Column | Values | Meaning |
|---|---|---|
| `channel_quality_phase` | `normal`, `p1_transition`, `p1_response_shift` | per device timeline; only 22482 has more than `normal` |
| `channel_quality_flag` | `p1` or empty | affected channel(s) of the row's phase |

- The boundaries are recording gaps fixed from this evidence. The transition phase covers the one recording in
  which the onset occurs, so no cut is placed inside a recording.
- Raw values stay unchanged. What to do with P1 of 22482 in the shifted phase (use, mask, model the shift, or
  choose a device) is decided in P2.
- No further anomaly audit is planned. The next step is P0 closure and the canonical data freeze.
