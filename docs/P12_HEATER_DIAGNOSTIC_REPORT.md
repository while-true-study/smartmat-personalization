# P12 — Heater-context confound diagnostic: report (protocol v1.6 addendum, D-067)

> **Post hoc and descriptive.** Designed after every P3–P11 result was known. Plan:
> `docs/P12_HEATER_DIAGNOSTIC_PLAN.md`; config: `configs/experiments/v1.6/p12_heater_diagnostic.yaml`; audit:
> `docs/P12_HEATER_DIAGNOSTIC_AUDIT.md`. No model was fitted; no heater or control field entered any predictive model;
> no v1.0–v1.5 result was changed. The heater-conditioned constant runs under the D-067 diagnostic-only exception to
> D-038 and is **not** an estimator: control codes are derived from temperature. No causal heater effect is claimed.
> N = 3 retrospective cases. Local only; nothing was pushed.

## 1. What was run

- Heater context: the D-047 A.2 definition reused unchanged (`p6_robustness.heater_events` / `heater_context`) — the
  most recent AHON/AHOF on the same mat with event time ≤ target time and within 60 min; otherwise `UNKNOWN`. Event
  tables per subject. `ON`/`OFF` name the last code, not a reconstructed heater state.
- Windows: the frozen labelled 40-s windows. Spans reported separately: **full** (strict-LOSO test span) and **common**
  (the P10/P11 common endpoints).
- Plan/config hashes were written to `pre_result_design_hashes.json` before the first statistic and equal the values in
  `provenance.json`. Run time 63 s, CPU only. Command: `python scripts/run_p12_heater_diagnostic.py`.

## 2. Heater code audit (`heater_code_audit.csv`)

Only AHON and AHOF define the context. Events; nights with the code / nights of the stream:

| Code | User01 | User02 22480 | User02 22482 | User07 |
| --- | --- | --- | --- | --- |
| AHON (heater ON, documented) | 1,395; 139/151 | 39; 33/45 | 122; 44/50 | 271; 90/100 |
| AHOF (heater OFF, documented) | 1,408; 140/151 | 39; 33/45 | 117; 44/50 | 266; 83/100 |

BHSDOWN (set-point, documented; 7,112 events) and FOH (forced off, documented; 4 events) are not used. BCSUP, STEMP,
SLIMIT, SMINLIMIT, BHNTSDOWN (set-point/limit), FON/FOF/FORCED_ON/FORCED_OFF/MON/MOF/AIHON/AIHOFF (heating-related
on/off) and AMODE/MMODE/AIDONE/SCHATIDS/WSTOP (controller/mode) are classified by name only and marked ambiguous; none
was reinterpreted or added. FOF (335 events) may hide heater-off actions the definition does not see.

## 3. Coverage (`heater_context_counts.csv`)

Share of windows per state, full span (common span in brackets):

| Subject | ON | OFF | UNKNOWN |
| --- | --: | --: | --: |
| User01 | 13.0 % (11.7 %) | 39.2 % (39.9 %) | 47.8 % (48.4 %) |
| User02 (both mats) | 0.03 % (0.01 %) — 36 windows | 13.4 % (11.8 %) | 86.6 % (88.2 %) |
| — 22480 | 0 windows | 10.9 % | 89.1 % |
| — 22482 | 36 windows | 15.1 % | 84.9 % |
| User07 | 3.6 % (2.6 %) | 16.5 % (16.7 %) | 79.9 % (80.6 %) |

Coverage is very uneven: for User02 the `ON` state is practically empty and 87 % of windows have no context, so every
User02 statement below rests on `OFF` versus `UNKNOWN`. Look-backs that reach an event before the session's first window:
User01 1,789 `ON` windows, User02 491 `OFF`, User07 589 `ON` + 448 `OFF` (kept, as in D-047).

Target level by state, full span (mean; `heater_target_summary.csv`):

| Subject | Temperature ON / OFF / UNKNOWN (°C) | Humidity ON / OFF / UNKNOWN (%RH) |
| --- | --- | --- |
| User01 | 24.39 / 25.83 / 26.17 | 26.6 / 27.8 / 25.6 |
| User02 | 30.61 (n = 36) / 30.25 / 30.60 | 62.6 (n = 36) / 61.4 / 57.7 |
| User07 | 24.18 / 26.31 / 26.38 | 34.6 / 36.3 / 40.0 |

Windows after an AHON are 1.4–2.2 °C colder than the others for User01 and User07 — the direction expected from a
controller that switches the heater on after the temperature has fallen (P1 §9).

## 4. η²: proportion of observed target variance associated with heater context (`heater_eta_squared.csv`)

Three states, night-cluster 95 % interval. Full span (common span in brackets).

| Subject | Target | A1 raw | A2 night-centred | A3 night × mat-centred | Case |
| --- | --- | --- | --- | --- | --- |
| User01 | temperature | 0.103 [0.074, 0.150] (0.100) | **0.152** [0.130, 0.177] (0.113) | – | **C** |
| User01 | humidity | 0.010 [0.001, 0.041] (0.001) | 0.008 [0.002, 0.019] (0.005) | – | A |
| User02 | temperature | 0.004 [0.000, 0.013] (0.002) | 0.007 [0.001, 0.018] (0.003) | 0.041 [0.017, 0.080] (0.029) | A |
| User02 | humidity | 0.008 [0.001, 0.022] (0.005) | 0.014 [0.003, 0.034] (0.009) | 0.023 [0.009, 0.047] (0.009) | A |
| User07 | temperature | 0.047 [0.035, 0.065] (0.020) | **0.108** [0.058, 0.167] (0.123) | – | **C** |
| User07 | humidity | 0.030 [0.012, 0.056] (0.029) | 0.050 [0.027, 0.079] (0.059) | – | A |

`ON`/`OFF` windows only (full span): temperature 0.175 raw / 0.232 night-centred for User01, 0.227 / 0.090 for User07,
≈ 0 for User02; humidity ≤ 0.005 everywhere.

- Temperature: a medium-to-large association for User01 and User07 that does **not** shrink under night-centring — it
  grows (0.103 → 0.152; 0.047 → 0.108). The association is therefore mainly within-night, not a night- or domain-level
  artefact (case C, not case B). For User02 it is small in every variant, including the night × mat-centred one
  (0.041), with `ON` practically unobserved.
- Humidity: small for every subject and variant (case A); User07's night-centred value (0.050 full, 0.059 common) sits at
  the threshold.

## 5. Heater-conditioned source constant (diagnostic comparator; `heater_constant_metrics_*.csv`)

MAE; the held-out subject is in no fit. Source mean and median equal the committed P10 (full) and P11 (common) tables to
1e-9.

| Span | Subject | Target | Source mean | Source median | Heater-conditioned mean | ΔMAE (mean − conditioned) [95 %] |
| --- | --- | --- | --: | --: | --: | --- |
| full | User01 | temperature | 2.735 | 3.220 | **2.232** | +0.503 [+0.453, +0.556] |
| full | User02 | temperature | 4.592 | 4.555 | 4.599 | −0.008 [−0.009, −0.006] |
| full | User07 | temperature | 1.815 | 1.659 | 1.682 | +0.133 [+0.083, +0.186] |
| full | User01 | humidity | 23.06 | 21.34 | **20.96** | +2.10 [+1.88, +2.33] |
| full | User02 | humidity | 27.63 | 28.31 | 27.82 | −0.19 [−0.22, −0.16] |
| full | User07 | humidity | 7.99 | 9.39 | 8.10 | −0.11 [−0.32, +0.11] |
| common | User01 | temperature | 2.750 | 3.115 | **2.203** | +0.547 [+0.480, +0.618] |
| common | User02 | temperature | 4.807 | 4.733 | 4.823 | −0.015 [−0.019, −0.012] |
| common | User07 | temperature | 2.041 | 1.672 | 1.874 | +0.167 [+0.112, +0.222] |
| common | User01 | humidity | 23.65 | 22.23 | **21.20** | +2.45 [+2.14, +2.78] |
| common | User02 | humidity | 28.76 | 29.37 | 29.01 | −0.24 [−0.30, −0.19] |
| common | User07 | humidity | 7.92 | 8.30 | 7.80 | +0.12 [−0.18, +0.41] |

The heater-conditioned constant has a lower MAE than the source mean for User01 (both targets) and User07 temperature,
a slightly higher one for User02, and no distinguishable difference for User07 humidity. Against the source **median**
it is lower for User01 but not for User07 temperature (common span: −0.203 [−0.277, −0.124], i.e. the median is lower).

**Caveat that limits this comparator.** Conditioning on heater state also changes which source subject the constant
comes from, because coverage differs between subjects. In fold 1 (source User02 + User07) the `ON` windows are 99 %
User07, `OFF` 55 %, `UNKNOWN` 47 %; in fold 3 (source User01 + User02) `ON` is 99.9 % User01, `OFF` 85 %, `UNKNOWN`
53 %. Since User02's level is far from the others (≈ 30.5 °C, ≈ 58 %RH), part of the gain for User01 and User07 is a
source-subject mixture effect, not heater context. User01 humidity shows it: η² is 0.001–0.010 yet the constant gains
2.1–2.4 %RH. The comparator cannot separate the two.

## 6. Longer-history gain by heater state (supplementary; common span; `heater_history_gain_by_context.csv`)

Temperature MAE from the committed P10/P11 predictions:

| Subject | State | Windows | Training mean | HGB 40 s | HGB 900 s | TCN-common | mean − HGB-900 |
| --- | --- | --: | --: | --: | --: | --: | --: |
| User01 | ON | 16,370 | 3.958 | 3.205 | 2.536 | 3.196 | **+1.422** |
| User01 | OFF | 55,713 | 2.823 | 2.491 | 1.900 | 2.467 | **+0.923** |
| User01 | UNKNOWN | 67,652 | 2.398 | 2.571 | 2.332 | 2.467 | +0.065 |
| User07 | ON | 1,637 | 3.117 | 2.466 | 2.207 | 2.750 | +0.910 |
| User07 | OFF | 10,323 | 1.904 | 1.957 | 1.577 | 2.083 | +0.327 |
| User07 | UNKNOWN | 49,822 | 2.034 | 2.110 | 1.789 | 2.227 | +0.245 |
| User02 | OFF | 8,858 | 4.606 | 4.823 | 4.707 | 4.918 | −0.101 |
| User02 | UNKNOWN | 65,938 | 4.834 | 5.122 | 4.993 | 5.166 | −0.159 |

For User01 almost the whole advantage of HGB-900 over the training mean sits in the windows with a recent heater code
(+1.42 and +0.92 °C) and nearly none in `UNKNOWN` windows (+0.07 °C). For User07 the advantage is largest after an AHON
but is present in every state. The 40 s → 900 s improvement itself (HGB-40 − HGB-900) appears in all states
(User01 0.67 / 0.59 / 0.24; User07 0.26 / 0.38 / 0.32; User02 0.12–0.23).

## 7. Answers

1. **Temperature and heater context.** User01: η² 0.10 raw, 0.15 night-centred (medium/large). User07: 0.05 raw, 0.11
   night-centred (small/medium). User02: ≤ 0.007, 0.041 after night × mat centring (small), with `ON` unobserved.
2. **Humidity.** Small everywhere (≤ 0.03 raw, ≤ 0.05 night-centred on the full span).
3. **Raw versus night-centred.** Centring does not reduce the association; for temperature it increases it (User01
   +0.05, User07 +0.06). Case B (night/domain entanglement) applies to no subject–target pair; cases: temperature C, A, C
   and humidity A, A, A for User01, User02, User07.
4. **User02 after night × mat centring.** 0.041 [0.017, 0.080] for temperature and 0.023 [0.009, 0.047] for humidity on
   the full span (0.029 and 0.009 on the common span): small, case A.
5. **Heater-conditioned constant versus the source mean.** Lower MAE for User01 temperature (−0.50 / −0.55 °C) and
   humidity (−2.1 / −2.4 %RH) and User07 temperature (−0.13 / −0.17 °C); slightly higher for User02; not distinguishable
   for User07 humidity. Part of this is a source-subject mixture effect (§5).
6. **Competing explanation for the P10 300/900-s improvement** (pre-registered rule, the four pairs where HGB-900 beat
   the training mean): **plausible** for User01 temperature (heater gain 0.547 vs HGB-900 gain 0.566), User01 humidity
   (2.45 vs 3.43) and User07 temperature (0.167 vs 0.276); **not supported** for User02 humidity (−0.24 vs +2.78, η²
   small). For User01 temperature a two-level constant keyed on the last heater code reaches the error of the 900-s
   boosting model (2.203 vs 2.184 °C), and the boosting gain is concentrated in windows with a recent heater code (§6).
7. **Can the mechanisms be separated?** No. **These mechanisms cannot be separated with the present observational
   data.** (A) sustained contact/load history acting as a proxy for slower thermal and moisture dynamics and (B)
   pressure/contact history co-varying with heater, controller and environment context predict the same pattern here;
   the control codes are themselves derived from temperature, heater context is confounded with occupancy, time of night
   and source-subject mixture, and there is no intervention on the heater.

## 8. What this means for P10 and P11

- P10's statement that longer pressure history "was associated with lower temperature error" stays a statement of
  association, and P12 adds that, for User01 and User07, heater/controller context is a plausible competing explanation
  of comparable size. P10/D-065 already excluded "thermal lag" and "occupancy effects" as claims; P12 gives a concrete
  reason to keep excluding them.
- This is evidence against reading the 300/900-s result as information carried by pressure history as such. It is not
  evidence that pressure history carries none: the 40 → 900 s improvement appears in every heater state, including
  `UNKNOWN`, and User02's humidity gain is not accounted for by heater context.
- P11's conclusion (the 40-s RAW-TCN does not consistently exceed the level baselines for temperature) is unaffected.
- The heater-conditioned constant is not a usable baseline: it consumes target-derived controller output (L9).

## 9. Validation (`validation.json`: 30 checks, all passed)

Look-up consistent with the frozen function; no future event and ≤ 60 min for every labelled window; `UNKNOWN` windows
receive the source overall mean; constants fitted on the source training windows only (fails closed otherwise); common
endpoints key- and target-equal to the nine committed P11 prediction files and the P10 HGB files; source mean/median
equal to the committed P10/P11 tables (1e-9); plan/config hashes equal to the pre-result record; 1,194 files under
`outputs/runs/p3`, `outputs/runs/p10`, `outputs/metrics/p3`, `outputs/metrics/p10`, `outputs/p11_common_pool_tcn` and
`paper/tables` unchanged; a second run in another output root gave 11 byte-identical tables. Tests:
`tests/test_p12_heater_diagnostic.py` (14); full suite 457 passed.

## 10. Limits

- Only AHON/AHOF define the context; 48–88 % of windows are `UNKNOWN`, and `ON` is practically absent for User02.
- Control codes are temperature-derived, so an association with temperature is partly built in.
- The heater-conditioned constant mixes heater context with source-subject composition (§5).
- η² thresholds (0.06, 0.14) are conventions fixed in advance, not tests. Intervals are within-subject night-level.
- N = 3; no population inference; no causal claim. No new model family follows P12.
