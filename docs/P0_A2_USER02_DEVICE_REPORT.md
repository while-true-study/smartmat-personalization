# P0-A2 — User02 Dual-Device Overlap Analysis

| | |
|---|---|
| Phase / analysis | P0 — Dataset Audit & Data Freeze / A2 (`docs/P0_DATASET_AUDIT_PLAN.md`) |
| Date | 2026-09-12 |
| Code | `src/data/device_overlap.py` (analysis), `scripts/audit_user02_devices.py` (I/O, tables) |
| Tests | `tests/test_device_overlap.py` (synthetic fixtures only) |
| Command | `python scripts/audit_user02_devices.py` (≈ 3 min) |
| Input | Sources `user02_mat_22480`, `user02_mat_22482`, `user02_mat_22480_prefix_mismatch` from the raw manifest (SHA-256 `dcf25e98b7d6f3a7…`); raw integrity verified before the run |
| Artifacts | `outputs/qa/p0/user02_devices/` — `device_summary.csv`, `temporal_overlap.csv`, `aligned_device_comparison.csv`, `lagged_correlation.csv`, `event_lag_scan.csv`, `event_lag_scan_by_date.csv`, `daily_th_difference.csv`, `occupancy_sensitivity.csv`, `device_distributions.csv`, `daily_device_profile.csv`, `prefix_mismatch_evidence.csv`, `user02_devices_run_meta.json` (regenerable, not committed; `CONVENTIONS.md` §5) |

This report contains evidence and clearly separated interpretation. It does **not** merge, select, resample,
calibrate or filter any data, and it does not decide how User02's devices will be used.

---

## 1. Purpose

User02 is a provisional primary subject (D-013) with two devices, 22480 and 22482 (D-003). A1 showed that the
two streams are not copies of each other. A2 describes, reproducibly:
- how the two devices record in time;
- whether they capture the same body movements and occupancy;
- how their temperature/humidity relate;
- whether they behave as different measurement domains within one subject;
- which device the two quarantined `_prefix_mismatch` files most likely come from.

## 2. Method

- **Identity.** Streams are built from `configs/subject_mapping.yaml`. All three sources resolve to one evaluation
  group, `User02` (checked at run time). Device IDs are never used as subject IDs.
- **Analysis view (in memory only).** Per device, rows are sorted by time. Identical rows repeated across adjacent
  daily files are counted once. Where two different rows share a second, the first in file order is used. This is
  a view for these statistics only, not the P0 de-duplication policy (OPEN-07). Nothing is written.
- **Coverage.** Each row covers the time until the next row, capped at a *coverage gap rule* of 10, 60 or 300 s
  (a descriptive parameter, not a session rule). Joint and exclusive recording time come from a per-second grid.
- **Pairing, not resampling.** Cross-device comparisons pair each 22480 row with the nearest existing 22482 row
  within ±1 s (sensitivity: ±3 s), restricted to jointly recorded time. No value is created or interpolated.
- **Pressure descriptors** (per device, never combined across devices): `pressure_sum` (P1+…+P6),
  `pressure_mean`, `pressure_std` across channels, number of active channels (> 0), and frame-to-frame change
  magnitude Σ|ΔPᵢ| (steps ≤ 5 s).
- **Coupling tests.**
  - Pearson and Spearman correlation at lag 0.
  - Lag profile from −30 to +30 s, with ±24 h as a control.
  - Coincidence of large movement events (top 10 / 5 / 1 % of change magnitude on each device) within ±3 and
    ±10 s, against the same statistic with one device shifted by ±24 h.
  - Supplementary clock-offset check: the event coincidence scanned over ±12 h in 5 s steps, pooled and per date.
- **Occupancy.** No threshold is frozen. Occupancy is evaluated under 14 definitions:
  - absolute `pressure_sum` thresholds 0–2000;
  - device-relative quantiles of each device's non-zero `pressure_sum`;
  - active-channel count ≥ 1/2/3;
  - the firmware label (≠ `NM`).
- **T/H.** Implausible values are masked for these statistics only (`0 < temp < 60`, `0 < humid ≤ 100`;
  sentinels and glitches, OPEN-09).

## 3. Recording coverage

| | 22480 | 22482 | quarantined (`_prefix_mismatch`) |
|---|---|---|---|
| Files | 45 | 49 | 2 |
| Raw rows | 431,471 | 635,126 | 22,205 |
| Identical rows repeated across files (counted once in view) | 33,023 | 40,917 | 3 |
| Seconds with two different rows | 992 | 1,225 | 36 |
| First / last row | 2026-07-19 19:54 / 09-05 01:11 | 2026-07-19 19:41 / 09-11 06:20 | 2026-08-24 07:06 / 08-26 06:39 |
| Calendar dates with data | 48 | 52 | 3 |
| Active recording hours (gap rule 10 / 60 / 300 s) | 332.1 / 332.8 / 335.8 | 495.1 / 496.5 / 501.6 | 18.5 / 18.6 / 18.8 |
| Δt median; share of 2 / 3 / 4 s | 3 s; 13 / 56 / 13 % | 3 s; 14 / 57 / 14 % | 3 s; 14 / 57 / 14 % |
| Δt ≤ 1 s / 5–10 s | 8.8 % / 8.8 % | 7.8 % / 7.8 % | 7.7 % / 7.4 % |
| Gaps > 60 s / > 2 h | 46 / 44 | 82 / 55 | 3 / 2 |
| Share of recording between 09:00 and 18:00 | 0.3 % | 2.4 % | 0 % |

- Both devices sample at a nominal 3 s with symmetric ±1–2 s jitter. They have the same sampling profile.
- Recording is nocturnal on both devices. 22480 covers roughly 19:00–06:00; 22482 roughly 20:00–09:00 and records
  more in the early morning (06–09 h). Daytime recording is rare on both.
  **Correction:** the initial inventory (§7.4) and issue draft P0-02 said 22482 "often records around the clock".
  That came from file spans, which contain several nights, not from continuous recording. It is corrected here.

## 4. Temporal overlap

Gap rule 60 s (10 s and 300 s give the same picture within 1.5 %):

| Measure | Value |
|---|---|
| Dates with data on both devices | 46 |
| Recording time: 22480 / 22482 / union | 332.8 h / 496.5 h / 576.0 h |
| **Simultaneous recording** | **253.3 h** |
| Only 22480 / only 22482 | 79.5 h / 243.2 h |
| Simultaneous ÷ union | 44.0 % |
| Simultaneous ÷ 22480 time / ÷ 22482 time | **76.1 %** / 51.0 % |
| Periods ≥ 30 min recorded by only one device | 35 (22480) / 68 (22482) |

- Per date, the simultaneous share ranges from 0 to 94 % (`temporal_overlap.csv`, level `date`). It is highest in
  the first week (77–94 %).
- Longer single-device periods: 22482 alone from 2026-09-06 to 09-11 (22480 ends 09-05 01:11). No 22482 files on
  08-25, the day covered by the quarantined files. 22480 alone on 07-26.
- Timestamp alignment during simultaneous recording (302,419 rows of 22480):

| Tolerance | exact (0 s) | ±1 s | ±3 s |
|---|---|---|---|
| 22480 rows with a 22482 row | 31.4 % | 88.6 % | 99.8 % |
| 22482 rows with a 22480 row | 31.3 % | 89.6 % | 99.7 % |

Median |Δt| to the nearest row of the other device is 1 s (90th percentile 2 s). The two streams are *not*
sample-synchronous. Any future alignment policy has to handle ±1–2 s jitter (not decided here).

## 5. Pressure relationship

**Lag 0** (pairs within ±1 s, n = 267,889; ±3 s gives the same values to two decimals):

| Descriptor | Pearson (all pairs) | Spearman (all pairs) | Pearson (both active) | Spearman (both active) |
|---|---|---|---|---|
| pressure_sum (= pressure_mean × 6) | −0.028 | −0.024 | −0.016 | −0.019 |
| pressure_std | −0.024 | −0.026 | −0.015 | −0.023 |
| active_channels | −0.015 | −0.004 | 0.009 | 0.012 |
| change_magnitude | −0.001 | −0.003 | −0.001 | 0.001 |

**Lags −30…+30 s.** For change magnitude, |r| ≤ 0.006 (Pearson and Spearman) at every lag, with no peak. The
±24 h controls give 0.001–0.007. For pressure_sum, r lies between −0.034 and −0.028 at every lag (controls −0.039 / +0.013).
Lag resolution is about ±1 s because rows are ≈ 3 s apart and paired within ±1 s.

**Large movement events** (share of one device's events with an event on the other device nearby):

| Event threshold | Window | 22480→22482 observed / 24 h control | 22482→22480 observed / control | Lift |
|---|---|---|---|---|
| top 10 % | ±3 s | 0.157 / 0.161 | 0.170 / 0.172 | 0.97–0.99 |
| top 10 % | ±10 s | 0.333 / 0.337 | 0.376 / 0.377 | 0.99–1.00 |
| top 5 % | ±3 s | 0.079 / 0.083 | 0.086 / 0.089 | 0.95–0.97 |
| top 1 % | ±3 s | 0.015 / 0.020 | 0.015 / 0.020 | 0.74–0.76 |

**Clock-offset check (supplementary).** A constant clock offset between the devices would hide coupling from the
±30 s analysis. Scanning the top-5 % event coincidence over ±12 h in 5 s steps:
- Pooled, lag 0 gives 0.079 against a median of 0.080 over all well-sampled lags. The maximum is 0.0995 at
  +5,675 s (robust z = 2.8 across ≈ 10,000 lags, i.e. unremarkable).
- Per date, the lag-0 share has a median of 0.072 (max 0.138). The best lag per date reaches at most 0.405
  (08-30, 84 events), and that is not replicated on any other date.
- In the synthetic test, a genuine clock-shifted copy gives a share of 1.0 at its offset.

**Evidence.** Within ±30 s, and also allowing any constant or day-specific clock offset within ±12 h, the two
devices' pressure signals show no detectable coupling. Levels, spread, active channels and movement changes are
all uncorrelated, and large movements on one mat are no more likely to coincide with movements on the other than
at the same time of day on another day.

**Interpretation (not a conclusion).** In the recorded data, the two mats do not register the same body movements
at the same time. Possible explanations include different placement (e.g. separate surfaces, or positions not
under the same body at the same time), other load on one mat, or timestamps that do not reflect real time in a
consistent way. The data cannot distinguish these. **Physical placement and use require provider confirmation**
(issue P0-02). Nothing here shows that either device is faulty.

## 6. Occupancy / activity sensitivity

Pairs within ±1 s during simultaneous recording (n = 267,889; firmware-label row n = 264,844):

| Occupancy definition | Both | Only 22480 | Only 22482 | Neither | Cohen's κ |
|---|---|---|---|---|---|
| pressure_sum > 0 | 0.899 | 0.077 | 0.023 | 0.001 | −0.02 |
| pressure_sum > 100 | 0.779 | 0.174 | 0.044 | 0.004 | −0.04 |
| pressure_sum > 500 | 0.660 | 0.233 | 0.086 | 0.022 | −0.04 |
| pressure_sum > 1000 | 0.527 | 0.249 | 0.153 | 0.071 | −0.00 |
| pressure_sum > 2000 | 0.181 | 0.209 | 0.301 | 0.309 | −0.03 |
| device quantile q0.10 (579 / 151) | 0.698 | 0.180 | 0.107 | 0.015 | −0.07 |
| device quantile q0.25 (1152 / 944) | 0.505 | 0.227 | 0.185 | 0.084 | 0.00 |
| device quantile q0.50 (1764 / 1940) | 0.231 | 0.251 | 0.264 | 0.254 | −0.03 |
| active channels ≥ 2 | 0.755 | 0.180 | 0.057 | 0.008 | −0.03 |
| active channels ≥ 3 | 0.423 | 0.260 | 0.196 | 0.121 | 0.00 |
| firmware label ≠ NM | 0.672 | 0.231 | 0.077 | 0.021 | −0.03 |

(All 14 definitions are in `occupancy_sensitivity.csv`.)

- The **"both active" share depends strongly on the threshold** (0.18–0.90). No single figure describes
  co-occupancy. The 66.8 % quoted in the inventory corresponds to the firmware-label definition (67.2 % here).
- **Agreement beyond chance is absent under every definition** (κ between −0.07 and +0.00). Both mats are loaded
  most of the time they record (`pressure_sum > 0` in ≈ 97 % / 93 % of rows), but when one changes state the other
  does not follow.
- No occupancy threshold or sample-filtering rule is derived from this (OPEN-06, OPEN-09).

## 7. Temperature and humidity

Pairs within ±1 s, both plausible (n = 267,078). ±3 s pairing and the inventory's per-minute-median method give the
same medians:

| | 22480 median | 22482 median | Median diff (22480 − 22482) | Mean diff (bias) | MAE | 5–95 % of diff | Pearson / Spearman |
|---|---|---|---|---|---|---|---|
| Temperature (°C) | 29 | 31 | **−2.0** | −2.05 | 2.16 | −6 … 0 | 0.27 / 0.21 |
| Humidity (%RH) | 51 | 69 | **−19.0** | −18.4 | 18.6 | −29 … −3 | 0.72 / 0.70 |

- **Inventory figures reproduced exactly:** −2 °C and −19 %RH. The per-minute-median method over 15,165 jointly
  recorded minutes gives −2.0 / −19.0 with r = 0.28 / 0.73.
- **Persistence (by date, 46 dates):**
  - Humidity is lower on 22480 on **all 46 dates** (daily median difference −27 … −4 %RH). The size varies by
    period: −22 … −27 on 07-19…07-29, −4 … −8 on 08-03…08-06, and mostly −12 … −25 afterwards, with single days
    at −8 (07-31, 09-05) and −4 (08-17).
  - Temperature is lower or equal on 22480 on 44 of 46 dates (−5 … +1 °C). The largest gaps (−4 … −5 °C) are
    mostly on 08-03…08-06.
  - The daily correlation of the two temperature series ranges from −0.81 to +0.92, so the devices do not track
    one common temperature signal.
- **Different temperature regimes:** 22480 is almost constant (p5–p95 28–30 °C; daily medians 28–32 °C), while
  22482 varies more (p5–p95 29–35 °C). Humidity p5–p95: 22480 39–63 %RH, 22482 35–86 %RH.
- **Evidence:** a persistent offset in direction, a time-varying size, and weak temperature co-variation.
  **Interpretation limits:** this does not establish a calibration error, a sensor fault or a location difference.
  Each could produce such patterns, and the heated-mat control loop (OPEN-10) may shape 22480's narrow temperature
  band. Sensor placement needs provider confirmation.

## 8. Device-domain differences

| Descriptor | 22480 | 22482 | quarantined |
|---|---|---|---|
| pressure_sum, active rows: p5 / median / p95 / p99 | 244 / 1,764 / 3,467 / 4,209 | 33 / 1,940 / 3,876 / 4,675 | 31 / 1,803 / 3,732 / 4,387 |
| Rows with zero pressure | 2.6 % | 7.1 % | 4.2 % |
| Firmware label `NM` (absent) | 9.8 % | 21.5 % | 17.8 % |
| Active channels = 1 / 2–4 / 5–6 | 4.2 % / 84.3 % / 8.9 % | 11.7 % / 65.8 % / 15.4 % | 16.5 % / 70.9 % / 8.3 % |
| Channel load (share of rows at 0): P1, P2, P3, P4, P5, P6 | 78, 39, 28, 83, 37, 35 % | 65, 44, 54, 46, 45, 54 % | 86, 43, 54, 43, 42, 56 % |
| Channel p95: P1 … P6 | 172, 1549, 1677, 135, 1255, 1067 | 1389, 1235, 1254, 1447, 1678, 1237 | 60, 1515, 1225, 1391, 1527, 1508 |
| Cells at ADC max 4095 | 17 (all on P2) | 0 | 0 |
| Temperature p5 / median / p95 | 28 / 29 / 30 °C | 29 / 32 / 35 °C | 30 / 33 / 35 °C |
| Humidity p5 / median / p95 | 39 / 52 / 63 %RH | 35 / 66 / 86 %RH | 57 / 71 / 87 %RH |
| Implausible T/H rows | 0.0 % | 0.3 % (incl. 08-08 glitches) | 0.0 % |
| Sampling interval | 3 s nominal | 3 s nominal | 3 s nominal |

- Sampling is identical. Pressure **scale** is similar (median active sum 1,764 vs 1,940).
- The **channel-load pattern differs**: 22480 rarely loads P1 and P4, while 22482 loads all six channels. 22482
  has more low-load and empty rows.
- T/H regimes differ systematically (§7).
- **Evidence:** within one subject, the two devices differ in channel-load pattern, empty-mat frequency and T/H
  regime, and their signals are independent in time (§5–§6). This supports treating *device* as a separate
  domain factor within User02 in later phases. It does not decide normalisation, calibration or selection
  (OPEN-17, OPEN-03).

## 9. Prefix-mismatch files: device evidence

The two files `sm22482_0824` and `sm22482_0825`, stored in the 22480 archive (`prefix_mismatch_evidence.csv`):

| Evidence | Observation | Points to |
|---|---|---|
| Storage location | Delivered inside the 22480 archive (isolated by the provider) | 22480 |
| Filename prefix | `sm22482_` | 22482 |
| JSON root key | `smartmat_22482` | 22482 |
| Missing files | 22482 has no 0824/0825 files; 22480 has its own 0824/0825 files | 22482 |
| Simultaneity | 7.0 h simultaneous with 22480's own stream, with 0 shared rows (A1); 0 h with 22482 | 22482 — one device cannot log two different streams at once, unless 22480's own files for these dates are misattributed |
| Continuity | Starts 30.1 min (1,806 s) after 22482's last row (about one upload chunk) and ends 3 s (one sampling interval) before 22482's next row. Against 22480: 278 min after, 809 min before | **22482** |
| T/H vs 22480 while simultaneous | 22480 − quarantined: −2.0 °C, −16 %RH (n = 7,421 pairs); typical 22480 − 22482: −2.0 °C, −19 %RH | 22482 (a same-device comparison would give ≈ 0) |
| Daily humidity median | 74, 71, 68 %RH; neighbouring days 22480: 48–58, 22482: 61–78 (ranges do not overlap) | 22482 |
| Daily temperature median | 32, 33, 32 °C; 22480: 28–30, 22482: 29–33 | outside 22480, inside 22482; ranges touch → neutral by rule |
| Recorded hours, daytime hours, max channel value, pressure p95, empty-mat share | within the overlapping ranges of both devices (full day only for duration-type metrics) | neutral |
| Channel-load pattern | Resembles 22482 in P3, P4, P6 and differs from both in P1 | mixed |

**Assessment of the evidence:** strong and consistent evidence for **22482**: identifiers in the files, the
seamless fit into 22482's timeline, simultaneous but distinct recording next to 22480, and 22482's T/H regime.
The only item pointing to 22480 is where the files were stored. **Device attribution remains `unresolved`** in
`configs/subject_mapping.yaml` until the provider confirms (D-006, OPEN-02). Subject attribution (User02) is
unaffected.

## 10. Research implications (for later decisions; nothing decided here)

1. **Evaluation grouping is fixed regardless:** both devices belong to User02 and must be in the same fold
   (RESEARCH_PROTOCOL L8). This analysis confirms why: 253 h of simultaneous recording.
2. **Fusion into one 12-channel "body" signal is not supported by the data as they stand.** The devices do not
   co-register movements, so concatenating their channels would not describe one body posture. This is evidence
   against a fusion policy, not a decision (OPEN-03).
3. **Device is a domain factor within User02.** It affects the target distribution (T/H offset of −2 °C /
   −19 %RH, different temperature regimes) and the input distribution (channel-load pattern). Chronological
   personalization and within-subject evaluation must not mix devices unknowingly. Pooling both devices, choosing
   one, or treating them as two within-subject domains are open options for P2, after provider confirmation.
4. **Occupancy is threshold-sensitive.** Any future occupancy-based filtering needs its own justified rule
   (OPEN-06/09). A single "both occupied" figure is not meaningful.
5. **Alignment jitter.** Cross-device pairing at ±1 s covers 89 % of rows and at ±3 s 99.8 %. Relevant only if a
   later protocol needs cross-device alignment.

## 11. Unresolved — provider confirmation needed

- **Physical placement and use of each mat** during 2026-07-19 → 09-11: same surface? which body region? separate
  beds or rooms? Was anyone or anything else on either mat? (OPEN-03)
- **Location of the T/H sensor** on each device, and whether the heater control differs between devices (OPEN-10).
- **Device of the two quarantined files** (OPEN-02). Evidence favours 22482.
- **Clock source of each device.** No offset was detected, but whether device timestamps are wall-clock time is
  not documented.

## 12. Limitations

- Coupling was tested with linear/rank correlation and event coincidence on device-level descriptors. Non-linear
  or channel-specific relationships (e.g. one channel of one mat against one channel of the other) were not tested.
- The analysis view keeps the first of two different rows sharing one second (992 / 1,225 seconds). This affects
  < 0.3 % of rows.
- T/H plausibility masking is descriptive. Sentinel and glitch handling is still open (OPEN-09).
- The clock-offset scan covers constant or day-specific offsets within ±12 h, not drifting clocks within a night.
- Neighbouring-day comparisons for the quarantined files use ±7 days (08-17…08-31).

## 13. Reproduce

```bash
python scripts/build_manifest.py            # verifies raw against the committed manifest
python scripts/audit_user02_devices.py      # writes outputs/qa/p0/user02_devices/
python -m pytest tests/test_device_overlap.py
```
