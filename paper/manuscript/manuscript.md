<!--
P8 second pass: first prose draft (sections 1, 3–7), Related Work as structure + topic sentences + placeholders.
- Numbers from results are source tokens {{…}} resolved from paper/tables/ (MANUSCRIPT_NOTES.md). Design parameters
  of the frozen protocol (window length, budgets, resample counts, cohort size) are written as text.
- Claims follow docs/P8_MANUSCRIPT_PLAN.md §3; tables and figures follow docs/P8_TABLE_FIGURE_SELECTION.md.
- Abstract: next pass. Citations: placeholders only (RELATED_WORK_GAPS.md). No calendar date or month (MANUSCRIPT_NOTES).
-->

# [TITLE — PI DECISION; recommended: "Chronological Personalization under Unseen-User Domain Shift: Offset Correction and Negative Transfer in Smart-Mat Temperature and Humidity Estimation" (docs/P8_TITLE_CANDIDATES.md)]

[AUTHORS AND AFFILIATIONS — PI]

[FIRST-PAGE NOTE — required for extended conference papers (to confirm, docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md
item 12): "This article is an extended version of a paper presented at the 18th International Conference on Future
Information & Communication Engineering (ICFICE 2026) [ICFICE CITATION]."]

## Abstract

[NEXT PASS — about 200 words, one paragraph, background–methods–results–conclusions without headings (to confirm).]

**Keywords:** smart mat; pressure sensing; temperature and humidity estimation; temporal convolutional network;
leave-one-subject-out evaluation; domain shift; chronological personalization; negative transfer [FINAL LIST: PI]

## 1. Introduction

Smart bedding and pressure-sensing mats monitor a person at rest without wearable devices or cameras, and they are
studied for sleep, posture and care applications [CITE: smart bedding / pressure-mat sensing]. In long-term care,
the thermal and moisture conditions at the body–mattress interface matter for the prevention of pressure injuries
[CITE: pressure injury prevention guideline], so the temperature and humidity of the bed microclimate are relevant
quantities to monitor.

Estimating these quantities indirectly, from signals that a mat already records, would avoid adding and maintaining
further sensors [CITE: indirect estimation / soft sensing]. Pressure sequences carry information about occupancy,
body contact and movement, which interact with the local microclimate. This makes them a plausible, if indirect,
input for temperature and humidity regression.

In a previous conference study [ICFICE CITATION], we examined this idea with a temporal convolutional network (TCN)
[CITE: TCN] that fused raw pressure sequences with movement-derived and contact-structure features. That study
reported gains from both feature types. Because part of the logs lacked second-level timestamps, it evaluated
pragmatic fixed-length sequences, and it stated that its results should not be read as strict elapsed-time or
strict leave-one-subject-out evaluation. It left strict time-based unseen-subject evaluation and user-adaptive
fine-tuning to future work.

These two open questions are the deployment questions. A model trained on some people is used for a new person, in a
new recording period, possibly on another mat and under a different microclimate. Cross-subject generalization of
this kind is known to be difficult for sensor-based models [CITE: cross-subject generalization / domain shift], and
in our data the new subject, the recording period, the season and the device cannot be separated. Under a strict
leave-one-subject-out protocol, we find that the errors differ strongly between subjects and are dominated by
systematic level offsets, and that changing the pressure representation does not remove them (Sections 4.1–4.2).

After deployment, a limited amount of labelled data from the new user can be collected if reference temperature and
humidity measurements are available for the first nights. Fine-tuning on these nights is an obvious way to correct a
domain-level offset [CITE: personalization / subject adaptation]. It carries a risk that is easy to overlook: the
earliest nights may not represent the later period the model is used in. When the conditions drift within a user
[CITE: temporal concept drift], adaptation can move the model towards a level that no longer holds, so it may
correct an offset or introduce a new one [CITE: negative transfer].

This study asks how far limited chronological personalization mitigates the unseen-subject failure of smart-mat
temperature and humidity estimation, and how its effect depends on the temporal representativeness of the adaptation
data. Its contributions are:
1. A leakage-controlled strict leave-one-subject-out evaluation of smart-mat temperature and humidity estimation
   across three held-out subjects under a combined subject–period–season–device shift, with a training-mean
   reference.
2. A comparison of six pressure feature families under the same protocol, showing target-dependent and non-additive
   contributions of movement and contact features and a cross-domain level offset that persists.
3. A chronological personalization evaluation with 0, 1, 3, 7 and 14 adaptation nights on a common future test span,
   showing both large offset corrections and clear negative transfer.
4. A night-level robustness analysis (paired cluster bootstrap, seed and start-span sensitivity, temporal
   level-mismatch and device-residual diagnostics), and a de-identified, model-ready data release from which all main
   results are reproduced.

Section 2 reviews related work. Section 3 describes the data, the protocol and the analysis. Section 4 reports the
results, Section 5 discusses them, Section 6 states the limitations, and Section 7 concludes.

## 2. Related Work

[STRUCTURE ONLY — topic sentences and citation placeholders until the literature pass (RELATED_WORK_GAPS.md).]

### 2.1. Pressure-Mat and Smart-Bedding Monitoring

Topic sentence: pressure-sensing mats and mattresses have been used for in-bed monitoring tasks such as posture,
occupancy and sleep assessment [CITE: pressure-mat monitoring].

### 2.2. Indirect Estimation of Temperature and Humidity

Topic sentence: environmental quantities are often estimated indirectly from other sensors when direct sensing is
costly or intrusive [CITE: indirect estimation / soft sensing], including in bedding microclimates
[CITE: bed microclimate].

### 2.3. Temporal Convolutional Networks for Sensor Time-Series Regression

Topic sentence: causal dilated convolutions provide a compact sequence model for sensor regression
[CITE: TCN time-series].

### 2.4. Cross-Subject Generalization and Leakage-Controlled Evaluation

Topic sentence: sensor models trained on some subjects often degrade on unseen subjects, and leave-one-subject-out
protocols without subject or temporal leakage are needed to measure this [CITE: cross-subject generalization]
[CITE: evaluation leakage].

### 2.5. Personalization, Subject Adaptation and Negative Transfer

Topic sentence: fine-tuning on a user's own data is a common personalization strategy
[CITE: personalized sensor models], but transfer can also degrade performance [CITE: negative transfer].

### 2.6. Temporal Drift and Level Calibration

Topic sentence: non-stationarity within a user and domain-level bias motivate drift monitoring and recalibration
[CITE: concept drift] [CITE: calibration / domain-level bias].

Positioning (to be written against verified literature only): this study combines strict unseen-subject evaluation
with chronological personalization and documents when adaptation helps and when it hurts.

## 3. Materials and Methods

### 3.1. Data and Cohort

The recordings come from smart mats with six pressure channels (12-bit analog-to-digital values, 0–4095) and with
temperature (°C) and relative-humidity (%RH) sensors measuring the mat microclimate. The mats contain a heater under
firmware control, which writes control codes into the logs; these codes are never used as model inputs.

**Cohort:**
- The primary cohort has three subjects, User01, User02 and User07. They were chosen before any model result, by
  structural data checks.
- User02 was recorded on two mats (22480 and 22482) at the same time. These are two device streams of **one
  subject**: they are kept as separate streams, never merged, and always assigned to the same partition. The cohort
  therefore has three subjects and four mat streams.
- The three subjects' recording periods do not overlap. Subject identity is therefore confounded with the recording
  period, the season, the mat and its microclimate. Every held-out fold in this study represents a combined
  unseen-domain shift, not a pure subject effect.

**Sources not used:**
- a source that the data provider confirmed as invalid;
- files with unresolved device attribution;
- restricted participant metadata;
- two legacy sources with minute-resolution timestamps, which are kept as auxiliary data and not used by the
  protocol.

Table 1 summarises the cohort and the protocol: `{{TABLE:manuscript_table_1_dataset}}`.

### 3.2. Canonical Dataset Construction

- **Source and verification:** all analyses use one canonical dataset, built deterministically from the raw logs.
  The raw files are read-only and verified against a checksum manifest before processing.
- **Copies:** repeated upload chunks are removed as exact copies only.
- **Sessions:** a new session starts after a gap longer than 30 min. Upload gaps of one known pattern on one mat are
  bridged and flagged.
- **Targets:** each row carries temperature and humidity validity flags. Missing values, zero sentinels and values
  outside a plausibility band (−10 to 60 °C; 0 to 100 %RH) are flagged invalid. No value is replaced, interpolated,
  smoothed or clipped, and no row is deleted.
- **Pressure:** values are not interpolated or clipped. The saturation value 4095 is kept, and all six channels are
  used.
- **Phase labels:** two acquisition changes are labelled and kept:
  - User01's sensor phases s1 and s2, before and after a sensor replacement;
  - the channel-quality phases of mat 22482, whose first channel shows a response shift in the later part of the
    recording.
  Both labels serve as window boundaries and reporting strata. They are never inputs, and no phase is excluded.

### 3.3. Windows, Inputs and Targets

- **Night:** runs from noon to noon and is the atomic unit of the chronological split.
- **Continuity segments:** rows of one subject, mat, session, phase and split partition with inter-row gaps of at most
  5 s.
- **Windows:**
  - 40-s windows start every 20 s within a segment;
  - each window is divided into eight 5-s bins, and the last observed row of each bin is one step;
  - a window exists only if all bins contain a row, so no value is invented;
  - splits are made before windowing, so no window crosses a partition boundary. Windows for personalization are also
    cut at night boundaries.
- **Target:** the temperature and humidity of the row at the last step (current, not future, conditions). A window
  is labelled only if both validity flags are true there.
- **Input:** the 8 × 6 raw pressure values divided by 4095. This fixed physical range is the same in every fold;
  there is no fitted input scaler.
- **Target scaling:** each target is standardised with the mean and standard deviation of the labelled windows of the
  training partition only. Metrics are computed in the original units.

### 3.4. Model and Training

- **Architecture:** a causal residual TCN with three blocks (dilations 1, 2 and 4), two causal convolutions per block
  with ReLU and dropout, and a linear head on the last time step. It predicts temperature and humidity jointly, with
  a mean-squared-error loss on the standardised targets.
- **Search space:** 16 configurations: channels {32, 64} × kernel size {2, 3} × dropout {0.1, 0.3} × learning rate
  {10⁻³, 3 × 10⁻⁴}.
- **Training:**
  - AdamW, weight decay 10⁻⁴, batch size 256, at most 50 epochs;
  - early stopping with patience 5 on the inner validation criterion;
  - training windows are shuffled uniformly each epoch, with no subject weighting.
- **Seeds and determinism:** every final model is trained with seeds 0, 1 and 2. Computation is deterministic, so that
  reruns are bitwise identical on the same hardware and software stack (Section 3.7).

### 3.5. Experimental Protocol

#### 3.5.1. Strict Leave-One-Subject-Out Evaluation (RQ1)

- **Folds:** each of the three outer folds holds out one subject entirely, including all its mats.
- **Nested selection:** model selection uses only the two training subjects.
  - Two inner splits train on one training subject and validate on the other, then swap.
  - Every configuration is scored with a unit-free criterion: the mean over the two inner splits of
    (MAE_T/sd_T + MAE_H/sd_H)/2, with the standard deviations taken from the inner training partition.
  - The best configuration is retrained on the whole outer training pool, for the rounded mean of its two inner
    best-epoch counts.
- **Single look:** the held-out subject is evaluated once per model. The selections were committed before any outer
  test evaluation.
- **Reference:** a training-mean predictor, which predicts the training pool's mean temperature and humidity, is
  evaluated on the same folds.

#### 3.5.2. Feature-Family Comparison (RQ3)

- **Features** are computed per window step from the step's six scaled channels:
  - **RAW** (6): the channels themselves.
  - **MOVEMENT** (10): the change of each channel from the previous step, the mean absolute change, and the changes of
    the total pressure and of the number of active channels, plus a dominant-channel switch indicator.
  - **CONTACT** (11): total pressure, the fraction of active channels, the six channel shares, the normalised entropy
    of the shares, the maximum share, and the across-channel standard deviation.
- **Geometry-free definitions:** the physical channel layout is unknown, so no feature uses channel coordinates. In
  particular, there is no centre of pressure.
- **Families:** RAW, MOVEMENT, CONTACT, RAW+MOVEMENT, RAW+CONTACT and RAW+MOVEMENT+CONTACT. Each family is trained as
  the TCN input.
- **Selection:** each family gets its own nested selection under the same budget. The comparison is therefore between
  representations, each with its own selected configuration. It is not a one-feature-at-a-time ablation of a fixed
  model.
- **Comparisons:** declared before the family results were seen:
  - movement added to RAW;
  - contact added to RAW;
  - both added to RAW;
  - contact added to RAW+MOVEMENT;
  - movement added to RAW+CONTACT.

#### 3.5.3. Chronological Personalization (RQ2)

- **Nights and budgets:** each subject's nights are numbered in time order. For budget b ∈ {0, 1, 3, 7, 14}:
  - nights 1…b are the adaptation data;
  - night b + 1 is an unused buffer;
  - evaluation uses the **primary test span of nights ≥ 16**. It is identical for every budget, including b = 0, so
    every budget is compared on the same future nights.
  - The per-budget later span (nights ≥ b + 2) is a secondary analysis.
- **Mats:** both User02 mats contribute to adaptation, and all devices of a night share its partition.
- **Base model:** the RQ1 RAW-TCN of the fold that holds the subject out, with the same seed.
- **Fine-tuning recipe:** for b > 0, all parameters are fine-tuned with AdamW:
  - learning rate 0.1 × the selected base rate, the base weight decay;
  - batch size 256, exactly 10 epochs;
  - no early stopping, no validation on target data;
  - the base model's target scaler is kept, not refit.
  The recipe and the per-subject plan (nights, windows, base checkpoints) were committed before any adaptation run.

#### 3.5.4. Leakage Control

- **Automated gate:** an automated check runs before every training or evaluation run. It stops the run if any rule
  fails.
- **Rules checked:**
  - held-out subjects and adaptation/test nights are disjoint from the data used for fitting and selection;
  - concurrent mats stay in one partition;
  - adaptation precedes the buffer and test nights;
  - scalers are fitted on training partitions only;
  - no input is a target, a control code, a calendar field or an identifier;
  - no window crosses a partition boundary.

### 3.6. Metrics and Statistical Analysis

- **Primary endpoints:** MAE and RMSE for temperature (°C) and humidity (%RH), computed separately over the labelled
  test windows of each held-out subject (both User02 mats pooled).
  - Results are reported per subject first.
  - The unweighted mean over the three subjects is shown as a description, not as a population estimate.
- **Secondary measures:**
  - the mean signed error (bias);
  - device and phase strata;
  - the per-budget later span.
  - For RQ2, the adaptation gain G_b = (E_0 − E_b)/E_0, with E the primary-span MAE; positive values mean improvement.
    A descriptive split of the RMSE into bias and error standard deviation is also reported.
- **Within-subject uncertainty:** a night-level paired cluster bootstrap.
  - Test nights are resampled with replacement together with all their windows, and base and adapted predictions are
    paired on the same resampled nights.
  - 2,000 resamples and 95 % percentile intervals; seed 0 is the primary model seed, and seeds 1 and 2 are reported
    as sensitivity.
  - Windows are never treated as independent samples, and with three subjects no population-level significance is
    claimed.
- **Post-hoc analyses:** defined in a written plan before they were computed, but after the personalization results
  were known. They are labelled post hoc and descriptive:
  - robustness of the gains to the start of the test span (nights ≥ 12, 14, 16, 18 or 21);
  - the difference between the mean target level of the adaptation nights and that of the later nights;
  - User02 strata by mat, quality phase and heater context. Heater context is the most recent heater on/off code on
    the same mat within 60 min before the target time, used for stratification only.

### 3.7. Reproducibility

- **Release:** a de-identified, model-ready release candidate was derived from the canonical dataset for
  reproduction:
  - 575,265 40-s windows of the three subjects (four mat streams), with raw pressure, targets, validity flags and
    window-set membership;
  - the evaluation splits;
  - the heater codes used for stratification;
  - reference digests of the frozen predictions.
- **Time:** only relative to each subject's first night (seconds since a per-subject anchor, relative night keys).
  No calendar date is included.
- **Excluded:** raw logs, participant metadata and the excluded sources are not part of it.
- **What was reproduced, from the release package alone in a clean checkout:**
  - the frozen selected models: the nine RAW-TCN base models, whose weights match their frozen digests, and the 45
    feature-family models;
  - the 45 personalization runs;
  - all downstream analyses;
  - every prediction file bitwise, and every reported result table.
- **Not rerun:** the hyperparameter searches (the nested inner searches for RAW and for the feature families). Their
  selections were reused as committed.

## 4. Results

### 4.1. Strict Leave-One-Subject-Out Generalization

Table 2 (`{{TABLE:manuscript_table_2_loso}}`) reports the held-out errors.

- **Heterogeneity:** the RAW-TCN errors differ strongly between subjects.
  - Temperature MAE: `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | User01 | .3f}}` °C
    (User01), `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | User02 | .3f}}` °C (User02) and
    `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | User07 | .3f}}` °C (User07).
  - Humidity MAE: `{{p3_primary_summary | model=tcn_raw, target=humidity, metric=mae | User01 | .3f}}`,
    `{{p3_primary_summary | model=tcn_raw, target=humidity, metric=mae | User02 | .3f}}` and
    `{{p3_primary_summary | model=tcn_raw, target=humidity, metric=mae | User07 | .3f}}` %RH.
- **Temperature: the neural model did not outperform the training-mean predictor for any held-out subject.**
  - Training-mean MAE: `{{p3_primary_summary | model=training_mean, target=temperature, metric=mae | User01 | .3f}}`,
    `{{p3_primary_summary | model=training_mean, target=temperature, metric=mae | User02 | .3f}}` and
    `{{p3_primary_summary | model=training_mean, target=temperature, metric=mae | User07 | .3f}}` °C.
  - Unweighted means:
    `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | unweighted_subject_mean | .3f}}` °C vs
    `{{p3_primary_summary | model=training_mean, target=temperature, metric=mae | unweighted_subject_mean | .3f}}` °C.
- **Humidity:** the TCN was better than the training mean for User01 and User02 and worse for User07.
  - Training-mean MAE:
    `{{p3_primary_summary | model=training_mean, target=humidity, metric=mae | User01 | .3f}}`,
    `{{p3_primary_summary | model=training_mean, target=humidity, metric=mae | User02 | .3f}}` and
    `{{p3_primary_summary | model=training_mean, target=humidity, metric=mae | User07 | .3f}}` %RH.
- **Level offsets:** the errors are largely systematic, and their signs differ between subjects.
  - User02 temperature bias `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=bias | User02 | +.3f}}` °C
    and humidity bias `{{p3_primary_summary | model=tcn_raw, target=humidity, metric=bias | User02 | +.3f}}` %RH.
    For this subject the bias accounts for essentially the whole MAE.
  - User01 humidity bias `{{p3_primary_summary | model=tcn_raw, target=humidity, metric=bias | User01 | +.3f}}` %RH.
- **Seeds:** the spread across the three seeds was much smaller than the differences between subjects (Table S1).

### 4.2. Feature-Family Comparison

Table 3 (`{{TABLE:manuscript_table_3_families}}`) compares the six families.

- **Movement → temperature:** movement information helped temperature.
  - MOVEMENT changed the unweighted temperature MAE by
    `{{p4_vs_raw | family=MOVEMENT, target=temperature, metric=mae | delta_unweighted_mean | +.3f}}` °C relative to
    RAW, improving `{{p4_vs_raw | family=MOVEMENT, target=temperature, metric=mae | improved_subjects | d}}` of three
    subjects.
  - Its humidity MAE worsened by
    `{{p4_vs_raw | family=MOVEMENT, target=humidity, metric=mae | delta_unweighted_mean | +.3f}}` %RH.
- **Contact → humidity:** RAW+CONTACT changed the unweighted humidity MAE by
  `{{p4_vs_raw | family=RAW+CONTACT, target=humidity, metric=mae | delta_unweighted_mean | +.3f}}` %RH, improving
  `{{p4_vs_raw | family=RAW+CONTACT, target=humidity, metric=mae | improved_subjects | d}}` of three subjects.
- **Not additive:** the model with all features ranked
  `{{p4_primary_summary | model=RAW+MOVEMENT+CONTACT, target=temperature, metric=mae | rank_among_tcn_families | s}}`
  of six for temperature and
  `{{p4_primary_summary | model=RAW+MOVEMENT+CONTACT, target=humidity, metric=mae | rank_among_tcn_families | s}}` for
  humidity.
- **Effect sizes:** the gains came mostly from User01 and were small compared with the differences between subjects.
- **No representation removed the domain-level offset.**
  - The best temperature family (MOVEMENT,
    `{{p4_primary_summary | model=MOVEMENT, target=temperature, metric=mae | unweighted_subject_mean | .3f}}` °C) did
    not reach the training-mean predictor
    (`{{p4_primary_summary | model=training_mean, target=temperature, metric=mae | unweighted_subject_mean | .3f}}` °C).
  - User02 temperature bias ranged from
    `{{p4_primary_summary | model=RAW, target=temperature, metric=bias | User02 | +.3f}}` to
    `{{p4_primary_summary | model=RAW+MOVEMENT+CONTACT, target=temperature, metric=bias | User02 | +.3f}}` °C across
    the TCN families.
  - User02 humidity bias ranged from
    `{{p4_primary_summary | model=MOVEMENT, target=humidity, metric=bias | User02 | +.3f}}` to
    `{{p4_primary_summary | model=RAW+MOVEMENT+CONTACT, target=humidity, metric=bias | User02 | +.3f}}` %RH (Table S7).

### 4.3. Chronological Personalization

Table 4 (`{{TABLE:manuscript_table_4_personalization}}`) and Figures 2 and 3 show the primary-span MAE by subject and
budget. The b = 0 values are the base models on the primary span (nights ≥ 16) only, so they differ from Table 2,
which covers all nights.

**Cohort curves** (unweighted means, descriptive):
- Temperature MAE:
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=0 | seed_mean | .3f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=1 | seed_mean | .3f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=3 | seed_mean | .3f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=7 | seed_mean | .3f}}` and
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=14 | seed_mean | .3f}}` °C for
  b = 0, 1, 3, 7 and 14.
- Humidity MAE:
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=0 | seed_mean | .3f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=1 | seed_mean | .3f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=3 | seed_mean | .3f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=7 | seed_mean | .3f}}` and
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=14 | seed_mean | .3f}}` %RH. The
  humidity curve is not monotone and improves only at 14 nights.

**The cohort curves hide opposite subject-level effects.**
- **User02 (offset correction):** improved on both targets at every budget.
  - Temperature G reached
    `{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | G_pct | +.1f}}` % at b = 14.
  - The temperature bias moved from
    `{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_0 | +.3f}}` °C to
    `{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_b | +.3f}}` °C.
  - Humidity G at b = 14 was
    `{{p5_adaptation_gain | subject_id=User02, target=humidity, budget_nights=14 | G_pct | +.1f}}` %.
- **User07 temperature (negative transfer):** worse than its base model at every budget.
  - G was `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=1 | G_pct | +.1f}}` % at b = 1
    and `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=14 | G_pct | +.1f}}` % at b = 14.
  - `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=14 | seeds_improved | d}}` of three
    seeds improved at b = 14.
  - Its bias changed sign, from
    `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=14 | bias_0 | +.3f}}` to
    `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=14 | bias_b | +.3f}}` °C.
  - User07 humidity, in contrast, improved (b = 14:
    `{{p5_adaptation_gain | subject_id=User07, target=humidity, budget_nights=14 | G_pct | +.1f}}` %).
- **User01 humidity:** negative transfer up to seven nights, then recovery.
  - G was `{{p5_adaptation_gain | subject_id=User01, target=humidity, budget_nights=1 | G_pct | +.1f}}`,
    `{{p5_adaptation_gain | subject_id=User01, target=humidity, budget_nights=3 | G_pct | +.1f}}` and
    `{{p5_adaptation_gain | subject_id=User01, target=humidity, budget_nights=7 | G_pct | +.1f}}` % at b = 1, 3 and 7.
  - It was `{{p5_adaptation_gain | subject_id=User01, target=humidity, budget_nights=14 | G_pct | +.1f}}` % at b = 14.
  - More adaptation data did not improve the result monotonically.
- **User01 temperature:**
  - slightly worse at b = 1
    (`{{p5_adaptation_gain | subject_id=User01, target=temperature, budget_nights=1 | G_pct | +.1f}}` %);
  - better from b = 3 (`{{p5_adaptation_gain | subject_id=User01, target=temperature, budget_nights=3 | G_pct | +.1f}}` %);
  - `{{p5_adaptation_gain | subject_id=User01, target=temperature, budget_nights=14 | G_pct | +.1f}}` % at b = 14.
- **Error decomposition, descriptive:**
  - the User02 temperature gain is almost pure offset correction;
  - User01 temperature at b = 3 and 7 improves mainly through a lower error spread;
  - the User07 temperature loss is a newly introduced offset;
  - humidity changes are dominated by the offset in both directions (Table S9).
- **Low budgets:** one to three adaptation nights did not provide reliable improvement across subjects and targets.

### 4.4. Night-Level Uncertainty and Robustness

Table 5 (`{{TABLE:manuscript_table_5_bootstrap}}`) and Figure 4 give the night-level paired bootstrap intervals of the
MAE change (base − adapted; positive = improvement) for model seed 0.

- **User02 temperature at b = 14:**
  `{{p6_bootstrap_mae | subject_id=User02, target=temperature, budget_nights=14 | point_estimate | +.3f}}` °C
  [`{{p6_bootstrap_mae | subject_id=User02, target=temperature, budget_nights=14 | ci_lower | +.3f}}`,
  `{{p6_bootstrap_mae | subject_id=User02, target=temperature, budget_nights=14 | ci_upper | +.3f}}`].
  - Every User02 interval lay above zero, for both targets and all budgets.
  - For humidity at b = 14:
    `{{p6_bootstrap_mae | subject_id=User02, target=humidity, budget_nights=14 | point_estimate | +.3f}}` %RH
    [`{{p6_bootstrap_mae | subject_id=User02, target=humidity, budget_nights=14 | ci_lower | +.3f}}`,
    `{{p6_bootstrap_mae | subject_id=User02, target=humidity, budget_nights=14 | ci_upper | +.3f}}`].
- **User01 temperature:**
  - the changes at b = 1 and 3 were within night-level uncertainty; at b = 1:
    `{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=1 | point_estimate | +.3f}}` °C
    [`{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=1 | ci_lower | +.3f}}`,
    `{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=1 | ci_upper | +.3f}}`];
  - the gains at b = 7 and 14 had intervals above zero; at b = 14:
    `{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=14 | point_estimate | +.3f}}` °C
    [`{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=14 | ci_lower | +.3f}}`,
    `{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=14 | ci_upper | +.3f}}`].
- **User01 humidity:**
  - intervals below zero at b = 1, 3 and 7; at b = 3:
    `{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=3 | point_estimate | +.3f}}` %RH
    [`{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=3 | ci_lower | +.3f}}`,
    `{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=3 | ci_upper | +.3f}}`];
  - above zero at b = 14:
    `{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=14 | point_estimate | +.3f}}` %RH
    [`{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=14 | ci_lower | +.3f}}`,
    `{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=14 | ci_upper | +.3f}}`].
- **User07 temperature: the negative-transfer direction was dominant across seeds and start-span analyses, but it was
  not literally invariant for every seed–start combination.**
  - Seed 0: the intervals lay below zero at
    `{{COUNT:p6_bootstrap_mae | subject_id=User07, target=temperature, interval=below_zero}}` of four budgets.
  - Seed 1: at `{{COUNT:p6_bootstrap_seed_sensitivity | subject_id=User07, target=temperature, metric=mae, seed=1, interval=below_zero}}`
    of four.
  - Seed 2: at `{{COUNT:p6_bootstrap_seed_sensitivity | subject_id=User07, target=temperature, metric=mae, seed=2, interval=below_zero}}`
    of four.
- **Start of the test span (post hoc):** moving the start among nights 12, 14, 16, 18 and 21 changed the magnitude of
  the gains, but at the aggregated subject–target–budget level the principal directional findings were stable across
  these start points (Table S17). Seed-level exceptions occurred in borderline cases.
  - For User07 temperature at start night 12 and b = 1,
    `{{p6_drift_sensitivity | start_night=12, subject_id=User07, target=temperature, budget_nights=1 | seeds_improved | d}}`
    of `{{p6_drift_sensitivity | start_night=12, subject_id=User07, target=temperature, budget_nights=1 | n_seeds | d}}`
    seeds showed a positive gain.
  - The seed-mean gain was negative there
    (`{{p6_drift_sensitivity | start_night=12, subject_id=User07, target=temperature, budget_nights=1 | G_pct | +.1f}}` %).
  - The User07 temperature loss grew as the test span moved later.

### 4.5. Temporal Level Mismatch (Post Hoc, Descriptive)

Using the targets only (no model), we compared the mean target level of each adaptation span with that of the
primary span (Table S15; Figure 5 or Figure S-level). Values below are span mean minus primary-span mean.

- **User07 temperature:**
  - the earliest night: `{{p6_level_mismatch_spans | subject_id=User07, target=temperature, span=adaptation_b1 | minus_primary_mean | +.3f}}` °C;
  - the 14-night adaptation span:
    `{{p6_level_mismatch_spans | subject_id=User07, target=temperature, span=adaptation_b14 | minus_primary_mean | +.3f}}` °C;
  - the base model's training pool:
    `{{p6_level_mismatch_spans | subject_id=User07, target=temperature, span=training_pool | minus_primary_mean | +.3f}}` °C.
  The early nights were cooler than the later period, whereas the training pool was close to it.
- **User01 humidity:** the adaptation spans lay far above the later level:
  - `{{p6_level_mismatch_spans | subject_id=User01, target=humidity, span=adaptation_b3 | minus_primary_mean | +.3f}}` %RH
    for b = 3;
  - `{{p6_level_mismatch_spans | subject_id=User01, target=humidity, span=adaptation_b14 | minus_primary_mean | +.3f}}` %RH
    for b = 14.
- **User02 temperature:** the adaptation spans were much closer to the later level than the training pool:
  - b = 14: `{{p6_level_mismatch_spans | subject_id=User02, target=temperature, span=adaptation_b14 | minus_primary_mean | +.3f}}` °C;
  - training pool: `{{p6_level_mismatch_spans | subject_id=User02, target=temperature, span=training_pool | minus_primary_mean | +.3f}}` °C.
- **Descriptive rule:** adaptation is expected to help when the adaptation-span level lies closer to the later level
  than the base model's bias.
  - It agreed with the observed direction in
    `{{COUNT:p6_level_mismatch_consistency | consistent=True}}` of 24 subject–target–budget cells.
  - The exception was User01 temperature at b = 3, where the gain came from a lower error spread.
  - This is an association within three subjects, not a test of a mechanism.

### 4.6. Device-Level Residual (User02)

- **Mat 22482 temperature:** a negative residual persisted after adaptation.
  - Bias at b = 14 (seed mean):
    `{{p5_user02_device_strata | subject_id=User02, budget_nights=14, seed=mean, stratum_type=device, stratum=22482, target=temperature, metric=bias | value | +.3f}}` °C.
  - Seed-0 night-level interval:
    `{{p6_user02_device_context_bootstrap | stratum=22482, target=temperature, quantity=bias_b14 | point_estimate | +.3f}}` °C
    [`{{p6_user02_device_context_bootstrap | stratum=22482, target=temperature, quantity=bias_b14 | ci_lower | +.3f}}`,
    `{{p6_user02_device_context_bootstrap | stratum=22482, target=temperature, quantity=bias_b14 | ci_upper | +.3f}}`].
- **Mat 22480:** bias at b = 14 of
  `{{p6_user02_device_context_bootstrap | stratum=22480, target=temperature, quantity=bias_b14 | point_estimate | +.3f}}` °C
  [`{{p6_user02_device_context_bootstrap | stratum=22480, target=temperature, quantity=bias_b14 | ci_lower | +.3f}}`,
  `{{p6_user02_device_context_bootstrap | stratum=22480, target=temperature, quantity=bias_b14 | ci_upper | +.3f}}`];
  the interval includes zero.
- **Strata:** the 22482 under-estimation persisted in every quality-phase and heater-context stratum with at least ten
  nights (Table S18).
- **Interpretation:** the mats differ in microclimate and control history, and their physical placement is unknown;
  these factors cannot be separated here. The residual is therefore reported as a device-level observation, not as
  evidence of a sensor defect or a heater effect.

## 5. Discussion

### 5.1. Why Adaptation Sometimes Helps and Sometimes Hurts

The results point to one pattern. Under strict leave-one-subject-out evaluation, a large part of the error is a
level offset between the held-out domain and the training pool (Section 4.1) [CITE: calibration / domain-level
bias]. Full fine-tuning on a subject's earliest nights moves the model's predictions towards the level of those
nights. When that level is close to the level of the later nights, the offset shrinks: this is the User02 case.
When it is far from it, the model acquires a new offset: User07 temperature and User01 humidity at up to seven
nights.

The post-hoc level comparison agrees with this in almost every cell (Section 4.5). These observations are consistent
with temporal representativeness being an important condition for successful personalization. They do not show
that temporal drift causes negative transfer: three subjects, confounded periods and one adaptation recipe allow
association only [CITE: temporal concept drift].

### 5.2. Feature Engineering and Personalization Address Different Problems

- **Features:** movement and contact features lowered a single subject's error by at most
  `{{p4_incremental_effects | effect=A, target=temperature, metric=mae | delta_User01 | +.3f}}` °C (movement added to
  RAW, User01) and
  `{{p4_incremental_effects | effect=B, target=humidity, metric=mae | delta_User01 | +.3f}}` %RH (contact added to
  RAW, User01). They did so for one target each, mostly for one subject, and they did not reduce the level offsets.
- **Personalization:** changed the level itself, by several degrees for User02.
- **Consequence:** in this setting, a better representation of pressure dynamics is not a substitute for
  information about the target user's level, and vice versa.

### 5.3. Personalization Is Not Intrinsically Beneficial

- **Same recipe, both outcomes:** the same frozen recipe produced the largest gain in the study and clear negative
  transfer.
- **Cohort mean:** the unweighted cohort mean improved for temperature but hid a subject that became worse at every
  budget, and for humidity it improved only at 14 nights.
- **Low budgets:** very low adaptation budgets were insufficient to guarantee benefit.
- **Reporting:** a personalization study that reported only cohort means would miss these failures. Subject-level
  reporting with night-level uncertainty is needed to see them.

### 5.4. More Adaptation Data Can Help, but Not Monotonically

- **User01 humidity:** recovered at 14 nights after being worse at one to seven nights. As the adaptation span grows,
  its level moves closer to the later level (Section 4.5).
- **User07 temperature:** did not recover within 14 nights. Its early nights stayed cooler than the later period
  throughout.
- **Consequence:** how much adaptation data is enough depends on the subject and the target, and in this cohort it
  could not be predicted from the budget alone.

### 5.5. A Device-Level Residual Remains

User02 temperature illustrates both sides:
- a large zero-shot negative bias was mostly corrected;
- the night-level interval of the improvement was narrow and above zero;
- yet one mat kept a negative residual after 14 nights.
Both mats belong to one subject and were adapted jointly. The residual is consistent with one adapted model having to
serve two mat microclimates at once. We do not attribute it to a device defect, to the heater or to a property of the
user.

### 5.6. Practical Implications (Not Tested)

For deployment, these results suggest that personalization needs safeguards: selecting or weighting adaptation data
by its similarity to current conditions, monitoring the level drift after adaptation, or falling back to a simpler
offset calibration [CITE: calibration / domain-level bias]. None of these safeguards was evaluated here; they are
future work.

## 6. Limitations

- **Cohort and inference:** the study has three independent primary subjects. Their recording periods do not
  overlap, so subject, recording period, season, mat and microclimate are confounded in every fold. The results
  therefore describe three combined domain shifts; they support no population-level inference and no statistical
  significance across subjects.
- **Adaptation design:** one frozen full fine-tuning recipe was evaluated (learning rate, epochs and scope fixed in
  advance). Adaptation always used the earliest recorded nights, as a deployment would, so its effect is tied to
  how representative those nights are; other samplings of adaptation data were not studied.
- **Confounded labels:** User01's sensor phases coincide with a change in time and season, so their effects cannot
  be separated. The differences between the two User02 mats have no causal interpretation.
- **Statistics:** the night-level bootstrap resamples nights independently. Consecutive nights are correlated
  through drift, so the intervals may be too narrow for trending series, and the serial dependence between nights is
  not fully captured.
- **Analyses not run:** the declared 20-s and 30-s window sensitivity analyses and a sensitivity analysis for the
  4095 saturation value were not run; the procedures they would need were not fixed in advance. A simpler bias-only
  calibration was not compared with full fine-tuning.
- **Release:** the public release is derived and model-ready. It contains 40-s windows, not the raw logs, so it
  reproduces this study's analyses but does not support new row-level preprocessing.

## 7. Conclusions

- **Strict evaluation:** in this cohort, smart-mat pressure sequences supported temperature and humidity estimation
  for an unseen subject only up to a large, subject-dependent level offset, which alternative pressure
  representations did not remove.
- **Chronological personalization:** can remove most of this offset when the earliest nights of the new user
  represent the later period. The same procedure produced negative transfer when they did not, and one to three
  nights were not enough to guarantee benefit.
- **Consequence:** the decisive factor was not the amount of adaptation data alone but its temporal
  representativeness. Future work should test adaptation-data selection, drift monitoring and calibration
  safeguards on larger cohorts.

## Reproducibility Statement

[PLACEMENT TO CONFIRM WITH THE TEMPLATE.] The frozen selected models and all downstream analyses were reproduced from
the derived release package in a clean checkout; the hyperparameter searches were not rerun (Section 3.7).

## Data Availability Statement

[See DATA_AVAILABILITY_DRAFT.md — placeholders [DATA REPOSITORY], [DOI], [LICENSE] remain until resolved.]

## Code Availability

[See CODE_AVAILABILITY_DRAFT.md — repository publication scope and license pending.]

## Institutional Review Board Statement

[ETHICS / IRB INFORMATION REQUIRED FROM PI]

## Informed Consent Statement

[PI] Documented: the data provider confirmed that participant consent was obtained and that the data may be used and
released for research. This confirmation is not an institutional ethics approval.

## Author Contributions

[PI — CRediT roles]

## Funding

[PI — confirm whether the funding acknowledged in the conference paper applies to this work]

## Conflicts of Interest

[PI]

## References

[references.bib — verified entries only; numbered in order of citation (style to confirm)]

## Supplementary Materials

Tables S1–S19 and supplementary figures as listed in docs/P8_TABLE_FIGURE_SELECTION.md.
