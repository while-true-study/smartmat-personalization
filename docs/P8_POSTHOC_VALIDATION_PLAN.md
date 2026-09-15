# P8 — Post-hoc validation analyses: plan and interpretation map (protocol v1.1 addendum)

> **Status: written before any of these analyses touched the test span.**
> - Every run and table of this addendum records the SHA-256 of this file and of
>   `configs/experiments/v1.1/posthoc_validation.yaml`.
> - Governing decision: D-057.
> - **Post hoc:** conceived after the P3–P6 primary results and the P8 manuscript draft were seen, from a
>   reviewer-style reading of the manuscript.
> - **Supplementary:** the analyses do not replace or supersede any v1.0 primary result. All results are reported,
>   whichever way they point.

## 1. Questions

- **A. Calibration.** Are the gains of full neural fine-tuning more than a correction of a domain-level output offset?
- **B. Residual variation.** Once the level is removed, does the pressure-based model track within-subject target
  variation?
- **C. Initialization.** Is pressure-to-target learning feasible without the subject/domain shift? Does the
  cross-subject pretrained model help relative to training only on the target user's early nights?
- **Heater context.** What do the existing P6 strata show? No recomputation and no new input.

## 2. Fixed design (inherits v1.0 unchanged)

- **Data and windows:**
  - canonical_v1, and the v1.0 split files, verified against `data/splits/v1.0_manifest.json`;
  - the P5 windows (`p5_personalization.subject_windows`), RAW inputs only.
- **Scope:**
  - subjects User01, User02 and User07; User02's two mats form one subject and are pooled (primary);
  - targets: temperature and humidity;
  - budgets b ∈ {0, 1, 3, 7, 14}; adaptation = the earliest b nights; buffer = night b + 1;
  - **primary span = nights ≥ 16**, identical for every budget.
- **Seeds:**
  - neural predictors use seeds 0, 1 and 2; seeds are never added or dropped;
  - the constant predictors are deterministic and get no seed-sensitivity rows.
- **Frozen inputs** (never modified):
  - the P3 selection and checkpoints (`p3-loso-baseline`);
  - the P5 runs and plan (`p5-personalization`);
  - the P3–P6 paper tables.

## 3. Experiment A — calibration comparators

For a predictor f and budget b > 0, per target:

    c_b = mean over the labelled adaptation windows of budget b of (y_i − f(x_i)),        ŷ_cal = f(x) + c_b

No optimisation, no test labels, no scaler refit, no hyperparameter. For b = 0 the offset is not applicable, and the
uncalibrated predictor is kept.

| Label | Predictor | Source |
|---|---|---|
| A | training-mean predictor | P3 outer training-pool mean of the fold (`p3_training_mean_by_fold`) |
| B | training mean + c_b = **mean target of the adaptation windows** (identity checked in code and tests) | adaptation windows |
| C | RAW-TCN base (seed s) | the frozen P3 checkpoint of the fold, by inference; checked bitwise against the P5 b = 0 predictions |
| D | RAW-TCN base + c_b (seed s), with c_b from the base predictions on the adaptation windows | the same checkpoint |
| E | full fine-tuning (seed s) | the frozen P5 runs |

- **User02, primary:** one c_b over the adaptation windows of both mats, applied to both mats. This is the same
  pooling as the full fine-tuning.
- **User02 per-mat diagnostic (supplementary; post-hoc per-device calibration diagnostic added after the primary
  results were known):**
  - for b ∈ {1, 3, 7, 14}, a separate c_b for mat 22480 and for mat 22482, from that mat's adaptation windows only;
  - each mat is evaluated on its own primary windows;
  - predictors: B and D, per mat, next to the pooled B, D and E on the same mat;
  - if a mat has no labelled adaptation window at some b, its per-mat offset is reported as not estimable. There is
    no fallback.
  - It never modifies a primary model or result.

## 4. Experiment B — residual variation

For every predictor and setting:
- MAE, RMSE and bias = mean(ŷ − y);
- target SD = SD(y) and error SD = SD(ŷ − y). Both are **population SDs (ddof = 0)**, the convention of the existing
  error decomposition (`p5_personalization.err_sd`: error SD = √(RMSE² − bias²));
- R = error SD / target SD;
- n_windows and n_nights.

**R is a descriptive residual-variation ratio, not "explained variance".** Identities checked in tests:
- a constant predictor has R = 1;
- a constant offset leaves the error SD unchanged, so A and B have R = 1, and C and D share their error SD.

**Settings:**
- (i) strict LOSO, all labelled windows of the held-out subject (Table 2): training mean and RAW-TCN (seeds);
- (ii) RQ2 primary span: A, B, C, D and E for every budget.

**Reading:**
- R < 1: residual variation below that of a constant predictor;
- R ≈ 1: little evidence of within-subject tracking beyond a constant;
- R > 1: more residual variation than the constant.

## 5. Experiment C — within-subject initialization control (b = 14)

- **Data:**
  - adaptation = nights 1–14; night 15 = buffer (never used); evaluation = nights ≥ 16;
  - User02's mats are grouped as one subject.
- **Arm E (existing):** the cross-subject pretrained RAW-TCN, fine-tuned at b = 14 (P5).
- **Arm S (new):** a RAW-TCN with the fold's source-selected architecture, **randomly initialised** and trained only
  on nights 1–14.
  - Recipe identical to the frozen fine-tuning: AdamW; learning rate 0.1 × the selected base rate; the base weight
    decay; exactly 10 epochs; batch 256; no early stopping; no validation; the base model's target scaler (not
    refit).
  - Only the initialisation differs; the random initialisation and the batch order are seeded by s.
- **Rationale, fixed before any result:**
  - the same data, compute and recipe as E, so the comparison isolates the pretrained initialisation;
  - it is an **initialization control, not an upper bound** on within-subject learnability. A short, low-rate
    schedule may under-train a network started from scratch;
  - no architecture, epoch, learning-rate or feature choice uses nights ≥ 16.
- **Gates:** each run passes the v1.0 leakage gate (personalization context, b = 14), the P5 checks, and two
  addendum checks:
  - every training window lies in nights 1–14 (adaptation partition);
  - no training window lies in night 15 or in a primary-span night.
- **Seeds:** 0, 1 and 2. Report MAE, RMSE, bias, error SD and R per seed and as the seed mean.

## 6. Night-level uncertainty

- **Method:** the P6 paired night-cluster bootstrap (`p6_robustness.resample_counts` / `paired_effects`).
  - Nights, not windows, are resampled; 2,000 resamples; RNG seed 0; 95 % percentile interval.
  - One set of resampled nights per subject is shared by every comparison.
  - Seed 0 is the primary model seed; seeds 1 and 2 give only the side of zero (sensitivity).
- **Comparisons,** each defined as Δ = MAE(first) − MAE(second), so positive means the second is better:
  - per subject × target × b ∈ {1, 3, 7, 14}:
    - D vs E (bias-calibrated RAW-TCN − full FT);
    - B vs E (adaptation-target mean − full FT);
    - B vs D (adaptation-target mean − bias-calibrated RAW-TCN);
  - at b = 14 only:
    - S vs E (scratch − pretrained FT);
    - B vs S (adaptation-target mean − scratch).
- **Scope:** within-subject night-level uncertainty only; n = 3 subjects gives no population-level significance.

## 7. Heater context

- Reuse the frozen P6 strata (`p6_user02_device_context`, `p6_user02_device_context_bootstrap`).
  - They cover User02 by mat, quality phase and heater context (after_AHON / after_AHOF / none within 60 min), with
    MAE and bias at b = 0 and 14, nights and windows.
- No recomputation, and no heater or control state as an input (L9).
- Wording: heater and controller state is an excluded, unobserved contextual factor that may contribute to
  microclimate variation. No causal claim.

## 8. Interpretation map (fixed before reading any result)

**Operational definitions, per subject × target × budget cell:**
- "X better than Y": the seed-0 interval of Δ = MAE(X) − MAE(Y) lies below zero **and** X has the lower seed-mean MAE.
- "X ≈ Y": neither X nor Y is better.
- For a deterministic predictor the seed-mean MAE is its single value.

| Case | Condition (evaluated per cell, summarised as counts) | Consequence for the manuscript |
|---|---|---|
| A | adaptation-target mean (B) seed-mean MAE ≤ full FT (E) | pressure-dependent personalization adds little or no demonstrated value over a personalized constant; the paper may become a negative-result / evaluation paper |
| B | bias-calibrated RAW-TCN (D) ≈ E | most of the personalization benefit is level correction; do not claim that full parameter adaptation is necessary |
| C | E better than D | evidence for adaptation beyond a constant offset |
| D | User07 temperature: D and E both have a higher seed-mean MAE than the base C at a budget | negative transfer is not explained only by fine-tuning dynamics; the adaptation-period level mismatch becomes the stronger descriptive explanation |
| E | User07 temperature: D lower than C but E higher than C at a budget | full-fine-tuning dynamics / over-adaptation are an important alternative explanation, and the story must change |
| F | b = 14: scratch S better than B | pressure carries useful within-domain predictive structure |
| G | b = 14: S not better than B | the pressure-only premise must be substantially weakened. Under this short-schedule control, also check whether E beats B, since E is the other pressure-based within-subject model |
| H | b = 14: E better than S | source-domain pretraining has value under the fixed protocol |
| I | b = 14: S ≈ E or S better than E | cross-subject pretraining gives limited benefit under this control |

- **Reporting:**
  - Case counts over all cells, per subject and target.
  - The primary emphasis for A–C is b = 14 (six cells), with all budgets reported.
  - No result is omitted because it is inconvenient.
- **Manuscript title:** re-evaluated after the results. An evaluation-focused title is favoured if the simple
  baselines dominate.

## 9. Outputs

- Runs: `outputs/runs/p8_posthoc/` (initialization control).
- Metrics: `outputs/metrics/p8_posthoc/`.
- Paper-facing exports (`scripts/export_p8_posthoc_tables.py`) in `paper/tables/`:
  - `p8_calibration_main.csv`, `p8_calibration_by_seed.csv`, `p8_calibration_user02_per_mat.csv`;
  - `p8_residual_variation.csv`, `p8_initialization_control.csv`, `p8_comparator_bootstrap.csv`.
- Report: `docs/P8_POSTHOC_VALIDATION_REPORT.md`.
