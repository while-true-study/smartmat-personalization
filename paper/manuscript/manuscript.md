<!--
P8 first pass: architecture skeleton for review. Not prose.
- Evidence notes are bullets. Numbers are source tokens `{{…}}` resolved from paper/tables/ (MANUSCRIPT_NOTES.md).
- Claims follow docs/P8_MANUSCRIPT_PLAN.md §3; tables and figures follow docs/P8_TABLE_FIGURE_SELECTION.md.
- Placeholders in [brackets] are open: citations, PI decisions, publication metadata.
-->

# [TITLE — PI DECISION; candidates in docs/P8_TITLE_CANDIDATES.md]

[AUTHORS AND AFFILIATIONS — PI]

## Abstract

- Context: smart-mat pressure sequences as an unobtrusive source for estimating bed-microclimate temperature and
  humidity [ICFICE CITATION].
- Gap: behaviour on a completely unseen user or domain, and whether a few nights of the user's own data help.
- Methods: three subjects (four mat streams), leakage-controlled strict LOSO, six feature families, chronological
  fine-tuning with 0/1/3/7/14 nights, night-level paired bootstrap.
- Results, one line each:
  - large, subject-dependent level offsets under LOSO;
  - feature families help one target each, without removing the offset;
  - adaptation corrects most of the offset where the early nights represent the later ones;
  - negative transfer where they do not.
- Reproducibility: a de-identified model-ready release candidate reproduces all main results.
- Structured abstract and word limit: [VERIFY AGAINST APPLIED SCIENCES INSTRUCTIONS].

**Keywords:** smart mat; pressure sensing; temperature and humidity estimation; temporal convolutional network;
leave-one-subject-out; domain shift; chronological personalization; negative transfer [FINAL LIST: PI]

## 1. Introduction

- **Problem.** Pressure-based smart bedding can estimate environmental or contact-related quantities without adding
  intrusive sensors [CITE: smart bedding / pressure-mat sensing] [CITE: indirect temperature/humidity estimation].
- **Prior work.** The authors' conference paper showed TCN-based temperature/humidity estimation from pressure
  sequences with movement/contact features [ICFICE CITATION]. What it covered: `docs/P8_CONFERENCE_EXTENSION_MAP.md`.
- **Deployment question.** How does such a model behave for a user and recording domain it has never seen
  [CITE: cross-subject generalization / domain shift]?
- **Strict LOSO answer** (preview of §5.1–§5.2):
  - errors are heterogeneous and dominated by level offsets;
  - representation engineering alone does not remove them.
- **Personalization.** After deployment, a few nights of the target user's data are realistically available
  [CITE: personalization / subject adaptation]. Early nights may not represent later conditions
  [CITE: temporal concept drift], so adaptation can correct an offset or create a new one [CITE: negative transfer].
- **Contributions** (conservative wording; no "first" or "novel" without literature support):
  1. A leakage-controlled strict LOSO evaluation across three held-out subjects under a combined
     subject–period–season–device shift.
  2. A feature-family comparison with target-dependent movement/contact contributions and a persistent
     cross-domain level offset.
  3. A chronological personalization evaluation with 0/1/3/7/14 target-subject nights: large gains and clear
     negative-transfer cases.
  4. Night-level robustness and privacy-preserving reproducibility: paired bootstrap uncertainty, temporal-drift
     sensitivity, device residual diagnostics, and a derived anonymized reproduction package.
- Paper outline.

## 2. Related Work

- 2.1 Smart bedding and pressure-mat sensing [CITE].
- 2.2 Indirect estimation of temperature and humidity from other sensors [CITE].
- 2.3 Temporal convolutional networks for sensor time-series regression [CITE].
- 2.4 Cross-subject generalization and domain shift in wearable/ambient sensing [CITE].
- 2.5 Personalization and subject adaptation; negative transfer [CITE].
- 2.6 Temporal concept drift and calibration / domain-level bias correction [CITE].
- Positioning paragraph: what the present study adds, relative to verified literature only.
- Topics and search status: `RELATED_WORK_GAPS.md`.

## 3. Materials and Methods

### 3.1 Data and cohort

- **Primary cohort** (D-020, D-023):
  - three subjects, `User01`, `User02`, `User07`;
  - four mat streams: User01, User07, and User02's two mats `22480` and `22482`;
  - the two User02 mats record the same person concurrently and are **one subject**; streams are never counted as
    subjects.
- **Confounding** (A11, D-029):
  - the subjects' recording periods do not overlap, so subject, period, season, device and bed microclimate are
    confounded;
  - every held-out fold is a combined unseen-domain shift, not a pure subject effect.
  - Seasons and months: [PI DECISION: may they be named?].
- **Signals:**
  - six pressure channels (12-bit ADC, 0–4095);
  - temperature (°C) and relative humidity (%RH) of the heater-controlled mat microclimate; the heater is
    controlled by firmware (D-038);
  - firmware control codes, never model inputs.
- **Excluded sources** (D-008, D-017, D-023), listed without data:
  - one provider-confirmed invalid source;
  - quarantined files with unresolved device attribution;
  - restricted participant metadata;
  - auxiliary legacy sources not used by protocol v1.0.
- Table 1: `{{TABLE:manuscript_table_1_dataset}}`. Sources: canonical_v1 summary, release manifest, `p3_training_mean_by_fold`,
  `p5_budget_counts`; nights as counts.

### 3.2 Preprocessing (canonical_v1)

- **Raw data** are immutable and checksum-verified (D-005, D-011).
- **Rows:**
  - repeated upload-chunk copies are removed (exact copies only; D-014);
  - sessions follow D-024.
- **Targets:** sentinel and glitch rows are flagged invalid, and their values are kept (D-025).
- **Pressure:**
  - no interpolation, no clipping, and the 4095 saturation value is kept (D-018, D-033);
  - all six channels are used.
- **Phase labels:**
  - User01 `sensor_phase` s1/s2 (D-019);
  - the 22482 channel-quality phase (D-022).
  Both are window boundaries and reporting strata, never inputs (D-035).
- **User02:** the dual-mat representation follows D-027 and D-036.
- Superseded or unexecuted preprocessing ideas are not described.

### 3.3 Windows, inputs and targets

- **Windows** (D-032):
  - 40-s windows of 8 × 5-s bins, stride 20 s;
  - the last observed row per bin, gaps of at most 5 s;
  - a window never crosses a session, device, phase or split partition (splits are made before windowing, L1).
- **Input:** raw pressure / 4095, shape 8 × 6. **Target:** temperature and humidity at the window's last step
  (D-034).
- **Target standardisation** uses training-partition statistics only (L3, L11).
- **Movement and contact features** (D-039): geometry-free, computed from the pressure window; definitions in the
  supplement.

### 3.4 Model

- **Architecture** (D-040): causal residual TCN, 3 blocks (dilations 1, 2, 4), linear head on the last step, 2 outputs;
  MSE on standardised targets.
- **Search space:** 16 configurations; AdamW; early stopping on inner validation only.
- **Seeds:** 0, 1 and 2 for every final model. Results are seed means, with the seed spread shown.

## 4. Experimental Protocol

### 4.1 RQ1 — strict leave-one-subject-out

- **Folds:** 3 outer folds, each holding out one subject entirely (D-031).
- **Nested selection:**
  - two inner splits with swapped train/validation subjects;
  - selection criterion unit-free, inner data only;
  - the outer test is evaluated once.
- **Baselines:** training-mean predictor and RAW-TCN (D-040).
- **Leakage gate** before every run (D-042).

### 4.2 RQ3 — feature-family comparison

- **Families:** RAW, MOVEMENT, CONTACT, RAW+MOVEMENT, RAW+CONTACT, RAW+MOVEMENT+CONTACT.
- **Each family gets its own pre-declared selection** under the same budget (D-044). This is a family comparison, not
  a fixed-hyperparameter ablation.
- **Pre-declared comparisons** A–E (movement or contact added to RAW, …); per subject and seed-paired.

### 4.3 RQ2 — chronological personalization

- **Base model:** the P3 RAW-TCN of the fold that holds the subject out, for the same seed (D-037, D-045).
- **Budgets:** b = 0, 1, 3, 7, 14 nights.
  - Nights 1…b for adaptation, night b + 1 as buffer.
  - **The primary test span is nights ≥ 16 for every budget** (the same test nights). The later span is secondary.
- **Recipe:** fine-tuning of all parameters for 10 epochs at 0.1 × the selected learning rate, batch 256.
  - No validation, no early stopping, no scaler refit.
  - The plan was committed before any adaptation.
- **Adaptation gain:** G_b = (E₀ − E_b)/E₀ with E = MAE, plus bias change and error-SD split (D-045).

### 4.4 Statistical analysis

- **Endpoints:** MAE and RMSE per target; subject-level first. The unweighted mean over three subjects is
  descriptive.
- **Uncertainty** (D-041, D-047):
  - night-level paired cluster bootstrap of ΔMAE (base − adapted), 2,000 resamples;
  - seed 0 primary, 95 % percentile interval;
  - seeds 1 and 2 as sensitivity.
- **Sample size:** windows are never the sample size. With n = 3 subjects there is no population-level inference.
- **Post-hoc analyses** (drift sensitivity, level mismatch, heater context) are labelled as such (D-047 B).

## 5. Results

### 5.1 Strict LOSO generalization

- Table 2: `{{TABLE:manuscript_table_2_loso}}` (source `p3_primary_summary`).
- RAW-TCN temperature MAE per subject, showing heterogeneity:
  - User01 `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | User01 | .3f}}`;
  - User02 `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | User02 | .3f}}`;
  - User07 `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | User07 | .3f}}` °C.
- **Temperature:** RAW-TCN is worse than the training-mean predictor for all three subjects. Unweighted:
  `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | unweighted_subject_mean | .3f}}` vs
  `{{p3_primary_summary | model=training_mean, target=temperature, metric=mae | unweighted_subject_mean | .3f}}` °C.
- **Humidity:** better for User01 and User02, worse for User07.
- **Level offset:**
  - the User02 bias is ≈ −MAE (`{{p3_primary_summary | model=tcn_raw, target=temperature, metric=bias | User02 | +.3f}}` °C);
  - the error is dominated by the domain-level offset.
- The seed spread is much smaller than the spread between subjects (S1).

### 5.2 Feature-family comparison

- Table 3: `{{TABLE:manuscript_table_3_families}}` (sources `p4_primary_summary`, `p4_vs_raw`).
- **Movement → temperature:**
  - MOVEMENT vs RAW `{{p4_vs_raw | family=MOVEMENT, target=temperature, metric=mae | delta_unweighted_mean | +.3f}}` °C;
  - improved subjects `{{p4_vs_raw | family=MOVEMENT, target=temperature, metric=mae | improved_subjects | d}}`/3.
- **Contact → humidity:**
  - RAW+CONTACT vs RAW `{{p4_vs_raw | family=RAW+CONTACT, target=humidity, metric=mae | delta_unweighted_mean | +.3f}}` %RH;
  - improved subjects `{{p4_vs_raw | family=RAW+CONTACT, target=humidity, metric=mae | improved_subjects | d}}`/3.
- **Not additive:** RAW+MOVEMENT+CONTACT ranks
  `{{p4_primary_summary | model=RAW+MOVEMENT+CONTACT, target=temperature, metric=mae | rank_among_tcn_families | s}}`
  (temperature) and
  `{{p4_primary_summary | model=RAW+MOVEMENT+CONTACT, target=humidity, metric=mae | rank_among_tcn_families | s}}`
  (humidity).
- **The offset remains:**
  - no family beats training-mean on the temperature unweighted mean;
  - User02 stays ≈ 100 % offset in every family (S7).
- **Effect sizes** are mostly from User01 and small against the differences between subjects.

### 5.3 Chronological personalization

- Table 4: `{{TABLE:manuscript_table_4_personalization}}`; Figures 2 and 3.
- **Cohort temperature MAE** (unweighted, descriptive), b = 0 → 14:
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=0 | seed_mean | .3f}}` →
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=1 | seed_mean | .3f}}` →
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=3 | seed_mean | .3f}}` →
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=7 | seed_mean | .3f}}` →
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=14 | seed_mean | .3f}}` °C.
- **Cohort humidity MAE**:
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=0 | seed_mean | .3f}}` →
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=1 | seed_mean | .3f}}` →
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=3 | seed_mean | .3f}}` →
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=7 | seed_mean | .3f}}` →
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=14 | seed_mean | .3f}}` %RH.
- **Subject heterogeneity, immediately:**
  - **User02 (offset correction):**
    - temperature G at b = 14 `{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | G_pct | +.1f}}` %;
    - bias `{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_0 | +.3f}}` →
      `{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_b | +.3f}}` °C;
    - humidity improves at every budget.
  - **User07 temperature (negative transfer):** G between
    `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=1 | G_pct | +.1f}}` % and
    `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=14 | G_pct | +.1f}}` %, 0/3 seeds at
    every budget. The bias changes sign.
  - **User01 humidity:**
    - negative transfer at b ≤ 7; b = 3 G `{{p5_adaptation_gain | subject_id=User01, target=humidity, budget_nights=3 | G_pct | +.1f}}` %;
    - recovery at b = 14, G `{{p5_adaptation_gain | subject_id=User01, target=humidity, budget_nights=14 | G_pct | +.1f}}` %.
  - **User01 temperature:** gain from b = 3; unsaturated at b = 14.
- **Error-SD split, descriptive (S9):**
  - User02 temperature is almost purely offset correction;
  - User01 temperature at b = 3/7 is mainly a lower error spread;
  - the User07 temperature loss is a newly introduced offset;
  - humidity changes are dominated by the offset in both directions.
- Few-night adaptation (1–3 nights) does not reliably reduce the error.

### 5.4 Night-level robustness

- Table 5: `{{TABLE:manuscript_table_5_bootstrap}}`; Figure 4.
- **User02 temperature b = 14:** ΔMAE
  `{{p6_bootstrap_mae | subject_id=User02, target=temperature, budget_nights=14 | point_estimate | +.3f}}` °C
  [`{{p6_bootstrap_mae | subject_id=User02, target=temperature, budget_nights=14 | ci_lower | +.3f}}`,
  `{{p6_bootstrap_mae | subject_id=User02, target=temperature, budget_nights=14 | ci_upper | +.3f}}`].
- **User01 temperature:**
  - b = 1 and 3: intervals include zero;
  - b = 7 and 14: above zero.
- **User01 humidity:**
  - b = 1, 3, 7: intervals below zero;
  - b = 14: above zero.
- **User07 temperature:**
  - on the primary span, all three seeds are worse than their base model at every budget;
  - the seed-mean gain stays negative at every evaluable start night (at start night 12, b = 1, one of three seeds
    is positive; `p6_drift_sensitivity`);
  - intervals exclude zero for seed 0 at 4/4 budgets, seed 2 at 2/4, seed 1 at 0/4 (`p6_bootstrap_seed_sensitivity`).
- **Drift sensitivity** (post hoc; S17): no sign change at any evaluable start night 12–21.

### 5.5 Temporal level mismatch (post hoc, descriptive)

- Figure 5 or S-figure: level trajectories (x axis = night ordinal).
- **Rule:** adaptation is expected to help when |adaptation-span mean − primary-span mean| < |base bias|.
- **Agreement:** `{{COUNT:p6_level_mismatch_consistency | consistent=True}}`/24 cells. The exception is User01
  temperature, b = 3.
- **Framing:** an association within three subjects, not a mechanism or a cause.

### 5.6 Device residual (User02)

- **22482 temperature bias at b = 14, seed 0:**
  `{{p6_user02_device_context_bootstrap | stratum=22482, target=temperature, quantity=bias_b14 | point_estimate | +.3f}}` °C
  [`{{p6_user02_device_context_bootstrap | stratum=22482, target=temperature, quantity=bias_b14 | ci_lower | +.3f}}`,
  `{{p6_user02_device_context_bootstrap | stratum=22482, target=temperature, quantity=bias_b14 | ci_upper | +.3f}}`].
- **22480:** `{{p6_user02_device_context_bootstrap | stratum=22480, target=temperature, quantity=bias_b14 | point_estimate | +.3f}}` °C, interval
  includes zero.
- **Across strata:** the residual persists across quality phase and heater context (S18).
- **Framing:** descriptive, not a confirmed device defect. Mat, microclimate and control regime are not separable.

## 6. Discussion

- **A. Level calibration.** Unseen-domain failure here is largely a level-calibration problem, not only temporal
  pattern modelling [CITE: calibration / domain-level bias].
- **B. Different problems.** Feature engineering changes error variation for one target at a time; personalization
  changes the level.
- **C. Not intrinsically beneficial.** Personalization is not beneficial by itself; the same recipe gave the largest
  gain and clear negative transfer.
- **D. Temporal representativeness.** The representativeness of the adaptation nights matters (5.5; descriptive)
  [CITE: temporal concept drift].
- **E. More nights.** More nights can recover performance (User01 humidity at b = 14), depending on subject and
  target.
- **F. Residual.** A device/microclimate residual remains after personalization (22482).
- **G. Practical implication, untested, future work:** adaptation-data selection, drift monitoring, calibration
  safeguards and a bias-only calibration comparator.

## 7. Limitations

- **Cohort:**
  - three independent primary subjects;
  - non-overlapping recording periods;
  - subject, time, season and device confounded;
  - no population-level inference.
- **Adaptation design:**
  - one frozen full fine-tuning recipe;
  - adaptation always uses the earliest recorded nights;
  - within-subject temporal drift affects the result.
- **Confounded labels:**
  - the User01 sensor phase is confounded with time and season;
  - differences between the User02 mats are not causal.
- **Not run:** the 20/30-s window sensitivity, the 4095 sensitivity and a bias-only calibration comparator.
- **Statistics:** the night-level bootstrap does not fully model serial dependence between nights.
- **Release:** the public release is derived and model-ready, not the private raw package.

## 8. Conclusions

- Restate the primary claim with its qualifiers (docs/P8_MANUSCRIPT_PLAN.md §3.1). No new numbers.

## Reproducibility

- **Release:** `public_release_v1` (P7).
  - Three anonymous subjects, four mat streams, 575,265 model-ready windows.
  - Relative time only; absolute dates removed.
- **Checks:**
  - the core tier (P3 → P5 → P6) and the extended tier (P4) pass from a clean checkout;
  - all frozen prediction files are reproduced bitwise, and the nine P3 model weights match their frozen digests;
  - the manuscript source tables are reproduced.
- **Not a complete end-to-end re-run:** the frozen hyperparameter selections were reused, and the inner searches were
  not re-run.

## Data Availability Statement

- See `DATA_AVAILABILITY_DRAFT.md`: [DATA REPOSITORY], [DOI], [LICENSE].

## Code Availability

- See `CODE_AVAILABILITY_DRAFT.md`.

## Institutional Review Board Statement / Informed Consent

- [ETHICS / IRB INFORMATION REQUIRED FROM PI]
- Documented: the data provider confirmed that participant consent was obtained and that the data may be used and
  released for research (D-002). This is not an IRB approval.

## Author Contributions, Funding, Conflicts of Interest

- [PI]

## References

- `references.bib` (verified entries only).

## Supplementary Materials

- Tables S1–S19 and supplementary figures as listed in `docs/P8_TABLE_FIGURE_SELECTION.md`.
