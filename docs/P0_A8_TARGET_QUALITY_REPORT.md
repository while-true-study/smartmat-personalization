# P0-A8 — Temperature / Humidity Target Quality Audit

| | |
|---|---|
| Phase / analysis | P0 — Dataset Audit & Data Freeze / A8 (`docs/P0_DATASET_AUDIT_PLAN.md`) |
| Date | 2026-09-13 |
| Code | `src/data/target_quality.py` (analysis), `scripts/audit_target_quality.py`; reuses the A5 audit view (`upload_copy_mask`), A5 conflict classification (`timestamp_conflicts`), A7 timelines and candidate sessions, and A2 pairing (`pair_rows`) |
| Tests | `tests/test_target_quality.py` (synthetic values and log text only) |
| Command | `python scripts/audit_target_quality.py` (≈ 1 min) |
| Artifacts | `outputs/qa/p0/target_quality/` — `target_quality_summary.csv`, `suspicious_value_patterns.csv`, `suspicious_target_rows.csv`, `zero_dropout_runs.csv`, `target_context_summary.csv`, `target_jump_summary.csv`, `constant_run_summary.csv`, `session_target_summary.csv`, `same_second_target_conflicts.csv`, `target_policy_impact.csv`, `target_distribution_by_device.csv`, `target_daily_medians.csv`, `user02_device_th_bias.csv`, `quality_flag_schema.csv` (regenerable, not committed) |

Evidence only. No target value was replaced, clipped, interpolated, smoothed or deleted. Candidate sessions
(proposed D-015) serve as context labels, not a frozen definition.

## 1. Purpose

Temperature and humidity are the regression targets. Before P0 closes, A8 characterises missing, zero, glitch,
jump and constant-value structure per primary subject/device, so that a target-quality policy can be decided on
evidence (OPEN-09).

## 2. Target coverage

Timeline = A5/A7 audit view (identical upload-chunk copies excluded; nothing else).

| | User01 | 22480 | 22482 | User07 |
|---|---|---|---|---|
| Rows | 2,152,204 | 398,464 | 594,316 | 991,075 |
| Missing / non-finite | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Temperature valid (no zero, inside −10…60 °C) | 99.888 % | 99.985 % | 99.745 % | 99.985 % |
| Humidity valid (no zero, inside 0…100 %RH) | 99.888 % | 99.985 % | 99.745 % | 99.985 % |
| Both valid | 99.888 % | 99.985 % | 99.745 % | 99.985 % |

- Every invalid-candidate row affects both channels at once, including the 22482 glitch rows (§3). No row has
  only one suspicious channel.
- Values are integers: 1 °C and 1 %RH resolution.

## 3. Sentinels and glitches

| Group | Pattern | Rows | % of rows | Period | Dates / files |
|---|---|---|---|---|---|
| User01 | T = 0, H = 0 | 2,412 | 0.112 | 2025-11-05 → 2026-04-01 | 104 / 104 |
| 22480 | T = 0, H = 0 | 58 | 0.015 | 2026-07-19 → 09-04 | 44 / 45 |
| 22482 | T = 0, H = 0 | 1,369 | 0.230 | 2026-07-19 → 09-11 | 48 / 48 |
| 22482 | T = −254, H = 0 | 97 | 0.016 | 2026-08-08 21:55–22:00 | 1 / 1 |
| 22482 | T = 256, H = 152 | 23 | 0.004 | 2026-08-08 22:04–22:05 | 1 / 1 |
| 22482 | T = 215, H = 150 | 15 | 0.003 | 2026-08-09 01:20 | 1 / 1 |
| 22482 | T = 238, H = 262 | 10 | 0.002 | 2026-08-08 22:15–22:16 | 1 / 1 |
| 22482 | T = 171, H = 135 | 2 | 0.000 | 2026-08-08 22:22 | 1 / 1 |
| User07 | T = 0, H = 0 | 146 | 0.015 | 2026-04-03 → 07-18 | 99 / 100 |

Reference sources: quarantined 9, User06 29, User03 legacy 20 joint zeros (User03 ⊂ User06, A1); User02 legacy 0.

**Joint zeros come from two different mechanisms** (runs of consecutive zero rows, `zero_dropout_runs.csv`):

| Group | Start sentinel: short run at a session / chunk / file start | Dropout run: elsewhere | Where the dropout rows are |
|---|---|---|---|
| User01 | 102 runs, 125 rows | 84 runs, 2,287 rows (max 187 rows) | **2,264 on 2025-12-28**, 10:28–15:29 (`phase_b/1228`) |
| 22480 | 47 runs, 51 rows | 6 runs, 7 rows | scattered single rows |
| 22482 | 58 runs, 61 rows | 99 runs, 1,308 rows (max 394 rows) | **1,156 on the night 2026-08-08/09** (`sm22482_0808`), the same night as every extreme glitch |
| User07 | 101 runs, 118 rows | 23 runs, 28 rows | scattered |

- **Start sentinel:** at the first row of a recording (e.g. 81 % of 22480 and 69 % of User07 joint zeros are the
  first row of a candidate session). The rest of the chunk is normal. Where a same-second partner exists, it
  sometimes carries a heater control event (`AHON`; §6).
- **Dropout episodes:** two episodes hold 86 % of all primary-group zero rows (3,420 of 3,985). User01's daytime recording of 2025-12-28 has
  repeated 1–9-minute zero runs (A7 also found interruptions that day). 22482's night of 2026-08-08/09 has zero
  runs interleaved with the only extreme values in the whole dataset (−254, 171–256 °C; 135–262 %RH). Both look
  like sensor/read failures within a limited episode, not systematic offsets.
- A zero is not simply "the first row of every chunk": only 4–7 % of chunk-first rows are zero, against
  0.003–0.22 % of other rows.

## 4. Abrupt jumps

Steps between consecutive **valid** observations (invalid rows skipped, never filled), `target_jump_summary.csv`:

| | Step ≤ 5 s: max \|ΔT\| | ≤ 5 s: \|ΔT\| ≥ 2 °C | ≤ 5 s: max \|ΔH\| | ≤ 5 s: \|ΔH\| ≥ 5 %RH | After gap > 30 min: \|ΔT\| p95 / max | \|ΔH\| p95 / max |
|---|---|---|---|---|---|---|
| User01 | 1 °C | 0 | 5 | 1 | 7 / 8 °C | 18 / 39 %RH |
| 22480 | 1 | 0 | 1 | 0 | 2 / 4 | 10 / 15 |
| 22482 | 2 | 1 | 8 | 2 | 7 / 9 | 25 / 39 |
| User07 | 1 | 0 | 5 | 2 | 3 / 4 | 18 / 27 |

- **Within normal sampling, targets change by at most one quantisation step.** p99.9 is 1 °C / 1 %RH everywhere.
  No isolated spike (jump in and back out within 5 s) exists at any tested size (T ≥ 2 °C, H ≥ 5 %RH).
- Large changes occur only across long gaps (between nights) and are real changes of state, not jumps.
- Once sentinels and glitches are labelled, there is no remaining abrupt-jump problem. A jump rule would only
  matter for future data.

## 5. Constant / low-variance behaviour

| | Unique T values | Most frequent T (share) | Share of recording time in constant-T runs ≥ 1 h / ≥ 3 h | Longest constant-T run | 30-min bins with zero T variance | Session median T std |
|---|---|---|---|---|---|---|
| User01 | 15 | 26 °C (25 %) | 39 % / 6 % | 8.6 h | 37 % | 1.05 |
| 22480 | 8 | **29 °C (63 %)** | **84 % / 58 %** | 10.5 h (29 °C) | 78 % | 0.36 |
| 22482 | 13 | 32 °C (26 %) | 49 % / 17 % | 6.2 h | 47 % | 0.84 |
| User07 | 11 | 24 °C (24 %) | **80 % / 54 %** | 11.8 h (27 °C) | 73 % | 0.45 |

- **22480:** 96.4 % of valid temperatures lie in 28–30 °C. 43 of 47 candidate sessions have ≥ 95 % of their rows in
  that band, and the median within-session temperature range is 1 °C. This holds throughout July–September
  (monthly median 29 °C, IQR 0–1).
- **User07 shows the same long constant runs**, so this is not unique to 22480.
- **Sensor-freeze check:** during constant-temperature runs of ≥ 3 h, the humidity of the same record still moves
  (median humidity range within the run 3–6.5 %RH; ≥ 2 %RH in 29/33 runs for 22480 and 73/81 for User07). A frozen sensor is
  therefore unlikely. The data fit 1 °C quantisation of a stable, possibly heater-regulated microclimate. They do
  not distinguish environment stability from control-loop regulation; heater-control event rates are similar
  (22480 2.2 / h, 22482 2.6 / h).
- Humidity is far less constant (share of time in runs ≥ 1 h: 4–41 %).

## 6. Same-second target conflicts

Of the 10,997 same-second conflicts found by A5 in the primary groups, **148 involve the targets**:

| Class | User01 | 22480 | 22482 | User07 | Total |
|---|---|---|---|---|---|
| Humidity only (±1 %RH) | 38 | 8 | 21 | 26 | 93 |
| Temperature only (±1 °C) | 9 | 0 | 0 | 5 | 14 |
| Both differ, no sentinel (±1 each) | 6 | 1 | 0 | 5 | 12 |
| Both differ, one side T = H = 0 | 11 | 4 | 8 | 6 | 29 |
| …of all 148: same second as a control event | 15 | 0 | 1 | 4 | 20 |
| …of all 148: pressure also differs | 63 | 13 | 27 | 40 | 143 |

- **The 119 non-sentinel conflicts differ by exactly one quantisation step.** They are two readings taken in the
  same second on either side of an integer boundary.
- The 29 sentinel conflicts pair a zero row with a real reading. 13 of them share their second with a heater
  control-event line (`AHON`).
- None is a copy. All are preserved; a canonical representation must keep both rows, their order and their
  provenance (`same_second_target_conflicts.csv`).

## 7. Policy sensitivity (simulation; nothing changed)

Primary groups, audit timeline, 4,136,059 rows, 364 candidate sessions:

| Hypothetical policy | Invalid-target rows | % | Usable rows (both targets) | Sessions touched |
|---|---|---|---|---|
| A — joint zero (T = H = 0) | 3,985 | 0.096 % | 4,132,074 | 311 |
| B — A + known extreme glitches (incl. the paired H = 0) | 4,132 | 0.100 % | 4,131,927 | 311 |
| C — B + abrupt-jump candidates (ΔT ≥ 3 °C or ΔH ≥ 10 %RH within 5 s) | 4,132 | 0.100 % | 4,131,927 | 311 |

Per group under B: User01 0.112 %, 22480 0.015 %, 22482 0.255 %, User07 0.015 %. Many sessions are "touched",
but usually only by their first row (start sentinel). C adds nothing at these thresholds (§4), and it remains a
threshold-dependent sensitivity, not a candidate rule.

## 8. Target distributions (input for P1)

Policy-B-valid values, `target_distribution_by_device.csv`:

| | T median (IQR) | T range | H median (IQR) | H range | Monthly T median | Monthly H median |
|---|---|---|---|---|---|---|
| User01 | 26 (3) °C | 17–31 | 26 (13) %RH | 6–80 | 28 (Aug) → 24 (Mar/Apr) | 69 (Aug) → 17 (Jan) → 40 (Apr) |
| 22480 | 29 (0) | 27–34 | 52 (10) | 27–68 | 29 throughout | 58 → 50 → 51 |
| 22482 | 32 (3) | 26–38 | 66 (23) | 22–95 | 29 → 32 → 31 | 82 → 65 → 42 |
| User07 | 26 (4) | 21–31 | 39 (15) | 9–82 | 24 (Apr) → 29 (Jul) | 34 → 41 → 34 → 52 |

- User02's device relation is reproduced on the audit view: 22480 − 22482 = −2.0 °C, −19.0 %RH (r 0.27 / 0.72;
  A2: −2 / −19).
- Target levels and spread differ strongly by subject, device and month. Because every subject was recorded in a
  different season on different hardware, **subject, season, device and heater regime are confounded**. This is
  described, not separated, and is passed to P1.

## 9. Impact on P0

- **Target corruption is rare and structured:** 0.10 % of primary rows. It consists of start sentinels, two
  dropout/glitch episodes and one-step same-second differences. It does not bias the targets broadly.
- A **cause-preserving flag schema** is feasible, and each suspicious row is identifiable by
  (source file, line, chunk key) (`quality_flag_schema.csv`):
  - per-channel state (`valid | missing | non_finite | zero | extreme_low | extreme_high`);
  - `target_zero_sentinel` and `target_extreme_glitch`;
  - zero-run class (`start_sentinel` / `dropout_run`) and chunk position;
  - `target_*_jump_abs` with previous-valid Δt (magnitudes, not decisions);
  - constant-run length;
  - same-second group id.
- **Proposed (D-016):** flag the known sentinel and glitch patterns as invalid targets, keeping raw values.
- **Low-variance targets** (22480, User07) are a property of the data, not corruption. They affect how informative
  the target is per device and feed into OPEN-10 (target definition under heater control) and P1/P2.

## 10. Unresolved

- Whether to exclude **whole episodes** (User01 2025-12-28 daytime; 22482 night 2026-08-08/09) beyond the flagged
  rows. The valid rows inside them may also be unreliable. Not decided.
- **Jump thresholds, clipping, interpolation or smoothing:** none decided. None is needed for the current data;
  any rule belongs to P2.
- **Representation of same-second target pairs** (keep both, order, or choose one per window) — P2, with D-014/D-015.
- **Cause of constant temperature** (quantisation of a stable environment vs heater regulation) and whether the
  target of heater-regulated periods is scientifically meaningful — OPEN-10, provider question on sensor placement
  and control mode.
- **Device calibration:** the 22480/22482 humidity offset is persistent but not attributed to calibration.

## 11. Reproduce

```bash
python scripts/build_manifest.py
python scripts/audit_target_quality.py     # writes outputs/qa/p0/target_quality/
python -m pytest tests/test_target_quality.py
```
