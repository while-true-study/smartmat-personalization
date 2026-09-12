# P1 — Domain-shift Exploratory Data Analysis

| | |
|---|---|
| Phase | P1 (`docs/RESEARCH_PROTOCOL.md` §5), branch `research/p1-domain-eda` (from `main` at `10002fc`, tag `p0-data-freeze`) |
| Input | canonical_v1 `primary.parquet` only, verified against `canonical_v1_build.json` before and after the run (primary content `26b970a4edce2bd5…`) |
| Code | `src/evaluation/canonical_input.py` (canonical-only guard), `src/evaluation/domain_shift.py` (slices, descriptors, distances), `src/evaluation/p1_eda.py` (tables), `src/evaluation/p1_figures.py` (figures), `scripts/run_p1_domain_eda.py` |
| Tests | `tests/test_domain_shift.py` (synthetic arrays; guard against raw access) |
| Command | `python scripts/run_p1_domain_eda.py` (≈ 80 s) |
| Outputs | `outputs/eda/p1/` — `domain_slice_summary.csv`, `pressure_distribution.csv`, `target_distribution.csv`, `domain_distance_matrix.csv`, `monthly_distribution.csv`, `time_of_night_summary.csv`, `control_event_summary.csv`, `pressure_target_relation.csv`, `figures/fig1…fig6`, `p1_run_meta.json` (regenerable, not committed) |

Descriptive only. Nothing in P1 does any of the following:
- re-reads or reinterprets raw data;
- changes canonical_v1 or a P0 decision;
- resamples, interpolates, normalises or clips;
- windows, splits, selects features or trains a model.

Invalid targets are left out of target statistics; their prevalence is reported. No row is removed.

## 1. Purpose

Describe how pressure, temperature and humidity change with subject, device, sensor phase, channel-quality phase,
collection period, season, time of night and heater-control context. This gives P2 (protocol and split freeze)
evidence about how far strict LOSO and chronological personalization results can be interpreted. The guiding
constraint throughout: **a cross-subject difference is not a pure subject effect.** The three primary subjects
were never recorded at the same time.

## 2. Dataset and frozen P0 constraints

- **Rows:** 4,136,059 primary rows of User01, User02 and User07 (D-020, D-023).
- **Excluded:**
  - auxiliary sources (User02 legacy, User03 legacy): kept apart (D-023), not read by P1;
  - the User06 source: excluded (D-017), not in canonical_v1.
- **Frozen labels, used as they are:**
  - User01 `sensor_phase` s1/s2 (D-019);
  - the User02 mats 22480 and 22482 as separate streams, never merged (D-027);
  - the 22482 `channel_quality_phase` (D-022);
  - sessions (D-024), target flags (D-025), pressure validity (D-018), timestamps (`local_unspecified`, D-026).
- **Guard.** P1 code cannot reach raw data. The loader accepts only files inside `data/interim/canonical_v1/`,
  refuses protected raw roots, and checks the SHA-256 of every canonical file. A test rejects raw-access
  identifiers in P1 code.

## 3. Domain slices

`domain_slice_summary.csv`. Main analysis unit = the six slices. Pooled subjects are secondary.

| Slice | Rows | Loaded rows | Sessions | Nights | Recording h | Dates | Target-valid rows | Invalid-target share | All-zero share | Rows with a 4095 channel |
|---|---|---|---|---|---|---|---|---|---|---|
| User01/s1 | 1,198,692 | 1,128,534 | 91 | 86 | 988.0 | 2025-08-25 → 2026-01-25 | 1,196,357 | 0.19 % | 5.9 % | 22.1 % |
| User01/s2 | 953,512 | 938,666 | 66 | 65 | 796.4 | 2026-01-25 → 04-02 | 953,435 | 0.01 % | 1.6 % | 0.002 % |
| User02/22480 | 398,464 | 388,196 | 47 | 45 | 332.8 | 2026-07-19 → 09-05 | 398,406 | 0.01 % | 2.6 % | 0.004 % |
| User02/22482/normal | 347,707 | 328,924 | 32 | 28 | 290.5 | 2026-07-19 → 08-19 | 346,254 | 0.42 % | 5.4 % | 0 |
| User02/22482/p1_shift | 229,805 | 207,213 | 25 | 21 | 192.0 | 2026-08-20 → 09-11 | 229,750 | 0.02 % | 9.8 % | 0 |
| User07 | 991,075 | 960,047 | 102 | 100 | 832.8 | 2026-04-03 → 07-19 | 990,929 | 0.01 % | 3.1 % | 0 |
| *User02/22482/p1_transition* | 16,804 | 15,822 | 1 | 1 | 14.0 | 2026-08-19/20 | 16,796 | 0.05 % | 5.8 % | 0 |

- The transition phase (one recording) is reported but not used in the main comparisons.
- The 22482 `p1_shift` slice also contains the later 22482 load/P6 change after 2026-08-25 (A9b). The frozen
  phase does not separate the two.

## 4. Pressure shift

Loaded rows (`pressure_distribution.csv`):

| Slice | Pressure-sum median | IQR | p05–p95 | Active channels (median) | Dominant channel |
|---|---|---|---|---|---|
| User01/s1 | 4,420 | 3,465 | 1,917–10,157 | 2 | P3 58 % |
| User01/s2 | 2,976 | 1,610 | 860–5,022 | 4 | P3 31 %, P2 22.5 % |
| User02/22480 | 1,764 | 1,276 | 244–3,467 | 3 | P3 44 % |
| User02/22482/normal | 2,167 | 1,778 | 35–4,106 | 4 | P5 26 % (even spread) |
| User02/22482/p1_shift | 1,509 | 1,668 | 29–3,427 | 3 | P5 37 %, P4 27 % |
| User07 | 2,037 | 1,328 | 311–3,784 | 3 | P3 42 % |

- **The largest pressure shift is the old User01 sensor (s1) against every other domain.** Pressure-sum W1/IQR is
  1.18–1.37 against the User02 slices and 1.25 against User07, with Cliff's δ = −1.0 on night medians.
- User07 and the User02 mats have almost the same pressure scale: W1/IQR 0.14–0.18 for User07 vs 22480 and
  22482/normal.
- Channel profiles differ by device, not only by person:
  - User01/s1, 22480 and User07 load P3 most;
  - 22482 loads its channels evenly;
  - in 22482's shift phase P1 loses its share (δ −0.61) and P6 falls with the later load change (δ −0.65).
- **Upper-bound sensitivity (descriptive, not a policy).** Without the rows that hold a 4095 value, the
  User01/s1 pressure-sum median moves from 4,420 to 4,077 (IQR 3,465 → 3,352). Every other slice is unchanged
  (≤ 17 affected rows).
- Pooled User01 (median 3,817) hides the s1/s2 step. Pooled 22482 (1,940) hides its normal/shift change. Phase
  slices, not pooled subjects, describe the input domains.

## 5. Target shift

Valid targets only (`target_distribution.csv`); resolution is 1 °C and 1 %RH (8–15 distinct temperatures per
slice).

| Slice | Temperature median (IQR) | Humidity median (IQR) | Night-median range T / H | Within-night IQR T / H (median) |
|---|---|---|---|---|
| User01/s1 | 26 (2) | 25 (13) | 24–29 / 10–73 | 1 / 3 |
| User01/s2 | 25 (2) | 28 (12) | 22–28 / 12–44 | 1 / 4 |
| User02/22480 | 29 (0) | 52 (10) | 28–31 / 28–66 | 0 / 2 |
| User02/22482/normal | 32 (3) | 66 (22) | 28–35 / 38–86 | 1 / 7 |
| User02/22482/p1_shift | 32 (2) | 67 (32) | 30–33 / 27–78 | 1 / 4 |
| User07 | 26 (4) | 39 (15) | 23–30 / 20–56 | 0 / 3 |

- **The largest target shifts are between User01 and User02.**
  - Temperature: User01/s2 vs 22482/p1_shift gives W1/IQR 3.20 (25 vs 32 °C) and δ = +1.0.
  - Humidity: User01/s2 vs 22482/normal gives W1/IQR 2.17 (28 vs 66 %RH) and δ = +0.99.
- **The same person on the same nights reads differently on the two mats.** 22482 is 3 °C warmer (δ 0.69) and
  14 %RH more humid (δ 0.63) than 22480. That is a device or microclimate offset, not a person effect.
- Pooling User02's two mats inflates its within-night humidity IQR to 15 %RH, against 2–7 %RH per mat.
- Invalid targets (D-025) are 0.01–0.42 % per slice. The highest is 22482/normal: 1,306 zero sentinels and 147
  extreme glitches.

## 6. Within-subject/device shift vs between-subject-associated shift

`domain_distance_matrix.csv` holds 18 pairs × 10 variables.
- Row level: W1, KS and W1/IQR. W1/IQR is W1 divided by the pooled IQR, √((IQR_a² + IQR_b²)/2).
- RSD = (median_b − median_a) / √(((IQR_a/1.349)² + (IQR_b/1.349)²)/2).
- Unit level: Cliff's δ on night medians.
- No row-level p-values are used.

| Pair | Pressure sum | Active channels | Temperature | Humidity |
|---|---|---|---|---|
| *within* User01 s1 ↔ s2 | 0.96 / 0.87 | 0.89 / 0.93 | 0.65 / 0.77 | 0.12 / 0.26 |
| *within* 22480 ↔ 22482/normal | 0.60 / 0.24 | 0.51 / 0.20 | 0.69 / 1.10 | 0.63 / 0.86 |
| *within* 22482 normal ↔ p1_shift | 0.71 / 0.29 | 0.69 / 0.38 | 0.08 / 0.27 | 0.14 / 0.25 |
| *between* User01/s2 ↔ User07 (1.5 days apart) | 0.96 / 0.64 | 0.55 / 0.24 | 0.41 / 0.42 | 0.63 / 0.90 |
| *between* 22480 ↔ User07 (0.6 days apart) | 0.43 / 0.18 | 0.03 / 0.03 | 0.83 / 1.00 | 0.65 / 0.90 |
| *between* 22482/normal ↔ User07 | 0.20 / 0.14 | 0.54 / 0.17 | 0.95 / 1.46 | 0.90 / 1.39 |
| *between* User01/s1 ↔ User07 | 1.00 / 1.25 | 0.73 / 0.55 | 0.12 / 0.14 | 0.62 / 1.00 |
| *pooled* User01 ↔ User07 | 0.98 / 1.04 | 0.18 / 0.21 | 0.10 / 0.13 | 0.63 / 0.94 |
| *pooled* User01 ↔ User02 | 1.00 / 1.08 | 0.19 / 0.19 | 0.98 / 1.57 | 0.89 / 1.86 |
| *pooled* User07 ↔ User02 | 0.32 / 0.13 | 0.01 / 0.08 | 0.94 / 1.20 | 0.72 / 1.06 |

Cells are |Cliff's δ| (nights) / W1/IQR (rows).

- **Pressure.** User01's sensor change is as large as the difference between subjects. s1 ↔ s2 gives W1/IQR 0.87,
  against pooled User01 ↔ User07 at 1.04. It is far larger than User07 ↔ User02 (0.13). The pressure scale
  follows the sensor/device, not the person (Figure 4).
- **Targets.** The two User02 mats differ in temperature (W1/IQR 1.10) about as much as User07 and 22480 do
  (1.00). The 22482 response shift barely moves the targets (0.27 / 0.25), as expected for a pressure-channel
  fault.
- Within-subject device/sensor/quality shifts therefore reach the same magnitude as between-subject-associated
  shifts in both pressure and targets. The between-subject distances cannot be attributed to the person.

## 7. Temporal and seasonal confounding

- The primary subjects' nights never overlap (Figure 1): User01 2025-08 → 2026-04, User07 2026-04 → 07, User02
  2026-07 → 09.
- Winter comes only from User01. Summer comes from User07 and User02 (and 6 nights of User01/s1).
- **Monthly target medians form one continuous seasonal curve across the hand-overs** (`monthly_distribution.csv`,
  Figure 5):

| Hand-over | Temperature | Humidity |
|---|---|---|
| April: User01/s2 → User07 | 24 → 24 °C | 40 → 34 %RH |
| July: User07 → User02 | 29 → 29 °C (22480) / 29 °C (22482) | 52 → 58 / 82 %RH |

- Within a subject, the level drifts with the season:
  - User01: humidity 69 %RH in August, 18 %RH in January, 40 %RH in April; temperature 28 → 24 °C.
  - User07: 24 → 29 °C from April to July.
- Much of the between-subject target difference is therefore calendar and season. Subject, season, collection
  period, device and sensor phase change together.

## 8. Time-of-night effects

`time_of_night_summary.csv` uses clock hour (naive local time, no timezone conversion) and hours since the
session start. Deviation of the hourly median from each night's own median, for hours that hold ≥ 1 % of a
slice's rows:
- **Temperature:** −2 to +1 °C, mostly 0.
  - User01/s2: −2 °C at 18 h, +1 °C at 19–21 h.
  - 22482/normal: −1 °C at 20–22 h, +1 °C at 07 h.
- **Humidity:** −5 to +5 %RH.
  - User01/s2 is drier in the early evening (−5 at 19 h).
  - 22482 is more humid at 22 h (+5 normal, +4 shift).
- Rare daytime hours (< 1 % of rows, mostly 10–17 h) deviate more: down to −5 °C, and from −13 to +11 %RH. They
  are too thin to interpret.
- **Occupancy:** 22482 is often empty at 20–21 h (loaded share 0.76–0.78 normal, 0.48–0.51 shift), so those hours
  mix empty-mat frames.
- These effects are small next to the gaps between slices (medians up to 7 °C and 42 %RH apart) and the
  night-to-night spread (night-median IQR 0–4 °C, 10–31 %RH). **Time of night is a secondary, evening-start
  effect.**

## 9. Heating and control context

The vocabulary comes from canonical `event_raw` (`control_event_summary.csv`). Firmware movement labels appear
on almost every row (≤ 0.7 % of rows have none). There are 12,919 control codes in the primary slices:
- in the six main slices: BHSDOWN 7,076; AHOF 1,825; AHON 1,822; BCSUP 1,018; FOF 335; STEMP 209;
- smaller set-point, limit and mode codes (BHNTSDOWN 169, SMINLIMIT 92, …).
- Rates per 100 recording hours: BHSDOWN 150–238 in every main slice; AHON/AHOF from 11.7 (22480) to 107
  (User01/s2).

Event-conditioned results use the nearest valid row of the same stream within ±30 s. Δ = value at the offset minus
value at the event. **No heater state between events is reconstructed.**

| Code (six main slices) | Events | Temperature at event (median) | Δ −30 min | Δ +10 / +30 / +60 min | All-zero share at event |
|---|---|---|---|---|---|
| AHON | 1,822 | 23 °C | +1 °C | +1 / +1 / +1 °C | 5.6 % |
| AHOF | 1,825 | 26 °C | 0 | 0 / 0 / 0 | 4.8 % |
| BHSDOWN | 7,076 | 27 °C | 0 | 0 / 0 / 0 | 0.06 % |
| BCSUP | 1,018 | 24 °C | +1 °C | +1 / +2 / +2 °C | 0.3 % |
| STEMP | 209 | 26 °C | 0 | 0 / +1 / +1 °C | 5.7 % |

- AHON fires after the temperature has fallen: it was 1 °C higher 30 min earlier. It then recovers by +1 °C.
  AHOF fires at a higher temperature, with no median change around it (at 1 °C resolution).
- Events mostly happen on occupied rows. The exception is AHON/AHOF on 22482, with an all-zero share of 22–30 %.
- Event timing depends on the subject. The median AHON/AHOF hour is 4.5–6 h for User01 but 17 h for User07 and
  20 h for User02. BCSUP/STEMP fall at 17–19 h, near session start.
- Temperature at AHON also depends on the domain: 23 °C (User01/s2, User07), 25 °C (User01/s1), 29 °C (User02).
- **The targets are measured inside a controlled microclimate.** The controller reacts to temperature, and the
  control codes are derived from temperature, so they are inadmissible inputs (RESEARCH_PROTOCOL L9).
- A pressure → T/H model will partly face control dynamics rather than physiology alone. Whether heater context is
  a stratifier or a covariate is a P2 question (OPEN-10).

## 10. Pressure–target relationship

`pressure_target_relation.csv` covers loaded rows with valid targets; Spearman ρ at row and night level, plus
decile trends.
- **The relationship is weak at row level:** |ρ| ≤ 0.23 in every slice and pair.
- **It is not consistent across domains at night level.**
  - Pressure sum vs temperature: +0.60 (User01/s2), −0.50 (User07), about 0 (User01/s1, 22480), −0.19/−0.23 (22482).
  - Pressure sum vs humidity: −0.37/−0.45 (User01), +0.34 (22480), +0.23/+0.28 (22482), −0.05 (User07).
- **The within-slice trend is small:**
  - across pressure deciles, the median temperature changes by at most 2 °C (Figure 6), while slice medians differ
    by up to 7 °C;
  - the median humidity changes by 3–9 %RH (14–16 on 22482), while slice medians differ by up to 42 %RH.
- The T/H level is set by the domain (season, device, microclimate), not by pressure within a domain. Any usable
  pressure signal is small and domain-specific.

## 11. Implications for RQ1 / RQ2 / RQ3

**RQ1 (strict LOSO).** Each fold is a domain-generalisation problem, not only a person-generalisation problem.
- The held-out subject brings its own pressure scale: User01's old sensor (s1) has a loaded pressure-sum median
  1.5–2.9× that of the other slices.
- It also brings its own target level (season, device) and its own pressure–target relation.
- Metrics must be read per domain slice, with level offsets in mind.
- Baselines should include the training mean, so that a model's gain over simply predicting a level is visible.

**RQ2 (chronological personalization).**
- User01's time axis crosses s1 → s2 and autumn → winter → spring.
- User07 warms by 5 °C from April to July.
- User02's late period is the 22482 shift phase, and its last 6 days exist only on 22482.
- A personalization gain may partly be adaptation to seasonal or level drift or to a hardware change.
  Adaptation and test spans need domain-aware reporting.

**RQ3 (feature contribution).**
- Contact-structure features are device- and sensor-dependent: active channels median 2 (s1) vs 4 (s2), and a
  different dominant channel per device.
- Firmware movement labels are device-dependent. "left" covers 66–73 % of rows on User01, 22480 and User07; on
  22482 "right" leads (35–42 %) and "absent" is higher (19–25 %). Their admissibility is OPEN-15.
- Feature contributions must be compared within domains, or reported with domain stratification.

## 12. P2 handoff questions (not decided in P1)

1. **Window continuity:** may windows span within-session gaps and 22482 bridged chunk gaps (`gap_before_s`,
   `session_bridged_gap`)?
2. **Window duration candidates:**
   - temperature moves by ≤ 1 °C within a night (IQR 0–1 °C);
   - humidity moves by 2–7 %RH within a night;
   - the largest hourly deviations fall at the evening session start (§8).
3. **Train-only scaling:** per subject, per device, per sensor phase, or global? User01/s1's loaded pressure-sum
   median is 1.5–2.9× that of the other domains.
4. **User02 dual-device use:**
   - the mats differ in targets (3 °C, 14 %RH) and pressure profile;
   - options: separate streams, one mat, or both;
   - no fusion without a protocol decision.
5. **User01 phase-aware reporting/scaling:** the s1 ↔ s2 pressure shift is as large as a between-subject shift.
6. **22482 response-shift handling:**
   - it affects pressure (P1, active channels);
   - it barely affects targets;
   - the phase also contains the later load change.
7. **4095 handling:** it matters for User01/s1 only (22.1 % of rows; median 4,420 vs 4,077 without those rows).
8. **Chronological validation unit:** nights or sessions (both exist; session = D-024).
9. **Personalization adaptation/test boundary** relative to the sensor phase, the channel-quality phase and the
   season.
10. **LOSO metric aggregation:** per subject, per domain slice, with n = 3 folds.
11. **Heater/control context:** stratifier or covariate. It is not an input (L9). OPEN-10.
12. **Domain-aware sensitivity reporting:** which slices (pooled vs phase) are primary in results tables.

## 13. Limitations

- **Sample:** three primary subjects. Subject, period, season, device and sensor phase are confounded. No
  population-level inference is possible.
- **Statistics:** rows are not independent. Row-level statistics are descriptive; the unit-level evidence rests on
  21–100 nights per slice.
- **Target resolution:** 1 °C / 1 %RH, so small effects are quantised.
- **Night and hour definitions** are EDA derivations (noon-to-noon; naive clock time).
- **Control analysis** is event-conditioned only; the heater state is not observed.
- **Slice granularity:** the 22482 `p1_shift` slice mixes the P1 fault with the later load change. The frozen phase
  is kept.
- **Auxiliary sources** are not analysed; the transition phase is too small for comparisons.

## 14. P1 closure assessment

All closure conditions are met:
- Q1–Q8 are answered quantitatively (§4–§10); all required slices were analysed.
- Pressure and target EDA, within-vs-between shifts, temporal/seasonal confounding, time of night, control context
  and pressure–target relationships are done.
- Six figures and eight tables are produced.
- canonical_v1 is unchanged: verified before and after the run.
- Tests pass.

**Figures:**
- Candidates for the paper (not frozen): Figure 1 (coverage timeline) and Figure 4 (within vs between shift).
- QA/supporting: Figures 2, 3, 5 and 6.

P1 is ready to close and hand over to P2.
