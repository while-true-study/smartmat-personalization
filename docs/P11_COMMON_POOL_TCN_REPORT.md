# P11 — Common-pool RAW-TCN: report (protocol v1.5 addendum, D-066)

> **Post hoc and exploratory.** Designed after every P3–P10 result was known, including the full-pool RAW-TCN on the
> P10 common test endpoints. Plan: `docs/P11_COMMON_POOL_TCN_PLAN.md`; config:
> `configs/experiments/v1.5/p11_common_pool_tcn.yaml`; audit: `docs/p11_common_pool_tcn_audit.md`. No v1.0–v1.4 result
> was changed. N = 3 retrospective cases; no population inference.

## 1. What was run

- The frozen RAW-TCN (40-s RAW input, per-fold configuration of `p3_selected_configs.yaml`, AdamW, batch 256) was
  trained from scratch with the inner-training, inner-validation, outer-training and test windows restricted to the P10
  common endpoints (labelled, with 40-, 300- and 900-s gap-free history). No grid search, no new hyperparameter, no
  900-s sequence input.
- Per fold: inner A and inner B for the frozen configuration (seed 0) → `final_epochs = round_half_up(mean(A, B))`
  (the unchanged v1.0 function `p3_loso.final_epochs`) → final runs with seeds 0, 1, 2; the target scaler was refitted
  on the common training pool; the common test endpoints were predicted once per seed.
- 15 training runs (6 inner, 9 final), 311 s of run time, 362 s wall time in total (RTX 4060 Ti, torch 2.12.0+cu126,
  deterministic algorithms on).
- Histogram boosting and the full-pool RAW-TCN were **read** from the committed P10 / P3 prediction files. Their
  recomputed metrics and the HGB bootstrap rows equal the committed P10 tables to 1e-9.

Command: `python scripts/run_p11_common_pool_tcn.py` (outputs under `outputs/p11_common_pool_tcn/`).

## 2. Common-pool retention (`common_pool_counts.csv`)

| Fold | Held out | Full source endpoints | Common source endpoints | Retention | Common test endpoints (of full) | Test nights (of full) |
| --- | --- | --: | --: | --: | --: | --: |
| 1 | User01 | 284,970 | 136,584 | 47.9 % | 139,735 (289,437) | 137 (151) |
| 2 | User02 | 430,408 | 201,517 | 46.8 % | 74,802 (143,999) | 51 (51) |
| 3 | User07 | 433,436 | 214,537 | 49.5 % | 61,782 (140,971) | 93 (100) |

The common training counts and test counts equal `p10_history_provenance.json`; the test keys and targets equal every
committed P10 prediction file of the fold key-wise and in order.

## 3. Epoch selection (`common_pool_epoch_selection.csv`)

| Fold | Inner A (train → val): best epoch | Inner B: best epoch | Final epochs, common pool | Final epochs, full pool (frozen) |
| --- | --- | --- | --: | --: |
| 1 | User02 → User07: 2 | User07 → User02: 7 | 5 | 5 (from 4, 5) |
| 2 | User01 → User07: 4 | User07 → User01: 1 | 3 | 5 (from 1, 8) |
| 3 | User01 → User02: 4 | User02 → User01: 14 | 9 | 3 (from 2, 3) |

Rule: `round_half_up(mean(inner A, inner B best epoch))`, unchanged. The held-out subject is in no inner run. The inner
best epochs are unstable between the two pools (fold 2 B: 8 → 1; fold 3 B: 3 → 14), which is a property of the
two-subject inner validation, not of P11.

## 4. Main table — MAE on the same common test endpoints (`common_pool_model_comparison.csv`)

Temperature (°C); TCN rows are seed means with the seed range.

| Model | Training pool | User01 | User02 | User07 |
| --- | --- | --: | --: | --: |
| Training mean | common | 2.750 | 4.807 | 2.041 |
| Training median | common | 3.115 | **4.733** | **1.672** |
| RAW-TCN 40 s (new) | common | 2.553 (2.504–2.640) | 5.137 (5.121–5.150) | 2.217 (2.120–2.305) |
| RAW-TCN 40 s (frozen) | full | 2.998 (2.716–3.225) | 5.023 (4.957–5.078) | 2.192 (1.961–2.438) |
| HGB 40 s | common | 2.613 | 5.087 | 2.094 |
| HGB 300 s | common | **2.183** | 5.034 | 1.812 |
| HGB 900 s | common | 2.184 | 4.959 | 1.765 |

Humidity (%RH).

| Model | Training pool | User01 | User02 | User07 |
| --- | --- | --: | --: | --: |
| Training mean | common | 23.65 | 28.76 | **7.92** |
| Training median | common | 22.23 | 29.37 | 8.30 |
| RAW-TCN 40 s (new) | common | 20.45 (19.45–21.42) | 26.96 (26.78–27.12) | 10.68 (10.36–11.02) |
| RAW-TCN 40 s (frozen) | full | 20.38 (19.24–21.35) | **25.93** (25.63–26.50) | 10.33 (10.00–10.79) |
| HGB 40 s | common | 21.44 | 26.81 | 10.31 |
| HGB 300 s | common | 21.35 | 26.75 | 9.74 |
| HGB 900 s | common | **20.21** | 25.98 | 9.59 |

RMSE, bias, R, Q and the correlations are in the CSV files. For the common-pool TCN, R > 1 in every subject and target,
and the night-centred correlations stay small (|r_within_night| ≤ 0.04 for User01 and ≤ 0.08 for User07; User02's
night × mat values are between −0.02 and −0.08): as before, no within-night co-variation is demonstrated.

## 5. Paired night bootstrap (`common_pool_bootstrap.csv`; ΔMAE = MAE(first) − MAE(second), positive = second lower)

Seed 0 (primary), temperature:

| Pair | User01 | User02 | User07 |
| --- | --- | --- | --- |
| mean − TCN-common | +0.110 [−0.046, +0.249] | −0.332 [−0.354, −0.310] | −0.079 [−0.194, +0.028] |
| median − TCN-common | +0.475 [+0.304, +0.626] | −0.406 [−0.428, −0.385] | −0.449 [−0.577, −0.315] |
| TCN-common − HGB-40 | +0.026 [−0.088, +0.135] | +0.052 [+0.028, +0.076] | +0.026 [−0.010, +0.063] |
| HGB-40 − HGB-300 | +0.431 [+0.365, +0.493] | +0.053 [+0.037, +0.069] | +0.282 [+0.203, +0.365] |
| HGB-40 − HGB-900 | +0.430 [+0.326, +0.531] | +0.127 [+0.096, +0.160] | +0.329 [+0.215, +0.454] |
| TCN-full − TCN-common | +0.076 [−0.057, +0.207] | −0.182 [−0.197, −0.167] | −0.159 [−0.207, −0.108] |

Seed 0, humidity:

| Pair | User01 | User02 | User07 |
| --- | --- | --- | --- |
| mean − TCN-common | +3.18 [+2.77, +3.57] | +1.64 [+1.35, +1.94] | −2.44 [−3.29, −1.60] |
| median − TCN-common | +1.77 [+1.42, +2.10] | +2.25 [+1.92, +2.57] | −2.06 [−3.70, −0.43] |
| TCN-common − HGB-40 | −0.98 [−1.45, −0.51] | +0.32 [+0.14, +0.50] | +0.05 [−0.16, +0.25] |
| HGB-40 − HGB-300 | +0.09 [−0.50, +0.65] | +0.06 [−0.17, +0.30] | +0.57 [+0.15, +1.01] |
| HGB-40 − HGB-900 | +1.23 [+0.61, +1.80] | +0.82 [+0.51, +1.13] | +0.73 [+0.19, +1.24] |
| TCN-full − TCN-common | −1.22 [−1.46, −0.97] | −1.46 [−1.61, −1.30] | −0.36 [−0.62, −0.09] |

Seeds 1 and 2 (reported separately, temperature): for **User01** both level-baseline intervals are above zero (mean
−TCN: +0.246 [+0.112, +0.369] and +0.236 [+0.073, +0.384]; median − TCN above zero in both); for User02 and User07
every interval is below zero. TCN-common − HGB-40 changes sign with the seed for User01 (seeds 1, 2 below zero) and is
above zero for User02 and User07 in all seeds.

## 6. Answers

**1. Is the common-pool TCN's temperature MAE below the training mean?**
- User01: yes as a point estimate in all three seeds (seed mean 2.553 vs 2.750); the seed-0 interval includes zero, the
  seed-1 and seed-2 intervals are above zero.
- User02: no (5.137 vs 4.807; interval below zero in every seed).
- User07: no (2.217 vs 2.041; seed 0 includes zero, seeds 1 and 2 below zero).

**2. Below the training median?** User01: yes (2.553 vs 3.115; above zero in every seed). User02: no (vs 4.733).
User07: no (vs 1.672). Both below zero in every seed.

**3. Effect of the training-pool restriction (TCN-common minus TCN-full, seed mean).**

| | User01 | User02 | User07 |
| --- | --: | --: | --: |
| Temperature MAE | −0.445 (per seed −0.076, −0.720, −0.538) | +0.113 (+0.182, +0.115, +0.043) | +0.025 (+0.159, −0.212, +0.127) |
| Humidity MAE | +0.060 (+1.223, +0.853, −1.896) | +1.029 (+1.463, +1.149, +0.476) | +0.348 (+0.362, +0.227, +0.454) |

The restriction lowered User01's temperature error and raised User02's error for both targets; elsewhere the change is
inside the seed range. The per-seed sign is not stable for User01 humidity and User07 temperature. The restriction also
changed the epoch count in two folds (5 → 3, 3 → 9), so this is the effect of the pool **and** of the epoch count the
unchanged rule derives from it; the two cannot be separated without a new experiment.

**4. TCN-40 versus HGB-40 on the same pool.** Temperature: the seed-mean TCN MAE is lower for User01 (2.553 vs 2.613)
and higher for User02 (5.137 vs 5.087) and User07 (2.217 vs 2.094); differences are 0.05–0.12 °C and the User01 sign
depends on the seed. Humidity: TCN lower for User01 (20.45 vs 21.44), higher for User02 (26.96 vs 26.81) and User07
(10.68 vs 10.31). At the same 40-s history and the same pool the two pipelines are close; this is a comparison of two
pipelines on three cases, not evidence of architecture superiority either way.

**5. HGB 40 → 300 → 900 s.** Identical to P10 by construction (the committed predictions were read; the bootstrap rows
equal the committed table to 1e-9): temperature intervals above zero for every subject at 300 s and 900 s; humidity
above zero at 900 s for every subject and at 300 s for User07 only.

**6. Do the manuscript's statements hold?**
- *"The 40-s pressure-only TCN did not consistently exceed simple level baselines."* **Holds.** By the pre-registered
  rule (seed-0 intervals against both the mean and the median above zero) no subject exceeds the level baselines for
  temperature (case A). In the seed sensitivity User01 does (seeds 1, 2), User02 and User07 never do. For humidity two of
  three subjects exceed both constants (case C) — the same pattern the full-pool TCN already showed in P10. Matching
  the training pool therefore did not turn the temperature result around.
- *"Longer pressure history was associated with lower temperature error in some subjects."* **Holds, and is no longer
  confounded by the training pool for the 40-s reference**: with the pool matched, the 40-s TCN (2.553 / 5.137 / 2.217)
  and HGB-40 (2.613 / 5.087 / 2.094) are close, while HGB-300/900 are lower for User01 (2.18) and User07 (1.76–1.81) and
  slightly lower for User02. HGB-900 is still above the training median for User02 and User07.
- *"The absence of pressure information is not demonstrated."* **Holds.** Nothing in P11 supports absence; the
  humidity results and the longer-history results argue against claiming it.

**7. Wording, by case.** The pre-registered outcome is **case A for temperature** (with a seed-dependent User01
exception) and **case C for humidity**.

- *Case A (applies to temperature):* "When the RAW-TCN was retrained on the same common endpoints as the summary models
  (post hoc, exploratory), its temperature MAE was 2.55, 5.14 and 2.22 °C against 2.75, 4.81 and 2.04 °C for the
  common-pool training mean and 3.12, 4.73 and 1.67 °C for the training median. It was lower than both constants only
  for User01, where the night-level interval against the mean included zero for one of three seeds. Matching the
  training pool therefore did not change the finding that the 40-s RAW-TCN did not consistently exceed simple level
  baselines for temperature."
- *Case B (would apply if the seed-1/2 pattern were taken as the criterion):* "… exceeded both level baselines for one
  of three subjects (User01) and neither for User02 and User07; the advantage is subject-specific and the statement of
  no consistent advantage is kept with this qualification."
- *Case C (applies to humidity, unchanged from P10):* "For humidity the common-pool RAW-TCN had a lower MAE than both
  constants for User01 and User02 and a higher MAE for User07, as the full-pool model did."
- Replace the P10 caveat "the RAW-TCN was trained on the full 40-s pool (different training pools, descriptive only)"
  with: "a RAW-TCN retrained on the common pool gave the same qualitative pattern (Table …); the 40-s TCN and the 40-s
  boosting model had similar errors (within 0.05–0.12 °C), so the lower temperature error of the 300-s and 900-s models
  is not explained by the training pool."

## 7. Did the training-pool confound matter?

It moved individual numbers (User01 temperature −0.45 °C, User02 humidity +1.03 %RH) but no qualitative conclusion:
the 40-s TCN still does not consistently exceed the level baselines for temperature, still exceeds them for humidity in
two of three subjects, and longer-history boosting still has the lowest temperature error for User01 and User07. The
manuscript's conclusions need no change; the confound caveat can be replaced by the P11 result.

## 8. Validation (`validation.json`: 73 checks, all passed)

- Subject separation: `pools` fails closed if the held-out subject is in any fitting or selection pool; the frozen v1.0
  gate passed before each of the 15 runs (`leakage_check.json` in every run directory).
- Common endpoints: test keys and targets equal to all 18 committed P10 prediction files (key-wise, order-exact);
  common training and test counts equal to `p10_history_provenance.json`.
- Target scaler: fitted on the two source subjects' common training windows only (`n` equals the common training
  count; the held-out subject is absent from the fit provenance).
- Seeds: three distinct weight digests and distinct predictions per fold; deterministic flags on; epochs run equal the
  frozen P11 selection.
- Regression: HGB, constants and full-pool TCN metrics and the HGB history bootstrap rows equal the committed P10
  tables to 1e-9.
- Existing outputs: SHA-256 of 1,049 files under `outputs/runs/p3`, `outputs/runs/p10`, `outputs/metrics/p3`,
  `outputs/metrics/p10` and `paper/tables` identical before and after.
- Tests: `tests/test_p11_common_pool_tcn.py` (10 tests).

## 9. Limits

- N = 3; within-subject night-level intervals only; no population inference.
- The inner best epochs are unstable between pools, so part of the full-to-common change is an epoch-count change.
- The per-fold configuration was selected on the full pool and kept on purpose.
- The common subset covers 44–52 % of the labelled endpoints and may favour long, stable recordings.
- The interpretation rule uses seed 0; the seed-1/2 intervals for User01 temperature differ from seed 0 and are
  reported rather than resolved.
