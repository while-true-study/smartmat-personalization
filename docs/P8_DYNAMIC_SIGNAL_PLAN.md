# P8 — Final dynamic-signal diagnostic: plan and interpretation map (protocol v1.2 addendum)

> **Status: written before any of the new metrics was computed.**
> - Every output of this addendum records the SHA-256 of this file and of
>   `configs/experiments/v1.2/dynamic_signal_diagnostic.yaml`.
> - Governing decision: D-059.
> - **Second-order post hoc.** The analysis was conceived after the frozen P3–P6 results **and** the v1.1 post-hoc
>   results (calibration comparators, residual-variation ratio, initialization control;
>   `docs/P8_POSTHOC_VALIDATION_REPORT.md`) were known. It is diagnostic, not confirmatory. It is not part of the
>   v1.0 or v1.1 pre-specification and gives no population inference.
> - All results are reported, whichever way they point.
> - **Final planned diagnostic for this manuscript.** After it, no further model experiment is run for this
>   manuscript (§10).

## 1. Question

v1.1 showed that simple level predictors often match or beat the neural models and that the residual-variation ratio
R was about 1 or above. R alone cannot show whether the predictions co-vary with the target: by the identity
R² = 1 + Q² − 2rQ, R ≈ 1 is compatible with a positive correlation r when the prediction scale Q is too large or too
small.

> Do the neural predictions contain useful temporal co-variation with the target that is hidden by offset and/or
> scale mismatch?

## 2. Data and conditions (existing predictions only; nothing is retrained)

- **Span and subjects:** the RQ2 primary span (nights ≥ 16) of User01, User02 and User07. User02's two mats form one
  subject.
- **Targets:** temperature and humidity.
- **Prediction sources:** frozen and read only; the SHA-256 of each file is recorded.
  - **C, RAW-TCN base (seeds 0–2):** the P5 b = 0 run predictions. v1.1 showed they are bitwise identical to base
    inference.
  - **D, bias-calibrated RAW-TCN (b = 1, 3, 7, 14; seeds 0–2):** C plus the frozen v1.1 offset of that subject,
    target, budget and seed (`paper/tables/p8_calibration_by_seed.csv`, column `offset`, calibration `pooled`).
  - **E, full fine-tuning (b = 1, 3, 7, 14; seeds 0–2):** the P5 run predictions.
  - **S, scratch initialization control (b = 14; seeds 0–2):** the v1.1 control-run predictions.
  - **A, training mean, and B, adaptation-target mean:** constant predictors, from the frozen v1.1 constants.
    Reported as R = 1, Q = 0, r = NA.
- **Alignment:** windows are matched by (mat, window start) to the C order, and the observed targets must be
  identical across all sources.

## 3. Metrics

Per subject × target × condition × budget × seed, with e = ŷ − y and population SDs (ddof = 0, the v1.1
convention):
- **R** = SD(e) / SD(y) and **Q** = SD(ŷ) / SD(y).
- **Pooled correlation** r_pooled = the Pearson correlation of ŷ and y over all primary windows.
- **Within-night correlation r_within (primary tracking diagnostic):**
  - subtract each night's own mean from ŷ and from y;
  - concatenate the centred values over all primary nights;
  - compute the Pearson correlation.
  - A night runs from noon to noon, and User02's two mats share a night.
  - A mean of per-night correlations is **not** used as the main statistic.
- **Mat-centred variant r_within_mat (sensitivity):** the same, centred within night × mat.
  - It equals r_within for User01 and User07, which have one stream each.
  - For User02 it removes between-mat level differences inside a night, which are not temporal co-variation.
- **Per-night correlations (supplementary):**
  - eligible nights have at least 10 windows, SD(ŷ) > 1e-12 and SD(y) > 1e-12;
  - report the median of the eligible nights' r, the number of eligible nights, and the numbers excluded for too few
    windows, zero target variance or zero prediction variance.
  - No night is dropped silently.
- **Oracle affine ratio:** R_oracle_affine = √max(0, 1 − r_pooled²).
  - This is the smallest R that an unrestricted affine map a·ŷ + c could reach if it were fitted on the same
    evaluation labels.
  - It is a retrospective oracle diagnostic only. Fitting a and c on test labels would be leakage, so it is not a
    deployable result, not a calibration result and not a performance endpoint.
  - r_pooled² is described only as the squared pooled Pearson correlation, never as explained variance, R² or
    deployment performance.
- **Constant predictions:**
  - a prediction is treated as constant when SD(ŷ) ≤ 1e-12 · max(1, |mean ŷ|); then Q = 0, R = 1, and r and
    R_oracle_affine are NA (never 0);
  - the same rule applies to the centred predictions for r_within.
- **Checks:** a failed check stops the analysis.
  - The identity R² = 1 + Q² − 2·r_pooled·Q holds for every non-constant row within 1e-9.
  - C and D have identical R, Q, r_pooled, r_within and r_within_mat within 1e-9; a constant offset changes none of
    them.
  - The C and E MAE/RMSE/bias reproduce the frozen P5 values.

## 4. Night-level uncertainty

- **Resampling:** the P6/P8 night-cluster bootstrap: `p6_robustness.resample_counts(n_nights, 2000, 0)` over the
  primary nights, with every window of a drawn night kept.
  - One set of resampled nights per subject is shared by every condition and seed, so conditions stay paired.
  - 95 % percentile intervals.
- **Statistics:** r_pooled, r_within and r_within_mat, computed exactly from per-night sufficient statistics (window
  counts, means, centred sums of squares and cross-products) weighted by the resample counts.
- **Paired differences (supplementary):** Δr_within = r_within(E) − r_within(C) at every budget, and
  r_within(S) − r_within(E) at b = 14, on the same resampled nights.
- **Seeds:** seed 0 is primary. Seeds 1 and 2 are sensitivity, reported with their own intervals and sides of zero.
  Seed means and ranges are descriptive.
- **Scope:** no window-level test and no population-level test.

## 5. Operational definitions (fixed before any result)

Per subject × target × condition (and budget), using the seed-mean point estimate and the seed-0 interval:
- **Correlations:**
  - **r positive:** the seed-0 interval lies above 0 and the seed mean is ≥ 0.10;
  - **r negative:** the seed-0 interval lies below 0 and the seed mean is ≤ −0.10;
  - **r ≈ 0:** otherwise. Two sub-labels are reported:
    - "includes zero": the seed-0 interval contains 0;
    - "detectable but small": the interval excludes 0, but |seed mean| < 0.10 or the signs disagree.
  - The 0.10 floor is a pragmatic magnitude threshold (a squared correlation of 1 %), not a significance threshold.
- **User02, within-night rule:** within-night co-variation counts as positive only if both r_within and
  r_within_mat are positive.
- **Q and R:**
  - Q ≈ 0 means Q < 0.10; Q > 0 means Q ≥ 0.10;
  - R ≈ 1 means 0.95 ≤ R ≤ 1.05.
- **Oracle headroom:**
  - R_oracle_affine ≈ 1 means R_oracle_affine ≥ 0.95;
  - headroom means R_oracle_affine ≤ 0.90;
  - values in between are reported as intermediate.

## 6. Interpretation map (fixed before any result; not changed afterwards)

| Case | Condition | Interpretation (wording) |
|---|---|---|
| J1 | Q > 0, r_pooled ≈ 0 and r_within ≈ 0 | "the predictor exhibited nonzero variation but little linear co-variation with the target under this evaluation" (never "only generates noise") |
| J2 | r_pooled positive, r_within ≈ 0 | any pooled association may primarily reflect between-night level or trend alignment rather than within-night tracking |
| J3 | r_pooled positive and r_within positive | evidence that the prediction contains some within-night target co-variation. Remove manuscript wording implying no dynamic information, and use Q and R to explain why MAE/RMSE stay weak |
| J4 | r_pooled negative and/or r_within negative | the learned variation may be misaligned or reversed in the evaluated domain; no causal "inversion" claim |
| J5 | R ≈ 1 and Q ≈ 0 | the output is effectively constant-like in its variation scale |
| J6 | R ≈ 1, Q > 0 and r positive (pooled or within) | some target co-variation exists, but prediction scale and/or other residual structure prevents improvement over a constant residual-variation baseline |
| J7 | R_oracle_affine ≈ 1 | little retrospective linear-calibration headroom |
| J8 | R_oracle_affine ≤ 0.90, in a consistent pattern (the §7 trigger pattern) | the base prediction may contain linearly recoverable structure that bias-only calibration cannot exploit. This does not establish deployable affine-calibration value |
| unmapped | r_within positive but r_pooled not positive | reported as within-night co-variation without pooled association (between-night levels misaligned). For the manuscript wording rule it is treated like J3 |

- **Cells classified:**
  - C (base, b = 0);
  - E at b = 1, 3, 7 and 14;
  - S at b = 14;
  - D carries C's classification (identical statistics).
- **Headline statements** (one per model condition and target):
  - "**within-night co-variation supported**" when r_within is positive (User02: both variants) for at least two
    of the three subjects;
  - otherwise "**only between-night association**" when r_pooled is positive for at least two subjects;
  - otherwise "**little linear co-variation**".
  - The conditions used are C and E at b = 14 (the pre-declared RQ2 models) and S at b = 14.

## 7. Pre-specified affine-calibration trigger

- **Trigger rule, applied to the RAW-TCN base C:**
  - a subject × target cell qualifies if its seed-mean R_oracle_affine ≤ 0.90 **and** at least two of its three
    seeds have R_oracle_affine ≤ 0.90, so that the result is not driven by one isolated seed;
  - the trigger fires if at least two subjects qualify for the same target.
  - This is a pragmatic rule for at least 10 % of retrospective linear residual-SD headroom in a reproducible pattern,
    not a significance threshold.
- **If it does not fire:**
  - no affine calibration is run;
  - the oracle diagnostic is reported;
  - affine calibration may be mentioned as future work.
- **If it fires, exactly one extra comparator is run** (F, "triggered second-order post-hoc comparator"):
  leakage-free adaptation-only affine calibration.
  - **Fit:** per subject, target, seed and b ∈ {1, 3, 7, 14}, ordinary least squares with intercept of
    y = a·ŷ_base + c on the labelled adaptation windows only.
    - The base predictions come from inference with the frozen P3 checkpoint.
    - User02 is fitted over both mats pooled.
  - **Application:** the fixed a and c are applied to the same primary span.
  - **Excluded:** no test label, slope selection, regularisation, clipping or budget selection.
  - **Degenerate case:** if the adaptation predictions have SD ≤ 1e-12 · max(1, |mean|), then a = 0 and
    c = mean(y_adapt), which is the B predictor, and the degeneracy is recorded.
  - **Gates:** every fit passes the v1.0 leakage gate and the v1.1 fit-window checks.
  - **Reported:** F is compared with B, D and E by MAE, RMSE, bias, R, Q, r_pooled and r_within, with night-bootstrap
    ΔMAE for F − B, F − D and F − E (seed 0 primary; seeds 1–2 sensitivity).
  - **Status:** it is not promoted to any primary protocol.

## 8. Language rules

- **R and r:** never infer "R ≈ 1 implies r ≈ 0"; use R² = 1 + Q² − 2rQ.
- **Scope of the negative result:** it is scoped to the tested formulation: the 40-s RAW-pressure representation, the
  TCN architecture and the fixed training and adaptation schedules. Never "pressure cannot estimate microclimate".
- **Temporal-scale mismatch** may be offered only as a plausible, non-causal explanation. The 40-s window captures
  short-term contact and movement, while the mat microclimate may also depend on longer occupancy history, heater and
  controller state, ventilation and other unobserved context.

## 9. Outputs

- **Metrics:** `outputs/metrics/p8_dynamic/`.
- **Runs:** `outputs/runs/p8_dynamic/`, holding the test-access log and, only if the trigger fires, the affine gate
  records.
- **Paper tables** (`scripts/export_p8_dynamic_tables.py`):
  - `paper/tables/p8_dynamic_summary.csv`;
  - `p8_dynamic_by_seed.csv`;
  - `p8_dynamic_bootstrap.csv`;
  - `p8_dynamic_oracle_affine.csv`;
  - `p8_dynamic_cases.csv`;
  - `p8_dynamic_affine.csv`, only if triggered;
  - `p8_dynamic_provenance.json`.
- **Report:** `docs/P8_DYNAMIC_SIGNAL_REPORT.md`.
- **Recorded in every output:** the git commit, protocol version v1.2, the plan and config hashes, the source
  prediction hashes, and the status "post hoc (second order)".

## 10. Stop rule

This is the final planned scientific diagnostic for this manuscript. The only possible extra comparator is the
triggered affine calibration of §7. The following are not added unless a new study phase is explicitly authorized:
- more representations;
- head-only, regularised or rolling-window adaptation;
- longer windows;
- heater inputs;
- new architectures;
- feature search;
- oracle-selected adaptation periods.
