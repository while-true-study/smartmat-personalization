# P10 — Level-baseline reproduction, median baselines and pressure-history models: plan (protocol v1.4 addendum, D-064)

> **Status: post-hoc exploratory addendum. Written before any P10 metric was computed.**
> - Authorized by the research lead on 2026-09-18 as a new phase outside the D-059/D-060 stop rule, in response to a
>   mock (not journal) review of the manuscript v1.1. The D-059 and D-060 stop rules stay recorded as history.
> - **Results already seen when this plan was written:** every P3–P9 result (v1.0 primary, v1.1 comparators, v1.2
>   dynamic-signal diagnostic, v1.3 User03 external sensitivity) and the manuscript v1.1. The design below was chosen
>   knowing those results. It is **not** a confirmatory analysis and is never described as originally planned.
> - Machine-readable parameters: `configs/experiments/v1.4/p10_level_baseline_history.yaml`. The SHA-256 of this
>   plan and of that config is recorded in every P10 output. Neither file is edited after the first P10 computation;
>   a correction would be a new, dated addendum section.
> - Nothing in v1.0–v1.3 is edited. Raw data, canonical_v1, splits, configs, models, predictions, tables and tags are
>   read only. P10 writes only under `outputs/runs/p10/`, `outputs/metrics/p10/` and `paper/tables/p10_*`.

## 1. Question and scope

Central question (clarified post hoc):

> How much of the error reduction after personalization is explained by simple level correction, and does pressure
> input contribute beyond that to tracking variation on the later evaluation span?

P10 narrows the scope of the existing negative result and tests alternative explanations. It has three parts, run in
this order:

1. **Reproduction check (R).** Recompute the frozen mean-baseline and neural metrics from canonical_v1, the frozen
   splits and the frozen predictions, and require agreement with the frozen full-precision tables.
2. **Median baselines (M).** Add source-training and adaptation-target medians next to the existing means.
3. **Pressure-summary models with longer history (H).** Ridge and one tree model on pressure summaries over 40-s,
   300-s and 900-s histories under strict LOSO, compared on a common endpoint set with the frozen RAW-TCN and the
   constants.

Out of scope (not added automatically): input-constant ablations, control of optimizer update counts, block
bootstrap, equal night weighting, User02 cross-mat transfer, personalization of the new models, User03 (P10 does not
touch User03 and User03 plays no role in any P10 model selection), new neural architectures, calendar or heater
inputs.

## 2. Frozen inputs and identifiers (verified before use; fail closed)

| Item | Source | Check |
|---|---|---|
| canonical_v1 | `data/interim/canonical_v1/primary.parquet` | `verify_canonical()`; content `26b970a4edce2bd5…`, file `1b34342b9906d288…` equal to the split manifest |
| split files | `data/splits/v1.0_*` | SHA-256 against `data/splits/v1.0_manifest.json` (v1.0 gate, split-level checks) |
| protocol | `configs/experiments/v1.0/protocol.yaml` | SHA-256 `96eeb17e…` |
| P3 selection | `configs/experiments/v1.0/p3_selected_configs.yaml` | P3 `frozen_selection()` |
| P5 plan | `configs/experiments/v1.0/p5_personalization_plan.yaml` | P5 `frozen_plan()` |
| P3 runs | `outputs/runs/p3/training_mean/fold{1,2,3}`, `outputs/runs/p3/final/fold{k}_seed{s}` | `run_status == complete` (artifact SHA-256) |
| P5 runs | `outputs/runs/p5/<subject>/b{bb}_seed{s}` (45 runs) | `run_status == complete` |
| P8 control runs | `outputs/runs/p8_posthoc/init_control/<subject>/b14_seed{s}` (9 runs) | `run_status == complete` |
| frozen tables | `paper/tables/p3_training_mean_by_fold.csv`, `p3_tcn_outer_by_seed.csv`, `p3_primary_summary.csv`, `p5_by_seed.csv`, `p5_budget_counts.csv`, `p8_calibration_by_seed.csv`, `p8_residual_variation.csv`, `p8_interpretation_cases.csv` | SHA-256 recorded |

Every prediction file used is recorded with its SHA-256.

## 3. Part R — reproduction check (before any new metric)

**Tolerance (fixed now, before any comparison).** The existing modules compare recomputed and frozen metrics with
an absolute tolerance of 1e-9 and no relative tolerance (`p8_posthoc.CONSISTENCY_TOL`, `IDENTITY_TOL`; the P3 scaler
check uses `rtol=0, atol=1e-9`). P10 uses **absolute 1e-9, relative 0** for every floating-point metric and constant,
and **exact equality** for keys, targets, window counts, night counts and night sets. The tolerance is never widened
to make a check pass. A failure stops P10 before Parts M and H produce results; the cause is investigated and
recorded.

**Strict LOSO (per fold; Table 2 setting).**
- R1: rebuild the fold windows from canonical_v1 and the frozen outer split (`loso_data.fold_data`).
- R2: labelled training / test window counts equal the frozen training-mean run metadata and
  `p3_training_mean_by_fold.csv`.
- R3: the training mean recomputed from the labelled outer-training windows equals the frozen value.
- R4: the frozen training-mean and RAW-TCN (seeds 0–2) predictions are paired window by window with the recomputed
  test windows on subject, device, session, sensor phase, channel-quality phase, night, window start, window end and
  target timestamp, in both targets (temperature row i and humidity row i describe the same window), and their
  `y_true` equals the recomputed targets exactly.
- R5: MAE, RMSE and bias = mean(prediction − target) recomputed from those pairs equal
  `p3_training_mean_by_fold.csv`, `p3_tcn_outer_by_seed.csv` and `p3_primary_summary.csv` (seed mean, unweighted
  subject mean).

**Personalization, primary span (nights ≥ 16).**
- R6: rebuild the RQ2 windows per subject and budget (`P5Session.windows`); the adaptation nights, buffer night and
  primary-span digest equal the committed P5 plan; labelled adaptation and primary windows and nights equal
  `p5_budget_counts.csv`.
- R7: the adaptation-target mean recomputed from the labelled adaptation windows (User02 pooled over both mats)
  equals `p8_calibration_by_seed.csv` predictor B (as training mean + offset) within tolerance, and the training mean
  equals predictor A.
- R8: base (b = 0) and full fine-tuning predictions (seeds 0–2) from the frozen P5 runs are paired with the
  recomputed primary windows (device, window start, target timestamp; targets equal exactly) and give MAE, RMSE and
  bias equal to `p5_by_seed.csv` and `p8_calibration_by_seed.csv` (C, E).
- R9: the scratch control predictions (P8 runs) reproduce `p8_calibration_by_seed.csv` (S).
- R10: the constants A and B reproduce their MAE, RMSE and bias in `p8_calibration_by_seed.csv`.
- R11: the count "B seed-mean MAE ≤ E seed-mean MAE" recomputed from R8/R10 equals the frozen
  `p8_interpretation_cases.csv` count (12 of 24). **Its definition is recorded as what it is:** a point-estimate
  comparison of the constant's MAE with the seed-mean MAE of fine-tuning. It is not a non-inferiority, equivalence or
  "no difference" test.
- The offset-calibrated base model D is **reused** from `p8_calibration_by_seed.csv`, not recomputed (its offset
  needs a new GPU inference pass whose last bits may differ from the frozen pass).

## 4. Part M — median baselines

Definitions (per target, `numpy.median`; for an even count the mean of the two middle values):
- **Source-training median** (A_med): median of the target over the labelled windows of the outer training pool of
  the fold (the same windows as the frozen training mean A).
- **Adaptation-target median** (B_med, b ∈ {1, 3, 7, 14}): median over the labelled adaptation windows of budget b
  (nights 1…b). User02: one median pooled over both mats, as for B.
- Constants are computed only from those windows. No evaluation-span statistic is ever used as a baseline. They are
  deterministic: one value, no seed repetition.

Evaluation:
- **Strict LOSO, all labelled windows of the held-out subject:** A, A_med, RAW-TCN (seeds 0–2 and seed mean).
- **Personalization, common primary span (nights ≥ 16):** A, A_med, B_b, B_med_b, C (base, seeds), E_b (fine-tuning,
  seeds); D_b and S reused from the frozen v1.1 tables for interpretation.
- Per subject × target (× budget): MAE, RMSE, bias; numbers of fitting windows and nights and of evaluation windows and
  nights. Neural rows are reported per seed and as seed mean ± SD; constants as a single value.
- **Point-estimate counts (descriptive only):** number of cells with constant MAE ≤ neural seed-mean MAE, for A vs
  RAW-TCN (strict LOSO, 6 cells), A_med vs RAW-TCN, A and A_med vs C (primary span, 6 cells), B vs E and B_med vs E
  (24 cells). Each constant is counted separately; the better of the two constants is never chosen per cell.
- No new bootstrap for Part M. Where an interval is needed for interpretation, the frozen v1.1 intervals of B are
  cited; B_med has none.

## 5. Part H — pressure-summary models over longer histories (strict LOSO)

### 5.1 Endpoints and history windows

- **Endpoint:** a v1.0 strict-LOSO 40-s window of a fold: target row = the last row with timestamp < t_end, where
  t_end = t0 + 40 s. The labelled endpoints are exactly the frozen labelled windows (Part R).
- **History H ∈ {40, 300, 900} s:** the interval [t_end − H, t_end), cut into H/5 bins of 5 s. Each step is the **last
  observed row of its bin**, same-second ties resolved by the last row in canonical order (`within_timestamp_order`),
  exactly the v1.0 rule (D-032). For H = 40 the steps are the v1.0 8 × 6 input.
- **Construction:** `windowing.build_windows` with `WindowSpec(duration_s=H, bin_s=5, stride_s=20, max_gap_s=5)` on
  the canonical rows, the group code encoding subject, device, session, sensor phase, channel-quality phase and the
  outer partition. Because 40 − H is a multiple of the 20-s stride for every H, an H-window with start
  t0_H = t_end − H exists exactly when the 40-s window with the same end exists and t_end − H ≥ the start of its
  continuity segment. Each H-window is matched to its 40-s endpoint by group, segment and target row, and
  t0_H + H = t0_40 + 40 is asserted.
- **Continuity:** the v1.0 quality rules are kept unchanged: max gap 5 s between consecutive rows, 4095 kept as
  observed, no interpolation, resampling, filling, clipping or imputation. A history never crosses a subject, mat,
  session, sensor-phase, channel-quality-phase or partition boundary, and never a gap > 5 s. It is never assembled
  from separate 40-s windows.
- **No future information:** every step row has timestamp < t_end; the last step is the target row; no target, flag
  or control field enters a feature.
- **Nights:** as in v1.0 strict LOSO, the noon-to-noon night is not a window boundary (it is one only for RQ2). P10
  adds no night boundary. A history may therefore start before noon when the endpoint is after noon inside one
  gap-free session segment (at most 900 s). This is stated as the only difference from the RQ2 rule and matches
  the frozen LOSO windows.
- **Fold independence:** in strict LOSO a subject's sessions share one partition, so a subject's windows do not depend
  on the fold. Windows are built once per subject and the partition is attached per fold; P10 asserts that the 40-s
  windows built this way equal the frozen fold windows (keys and target rows) for every fold.

### 5.2 Availability, common set and exclusions (fixed before results)

- An endpoint is **available at H** iff its H-window exists (§5.1). H = 40 is available for every endpoint.
- **Common endpoint set:** labelled endpoints available at all three histories. It is computed per subject and is
  identical in every fold.
- **Exclusion reasons**, reported per subject, partition role and H: the continuity segment starts less than H before
  t_end, split by whether that segment starts at the **session start** or after an **intra-session gap > 5 s**. (Phase
  and partition boundaries coincide with session boundaries.) Nothing else excludes an endpoint.
- **Reported counts:** per subject and H: labelled endpoints, available, excluded (by reason); common set; share
  of the original.
- **Every model is trained, validated and evaluated on common endpoints only** (outer training, inner training, inner
  validation and test). The frozen RAW-TCN is re-evaluated on the common test endpoints by key alignment; it was
  trained on the full 40-s pool, which is stated wherever it is compared.
- **Constants on the common test set:** A_orig and A_med_orig (from the full frozen training pool) and A_common and
  A_med_common (from the common training endpoints) are all reported and labelled.

### 5.3 Features (fixed; 42 per history)

For each channel c = P1…P6, on the step values x_k = p_c[k] / 4095, k = 1…K, K = H / 5 (equal weight per 5-s step;
no time weighting beyond the bin rule):

| Feature | Definition |
|---|---|
| `h{H}_p{c}_mean` | mean_k x_k |
| `h{H}_p{c}_std` | population SD (ddof = 0) of x_k |
| `h{H}_p{c}_min` | min_k x_k |
| `h{H}_p{c}_max` | max_k x_k |
| `h{H}_p{c}_last` | x_K (the target row) |
| `h{H}_p{c}_net_change` | x_K − x_1 |
| `h{H}_p{c}_abs_change_sum` | Σ_{k=2..K} \|x_k − x_{k−1}\| (differences between consecutive 5-s steps inside the history only) |

- No cross-channel feature, no total pressure, no active-channel threshold, no centre of pressure or other geometry
  (channel layout unknown, OPEN-20), no calendar, identity, phase, heater, event, target or firmware-label field.
- Interpretation limits written now: a pressure level is a contact proxy, not occupancy or body contact area; a
  pressure SD or change sum is not a count of turns or movements.

### 5.4 Models, grids and selection

| Family | Implementation | Preprocessing (fitted on the training partition of each fit only) | Grid |
|---|---|---|---|
| Ridge | `sklearn.linear_model.Ridge` (multi-output, intercept) | feature standardisation (`StandardScaler`, zero-variance features scaled by 1); target z-score (`TargetScaler`) | alpha ∈ {1e-3, 1e-2, 1e-1, 1, 10, 100, 1000} |
| Tree | `sklearn.ensemble.HistGradientBoostingRegressor`, one model per target | none (raw targets, raw features) | learning_rate 0.1, max_iter 200, early_stopping False, l2_regularization 0, max_bins 255, random_state 0; max_leaf_nodes ∈ {15, 63} × min_samples_leaf ∈ {100, 1000} |

- **Why this tree model:** it is in scikit-learn, which Ridge already needs, so P10 adds one library and no second
  boosting dependency; histogram boosting fits several hundred thousand rows × 42 features in seconds to minutes on
  CPU; with early stopping and row subsampling off it is deterministic for a fixed `random_state` (which only affects
  bin-threshold subsampling above 200,000 rows). It is run once, not over seeds; its determinism is tested (§7).
- **Selection:** per fold × history × family, on the frozen inner splits A and B (train on one training subject,
  validate on the other; common endpoints only). Criterion: the v1.0 unit-free score, mean over A and B of
  (MAE_T / sd_T + MAE_H / sd_H) / 2 with sd from the inner-training partition. Ties: the first configuration in grid
  order. The same configuration serves both targets.
- **Final model:** refit with the selected configuration on the common endpoints of the whole outer training pool;
  the held-out subject's common test endpoints are predicted once (test access logged).
- **Never:** selection or feature choice on the held-out subject; choice of one history by test results (all three
  are reported); the new features passed through the v1.0 RAW allowlist.

### 5.5 Metrics and comparisons (common test endpoints)

- Per held-out subject × target, for Ridge_H and Tree_H (H = 40, 300, 900), RAW-TCN (seeds 0–2, seed mean),
  A_orig, A_med_orig, A_common, A_med_common: MAE, RMSE, bias; R = error SD / target SD, Q = prediction SD / target
  SD, pooled, night-centred and (User02) night × mat-centred correlations (the v1.2 `signal_stats` definitions).
- Night-level paired cluster bootstrap with the frozen P6 settings (2,000 resamples, RNG seed 0, 95 % percentile,
  all windows of a drawn night), Δ = MAE(first) − MAE(second), for these fixed pairs:
  - (A_common, m_H) for each family m and H — positive: the model beats the common-pool training mean;
  - (m_40, m_300) and (m_40, m_900) for each family — positive: the longer history has the lower error;
  - (RAW-TCN seed 0, m_H) for each family and H — descriptive only (different training pools).
- The intervals describe within-subject night-level uncertainty; nights are resampled independently, so serial
  dependence between nights is not fully captured.

### 5.6 Interpretation map (fixed now; applied mechanically)

Per family m, history H, subject s and target t, on the common test set:
- **H-a (beats the level baseline):** the (A_common, m_H) interval lies above zero.
- **H-b (longer history lower error):** the (m_40, m_H) interval lies above zero, H ∈ {300, 900}.
- **H-c (variation beyond level, descriptive):** R < 1, and the night-centred correlation ≥ 0.10, and for User02 also
  the night × mat-centred correlation ≥ 0.10.

Statements (per target):
- If H-a holds in ≥ 2 of 3 subjects for some family and history: "under strict LOSO a simple pressure-summary model
  had a lower error than the source training mean in x/3 held-out subjects; the 40-s RAW-TCN negative result does not
  extend to every pressure model." Otherwise: "the negative result also held for Ridge and histogram-boosting models
  on 40-s, 300-s and 900-s pressure summaries."
- If H-b holds in ≥ 2 of 3 subjects for a family: "longer pressure history was associated with lower error for this
  family." Never "thermal lag", never a causal time constant.
- H-c is reported as descriptive evidence of within-subject co-variation; an MAE gain without H-c is described as a
  level difference.
- A summary model beating the TCN is not evidence that the TCN overfitted; a 40-s TCN versus a 900-s summary model
  difference is not attributed to history length alone (different representation, model family and training pool).
- If every model fails, P10 does not conclude that pressure carries no information.
- N = 3 retrospective cases; no population inference.

## 6. Leakage control: v1.0 gate plus a P10 addendum gate

- The **v1.0 gate** runs with its split-level checks (canonical data, split files, protocol, folds, inner splits,
  personalization chronology, devices together, sources, coverage) before any P10 fit. Its run-level input allowlist
  is not applied to the new features, and the new features are never declared as RAW.
- The **P10 addendum gate** (fail closed; stored as `p10_gate.json` per fold × history) checks:
  1. every feature name is in the P10 allowlist (§5.3) and contains no target, control, calendar or identity token of
     the v1.0 lists;
  2. every history window lies in one group and one gap-free segment (`validate_windows`), with its last step equal
     to the endpoint's target row and t0_H + H = t0_40 + 40;
  3. no step row has a timestamp ≥ t_end;
  4. the 40-s windows built per subject equal the frozen fold windows;
  5. test endpoints belong only to the held-out subject; training, inner-training and inner-validation endpoints never
     do; inner validation uses only a training subject (v1.0 `check_selection`);
  6. every fitted transform and constant (feature standardiser, target scaler, common-pool constants) records
     training-only provenance (v1.0 `check_fits`);
  7. train, inner and test endpoint sets are subsets of the common set, and the common set is identical across the
     three histories;
  8. window boundary labels of first and last steps agree (v1.0 `check_window_groups`).
- **Synthetic tests** (`tests/test_p10_*.py`) cover: bin rule and same-second ties; histories that would cross a
  gap, session or phase boundary are unavailable; endpoint alignment across H; feature values on a hand-computed
  example; perturbing rows at or after t_end leaves features unchanged; exclusion-reason assignment; medians use fit
  windows only; the tolerance comparator; gate failures on a held-out subject in fits or selection, on an unknown
  feature name, and on a history with a future row; determinism of the tree model on synthetic data.

## 7. Environment

- The frozen P3–P9 environment (`requirements.txt`) is unchanged.
- P10 adds scikit-learn 1.8.0 (with scipy 1.17.1, joblib 1.5.3, threadpoolctl 3.6.0), recorded in
  `requirements-p10.txt`. Every P10 output records the package versions and thread settings.
- Part H runs on CPU. Parts R and M need no model inference.

## 8. Outputs and reporting

- `outputs/metrics/p10/`: reproduction check, median tables, availability, selection, metrics, bootstrap, gate reports,
  provenance (plan and config SHA-256, input hashes, git state, environment).
- `outputs/runs/p10/history/`: per fold × history × family selection records and test predictions.
- `paper/tables/p10_*.csv`: exported from the metrics by `scripts/export_p10_tables.py`.
- `docs/P10_LEVEL_BASELINE_HISTORY_REPORT.md`: every result, whichever way it points, with this plan's interpretation
  map; everything labelled post hoc and exploratory.
- The manuscript is revised only after the results pass their checks; sentences that depend on P10 numbers are
  written only then.
