<!-- Rendered by scripts/build_submission_candidate.py from paper/manuscript/manuscript.md. Do not edit; edit the source and re-render. Bracketed items are open placeholders (docs/P8_FINAL_BLOCKERS.md). -->



# Strict Unseen-Domain Evaluation of Smart-Mat Microclimate Estimation against Simple Level Baselines

**Authors:** [AUTHOR NAMES AND ORDER — CONFIRM]

**Affiliations:** [AFFILIATIONS — CONFIRM]

**Corresponding author:** [NAME AND E-MAIL — CONFIRM]

**ORCID:** [ORCID iDs — CONFIRM]

**Note:** This article is a revised and expanded version of a paper entitled "Robust Temperature and Humidity
Estimation from Smart Bedding Pressure Sequences Using Movement and Contact-Structure Features", which was presented at
the 18th International Conference on Future Information & Communication Engineering (ICFICE 2026), Sapporo, Japan, 7–10 July 2026 [1].

**Featured Application:** This study provides a deployment-oriented evaluation framework for smart-mat temperature
and humidity estimation. In three held-out cases, limited chronological user adaptation mainly corrected
unseen-domain prediction offsets, which a personalized constant corrected as well, and the neural predictions showed
no consistent within-night co-variation with the measured microclimate; simple level baselines are therefore needed to
judge such systems.

## Abstract

Smart-mat pressure could yield bed-microclimate temperature and humidity estimates without extra sensors, but
deployed models face unseen users, periods and mats. We evaluated temporal convolutional networks on 40-s pressure
windows from three subjects (four mat streams) under strict leave-one-subject-out evaluation; each held-out fold was an
unseen domain of subject, period and mat. Models were fine-tuned on each subject's earliest 1–14 nights and tested
on a fixed later span. Under strict evaluation, errors were dominated by level offsets, and for temperature the network did not outperform a
training-mean predictor. Fine-tuning moved one subject's temperature bias from
−5.06 to
−1.21 °C after 14 nights,
whereas another subject's seed-mean temperature error exceeded its base model's at every budget. Post-hoc comparators
showed mainly level corrections: the mean target of the adaptation nights, which uses no pressure input, was not worse
than full fine-tuning in 12 of 24 subject–target–budget cells.
Night-centred correlations showed no consistent within-night co-variation between predictions and targets, and an
affine recalibration fitted retrospectively on the test labels could not have lowered the residual standard deviation
below 0.93 times the target's. Under the tested representation, architecture and schedules,
pressure-based neural estimation showed no consistent advantage over simple level baselines. With three subjects, these
findings are case-level.

**Keywords:** smart bedding; pressure sensing; temperature and humidity estimation; temporal convolutional network;
cross-subject generalization; leave-one-subject-out evaluation; negative transfer; baseline comparison

## 1. Introduction

Pressure-sensing mats and bedsheets record a person at rest without wearable devices or cameras. They have been used
to monitor sleep posture [2,3] and breathing [4], within a broader
effort to replace laboratory sleep studies by unobtrusive home monitoring [5]. In care settings,
the microclimate next to the skin (temperature and humidity) is an indirect risk factor for pressure injuries
[6], so the temperature and humidity of the bed microclimate are relevant quantities to
monitor.

These quantities can be measured with sensors built into the mattress [7]. Estimating them instead
from signals that a pressure mat already records would avoid adding and maintaining further sensors. Pressure
sequences reflect posture, body contact and movement [2,4]. Whether they also
carry enough information to estimate the local temperature and humidity is not established; it is the question
examined here.

In a previous conference study [1], we examined this idea with a temporal convolutional network (TCN)
[8,9] that fused raw pressure sequences with movement-derived and contact-structure features.
That study reported gains from both feature types. Because part of the logs lacked second-level timestamps, it
evaluated pragmatic fixed-length sequences, and it stated that its results should not be read as strict elapsed-time
or strict leave-one-subject-out evaluation. It left strict time-based unseen-subject evaluation and user-adaptive
fine-tuning to future work.

These two open questions are the deployment questions. A model trained on some people is used for a new person, in a
new recording period, possibly on another mat and under a different microclimate. Sensor-based models are known to
lose accuracy for new users and on different devices [10–12]. In our data, the new subject, the recording period, the season and the device cannot be
separated, so each held-out subject defines an unseen domain: a combined shift, not a pure subject effect. Under a
strict leave-one-subject-out protocol, we find that the errors differ strongly between subjects and are dominated by
systematic level offsets, and that changing the pressure representation does not remove them (Sections 4.1–4.2).

Labelled data from a new user require reference temperature and humidity measurements, which the pressure-based
estimate is meant to replace. One way to reconcile the two is a temporary commissioning period: reference sensors
are installed for the first nights of a deployment, their labels are used to adapt the model, and the sensors are
then removed while the pressure-based estimate serves the later period. This study emulates that scenario with the
mats' own temperature and humidity records; it does not evaluate it operationally. Personalizing sensor models, with
a small amount of the new user's labelled data or with data from similar users, has improved recognition accuracy in
other domains
[10,13]. It carries a risk that is easy to overlook: the earliest
nights may not represent the later period the model is used in. When the relation between inputs and target changes
over time [14], adaptation can move the model towards a level that no longer holds. Transfer can then
hurt instead of help [15,16], and adaptation may correct an offset or introduce a new
one.

This study evaluates, under strict subject-wise and chronological evaluation, whether pressure-based neural
estimation of the smart-mat microclimate and its limited chronological personalization outperform simple level
baselines for an unseen domain, and how the effect of personalization depends on the temporal representativeness of the
adaptation data. It addresses three research questions:
- **RQ1:** How accurate and how systematic is the estimation for an unseen subject under strict
  leave-one-subject-out evaluation?
- **RQ2:** How far does fine-tuning on a limited number of the new subject's earliest nights reduce this error, and
  when does it increase it?
- **RQ3 (secondary):** Do movement-derived or contact-structure representations of the pressure signal reduce the
  unseen-domain error?

A gain in RQ2 could come from correcting the output level alone, which needs no pressure information. After the
primary results were known, we therefore compared the adapted models, post hoc and with a design fixed before the
comparison was computed, with simpler predictors: constant predictors, the base model shifted by an offset estimated
on the adaptation nights, and a network trained from scratch on those nights (Section 3.5.5). A residual-variation
ratio near one does not by itself exclude co-variation hidden by an offset or scale mismatch, so a final second-order
post-hoc diagnostic measured the prediction scale and the pooled and within-night correlations between predictions and
targets (Section 3.5.6).

The contributions are:
1. A leakage-controlled strict leave-one-subject-out evaluation of smart-mat temperature and humidity estimation
   across three held-out subjects under a combined subject–period–season–device shift, with a training-mean
   reference (RQ1).
2. A chronological personalization evaluation with 0, 1, 3, 7 and 14 adaptation nights on a common future test span,
   reported per subject and target, which shows both large offset corrections and clear negative transfer (RQ2).
3. A post-hoc comparator analysis showing that the personalization gains were mainly level corrections: a
   personalized constant had an error no higher than full fine-tuning in
   12 of 24 cells, the pressure-based models showed no
   demonstrable within-subject tracking of the targets, and cross-subject pretraining added little over training on
   the adaptation nights alone. A final diagnostic found no consistent within-night co-variation between the neural
   predictions and the targets and little retrospective linear-calibration headroom.
4. A night-level robustness analysis: a paired cluster bootstrap, seed and start-span sensitivity, and post-hoc
   temporal level-mismatch and device-residual diagnostics.
5. A secondary comparison of six pressure feature families under the same protocol. It shows target-dependent,
   non-additive contributions of movement and contact features and a level offset that no representation removes
   (RQ3).
6. A de-identified, model-ready release candidate from which the selected models, the predictions and the result
   tables were reproduced in a clean checkout; the hyperparameter searches were not rerun (Section 3.7).

**Relation to the conference study.** The conference study [1] evaluated a late-fusion framework for
movement and contact features on pragmatic fixed-length sequences, including subjects whose logs lacked
second-level timestamps. It did not perform strict elapsed-time leave-one-subject-out evaluation or target-user
fine-tuning. The present article:
- rebuilds the recordings into an audited canonical dataset;
- restricts the primary cohort to subjects with complete second-level timestamps;
- adds strict elapsed-time leave-one-subject-out evaluation with frozen nested model selection, chronological
  personalization, a negative-transfer analysis, night-level robustness analyses and a de-identified reproduction
  package.
No text, table or figure of the conference paper is reused. Its results are not compared numerically with those
reported here, because the data policies differ. The conference study found relative improvements from movement- and
contact-aware pressure representations under its original evaluation setting. The present study shows that relative
improvements among neural representations do not, by themselves, establish superiority over simple level baselines or
unseen-domain validity under subject-wise and chronological evaluation (Section 5.4). It does not show that the
conference results were wrong, and it does not attribute them to leakage or to level artefacts.

Section 2 reviews related work. Section 3 describes the data, the protocol and the analysis. Section 4 reports the
results, Section 5 discusses them, Section 6 states the limitations, and Section 7 concludes.

## 2. Related Work

### 2.1. Smart Bedding and Pressure-Based Monitoring

In-bed pressure sensing is an established route to unobtrusive monitoring:
- Dense textile bedsheets and commercial pressure mats have been used to classify sleep posture
  [2,3], in the latter case explicitly for pressure-injury prevention.
- Public pressure-map data sets support posture and subject analytics [17].
- A textile pressure matrix integrated into a mattress has characterised posture and movement and extracted breathing
  activity [4].
- These systems belong to a wider move towards unobtrusive sleep monitoring outside the laboratory
  [5].

The bed microclimate has a separate clinical motivation:
- The skin microclimate is regarded as an indirect pressure-injury risk factor
  [6].
- Modelling indicates that higher temperature and humidity lower skin tolerance [18].
- Microclimate differences have been observed between patients who did and did not develop skin damage
  [19].
- Where the microclimate is monitored, this has been done with dedicated sensors, such as humidity sensors built into
  a mattress [7], or as part of a smart bed that also collects environmental data next to its
  pressure layer [4].

These studies use pressure to infer posture, movement or breathing, or they measure temperature and humidity
directly. In the studies reviewed here, the microclimate is measured, not estimated from the pressure signal. Our
conference study examined it with fused pressure representations, but it did not evaluate unseen users or adaptation
[1]. The present work treats pressure-based temperature and humidity estimation as an open deployment
problem rather than as an established capability.

### 2.2. Temporal Models for Sensor Regression

- **TCNs:** temporal convolutional networks were introduced as hierarchies of temporal convolutions for fine-grained
  action segmentation [8]. A generic TCN built from causal and dilated convolutions with residual blocks was
  later evaluated against recurrent networks and performed better on the benchmark tasks studied, with a longer
  effective memory [9].
- **Wearable sensors:** deep networks that learn features directly from raw sequences and model their temporal
  dynamics have been proposed for sensor-based recognition [20].
- **Our task:** estimating the current temperature and humidity from a window of past and present pressure values is
  a regression from a time series to continuous values, known as time series extrinsic regression. It is distinct
  from forecasting and from classification [21].
- **Use in this study:** we use the TCN as a well-studied model family for this setting. We do not claim that it is
  superior to recurrent alternatives, which were not compared.

### 2.3. Cross-Subject Generalization and Personalization

**Evaluation.** How generalization to new people is measured matters:
- Random cross-validation over segmented sensor time series is optimistic, because adjacent segments are not
  independent [22].
- Record-wise validation can grossly overestimate accuracy for new subjects, whereas subject-wise validation mirrors
  that use case [23].

**Generalization failures:**
- Individual diversity limits population models of human activity [10].
- Recognition accuracy drops for new users or when a user's condition changes [11].
- One-size-fits-all models perform poorly when outcomes vary between individuals [24].
- Heterogeneity between devices [12] and sensor placements [25] degrades recognition
  further.

**Responses:**
- personalization with small amounts of the new user's data, or with similar users [10,13];
- transfer learning with minimal user supervision [11];
- personalized multitask models [24];
- domain adaptation for time-series sensor data [26]. Its assumptions can fail in practice
  [25].

**Scope gap:** most of this work concerns activity or state recognition. Less examined is the regression of
continuous environmental quantities for an unseen user under a combined shift of subject, recording period, season
and device. The same holds for personalization data taken chronologically from the start of deployment and evaluated
on a fixed later span. The present study addresses this setting with three subjects, so it describes cases rather
than population effects.

### 2.4. Negative Transfer, Temporal Drift and Calibration

- **Transfer learning** addresses the case in which training data and the data of later use follow different
  distributions [27]. Its benefit is not guaranteed: transfer from a less related source can reduce
  target performance, which is known as negative transfer [15]. This long-standing problem has
  motivated many remedies [16].
- **Concept drift:** the relation between inputs and target may also change over time [14]. For
  data-driven soft sensors, which estimate quantities indirectly, adaptation mechanisms such as moving windows,
  recursive updates and ensembles have been organised around this concept-drift view [28].
- **Calibration:** low-cost environmental sensors are error-prone in the field and drift over time. Calibration and
  in situ recalibration have been used to maintain data quality in long-term deployments
  [29,30].

**Relation to this study:** in chronological personalization, the adaptation data are the target user's own earliest
nights. If the user's conditions drift, adapting to those nights can make later predictions worse. This is a temporal
form of the relatedness question behind negative transfer.
- The literature above describes the ingredients: distribution shift, negative transfer, drift and recalibration. It
  does not establish how they combine in this application.
- Our evidence on this point is empirical and descriptive (Sections 4.3–4.5).
- The calibration literature motivates simpler offset-correction comparators. This study evaluates them post hoc
  against full fine-tuning (Section 3.5.5 and Section 4.7).

## 3. Materials and Methods

### 3.1. Data and Cohort

The recordings come from smart mats with six pressure channels (12-bit analog-to-digital values, 0–4095) and with
temperature (°C) and relative-humidity (%RH) sensors measuring the mat microclimate. The mats contain a heater under
firmware control, which writes control codes into the logs. These codes are excluded from the model inputs under the
leakage policy (Section 3.5.4), so the heater and controller state remains an unobserved determinant of the
microclimate for every model in this study.

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
  protocol. The conference study's recordings without second-level timestamps are consistent with this retained
  legacy minute-resolution lineage; exact file-level identity is not assumed.

Table 1 summarises the cohort and the protocol.

**Table 1.** Cohort, data and protocol summary. One row per subject (three subjects, four mat streams); User02's two
mats are one subject and always share a partition. Columns: mat streams; recording sessions (per mat for User02);
the leave-one-subject-out fold in which the subject is held out; labelled 40-s windows; primary test nights
(nights ≥ 16) and primary test windows of chronological personalization. Counts only; no performance values; nights
are counted, never dated.

| Subject | Mat streams | Recording sessions | Held out in | Labelled 40-s windows | Primary test nights (≥ 16) | Primary test windows | Notes |
|---|---|---|---|---|---|---|---|
| User01 | 1 (mat ID not recorded) | 157 | fold 1; training subject in folds 2 and 3 | 289,437 | 136 | 265,852 | Sensor phases s1/s2 (before/after a sensor replacement): window boundary and reporting stratum, never an input |
| User02 | 2 (mats 22480, 22482) | 47 / 58 | fold 2; training subject in folds 1 and 3 | 143,999 | 36 | 95,839 | One subject: two concurrent mats, kept as separate streams in the same partition |
| User07 | 1 (mat ID not recorded) | 102 | fold 3; training subject in folds 1 and 2 | 140,971 | 85 | 114,838 | — |

Notes:

- Three subjects and four mat streams. User02's two mats belong to one subject and are never counted as two subjects. Sessions for User02 are given per mat (22480 / 22482).
- Labelled windows: all labelled windows of the subject, i.e. its test set when it is held out in strict leave-one-subject-out evaluation.
- Chronological personalization: adaptation budgets b = 0, 1, 3, 7 and 14 nights (the earliest nights); night b + 1 is an unused buffer; the primary test span (nights ≥ 16) is identical for every b.
- Counts only. Nights are counted, never dated.

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
  - splits are made before windowing, so no window crosses a partition boundary. Overlapping windows are not
    independent, and random splits over them would overstate accuracy for new users [22].
    Windows for personalization are also cut at night boundaries.
- **Target:** the temperature and humidity of the row at the last step (current, not future, conditions). A window
  is labelled only if both validity flags are true there.
- **Input:** the 8 × 6 raw pressure values divided by 4095. This fixed physical range is the same in every fold;
  there is no fitted input scaler.
- **Target scaling:** each target is standardised with the mean and standard deviation of the labelled windows of the
  training partition only. Metrics are computed in the original units.

### 3.4. Model and Training

- **Architecture:** a causal residual TCN following the generic TCN design [9]: three blocks (dilations 1,
  2 and 4), two causal convolutions per block with rectified linear unit (ReLU) activation and dropout, a 1×1 convolution on the residual path when the
  channel count changes, and a linear head on the last time step. It predicts temperature and humidity jointly, with
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

Figure 1 summarises the evaluation design.

![Figure 1](../figures/figure1_study_design.png)

**Figure 1.** Study and evaluation design. (a) Data preparation: smart-mat logs with six pressure channels,
temperature and humidity; the audited canonical dataset (checksums, validity flags, sessions); splits defined first,
then 40-s windows of 8 steps × 6 channels; the cohort of three subjects and four mat streams (one subject on two
mats). (b) Strict leave-one-subject-out evaluation: three outer folds, each holding out one subject (labelled
generically A–C) with all its mats; model selection uses two swapped inner splits of the two training subjects only;
the held-out subject is evaluated once; each fold and seed yields a RAW-TCN base model. (c) Chronological
personalization of the held-out subject: the base model is fine-tuned in all parameters for 10 epochs on nights 1…b,
night b + 1 is an unused buffer (for b > 0), and the primary test span (nights ≥ 16) is the same for every budget
b ∈ {0, 1, 3, 7, 14}. (d) Evaluation: per-subject MAE, RMSE and bias with the night-level paired bootstrap of ΔMAE;
post-hoc comparators (constant predictors, the base model plus an adaptation-night offset, a scratch control) and the
residual-variation ratio R; reproduction of the pre-declared models, predictions and tables from the de-identified
release candidate. Schematic only; it contains no data. TCN, temporal convolutional network; MAE, mean absolute
error; RMSE, root-mean-square error.

#### 3.5.1. Strict Leave-One-Subject-Out Evaluation (RQ1)

- **Folds:** each of the three outer folds holds out one subject entirely, including all its mats.
- **Nested selection:** model selection uses only the two training subjects.
  - Two inner splits train on one training subject and validate on the other, then swap.
  - Every configuration is scored with a unit-free criterion: the mean over the two inner splits of
    (MAE_T/sd_T + MAE_H/sd_H)/2, where MAE is the mean absolute error of temperature (T) or humidity (H) and sd
    the standard deviation of the target in the inner training partition.
  - The best configuration is retrained on the whole outer training pool, for the rounded mean of its two inner
    best-epoch counts.
- **Single look:** the held-out subject is evaluated once per model. The selections were committed before any outer
  test evaluation.
- **Reference:** a training-mean predictor, which predicts the training pool's mean temperature and humidity, is
  evaluated on the same folds.

#### 3.5.2. Feature-Family Comparison (RQ3, Secondary)

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
  fails. It targets leakage, i.e. information about the target that would not be available in deployment
  [31], and it enforces subject-wise evaluation as in the intended use [23].
- **Rules checked:**
  - held-out subjects and adaptation/test nights are disjoint from the data used for fitting and selection;
  - concurrent mats stay in one partition;
  - adaptation precedes the buffer and test nights;
  - scalers are fitted on training partitions only;
  - no input is a target, a control code, a calendar field or an identifier;
  - no window crosses a partition boundary.

#### 3.5.5. Post-Hoc Validation Comparators (Protocol Addendum)

These analyses were added after the primary results and a draft of this article were known, to test simpler
explanations of the RQ2 results. Their predictors, statistics, comparisons and interpretation rules were fixed in a
written protocol addendum before any of them was evaluated on the test span. The addendum reuses the frozen data,
splits, windows and models unchanged, and all its results are reported. They are labelled post hoc wherever they
appear and replace no primary result.
- **Predictors on the primary span**, per subject, target and budget:
  - A: the training-mean predictor of the fold (the RQ1 reference);
  - B: A plus an offset c_b, the mean over the labelled adaptation windows of the observed minus the predicted value.
    B therefore equals the mean target of the adaptation windows, a personalized constant that uses no pressure input;
  - C: the RAW-TCN base model;
  - D: C plus its own offset c_b computed in the same way (a bias-calibrated base model);
  - E: full fine-tuning (Section 3.5.3).
  The offsets involve no optimisation, no test label, no scaler refit and no hyperparameter. For User02 one offset is
  estimated from both mats and applied to both, as in fine-tuning. A per-mat offset is reported only as a diagnostic.
- **Initialization control (b = 14):** S is a network with the fold's selected architecture, randomly initialised and
  trained on nights 1–14 with exactly the fine-tuning recipe of Section 3.5.3 and the base model's target scaler.
  - Only the initialisation differs from E. Night 15 is unused, and the evaluation uses nights ≥ 16.
  - With its short fixed schedule, S is an initialization control, not an upper bound on what a within-subject model
    could learn.
- **Residual variation:** for every predictor, the standard deviation (SD) of the error and the SD of the target over
  the same windows (both population SDs), and their ratio R = error SD / target SD.
  - A constant predictor has R = 1, and a constant offset leaves R unchanged. R < 1 therefore indicates that a model
    tracks part of the within-span target variation.
  - R is a descriptive ratio, not explained variance.
- **Comparisons:** ΔMAE = MAE(first) − MAE(second), with the night-level paired bootstrap of Section 3.6 on the same
  resampled nights:
  - D versus E, B versus E and B versus D at every budget;
  - S versus E and B versus S at b = 14.
  A predictor is called better than another in a cell only if the seed-0 interval of the difference excludes zero in
  its favour and its seed-mean MAE is lower.
- **Interpretation rules, fixed before the comparison:**
  - where B is not worse than E, pressure-dependent personalization adds no demonstrated value over a personalized
    constant;
  - where E is better than D, adaptation goes beyond a constant offset of the base model;
  - where S is not better than B at b = 14, the premise that pressure carries usable within-subject information is
    weakened.
- **Leakage control:** every calibration budget and every control run passed the automated gate of Section 3.5.4, and
  explicit checks confirmed that no offset or training window lies in the buffer night or the test span.

#### 3.5.6. Dynamic-Signal Diagnostic (Second-Order Post Hoc)

A residual-variation ratio near one does not show that predictions and targets are uncorrelated. With
Q = prediction SD / target SD and the pooled Pearson correlation r, R² = 1 + Q² − 2·r·Q, so a positive r can coexist
with R ≈ 1 when the prediction scale is mismatched. After the results of Section 3.5.5 were known, a final diagnostic was
therefore added under a further protocol addendum. Its plan, thresholds and interpretation rules were fixed before any
of its metrics was computed. It uses the existing primary-span predictions of the base model, the offset-calibrated base
model, full fine-tuning and the scratch control; nothing was retrained.
- **Metrics:**
  - Q and the pooled correlation r;
  - the within-night correlation, the primary tracking diagnostic: predictions and targets are centred on each
    night's own mean, and the centred values of all nights are correlated;
  - a variant centred within night and mat, which removes the level difference between User02's two mats inside a
    night;
  - R_oracle = √(1 − r²), the smallest R that an affine recalibration fitted on the same test labels could reach. It
    is a retrospective oracle, not a result: such a fit would be leakage.
  - Constant predictors have Q = 0, R = 1 and undefined correlations.
- **Uncertainty:** the night-level bootstrap of Section 3.6 on the same resampled nights, with model seed 0 primary.
- **Classification:** a correlation counts as positive if its seed-0 interval lies above zero and its seed-mean value
  is at least 0.10, a pragmatic magnitude floor, not a significance threshold. For User02, within-night co-variation
  also requires a positive night × mat-centred correlation.
- **Trigger:** a leakage-free affine calibration, fitted on the adaptation windows only, was pre-specified as the only
  possible additional comparator. It was to be run only if R_oracle of the base model was at most 0.90 for at least
  two subjects for the same target.

### 3.6. Metrics and Statistical Analysis

- **Primary endpoints:** MAE and root-mean-square error (RMSE) for temperature (°C) and humidity (%RH), computed
  separately over the labelled
  test windows of each held-out subject (both User02 mats pooled).
  - Results are reported per subject first.
  - The unweighted mean over the three subjects is shown as a description, not as a population estimate.
- **Secondary measures:**
  - the mean signed error (bias, predicted minus observed; negative values mean under-estimation);
  - device and phase strata;
  - the per-budget later span.
  - For RQ2, the adaptation gain G_b = (E_0 − E_b)/E_0, with E the primary-span MAE; positive values mean improvement.
    Negative transfer means that the adapted model is worse than its own base model on the same test nights
    (G_b < 0). A descriptive split of the RMSE into bias and error standard deviation is also reported.
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
    the same mat within 60 min before the target time, used for stratification only;
  - the comparators, the initialization control and the residual-variation ratio of Section 3.5.5, which follow a
    later protocol addendum;
  - the dynamic-signal diagnostic of Section 3.5.6, which follows a second addendum written after those results.

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
- **Reproduced from the release package alone, in a clean checkout, with the frozen selections:**
  - the selected strict leave-one-subject-out models: the nine RAW-TCN base models, whose weights match their frozen
    digests, and their predictions;
  - the predictions of the 45 selected feature-family models (retrained from the frozen selection);
  - the predictions of the 45 personalization runs;
  - the night-level robustness analyses;
  - every prediction file bitwise, every reproduced result table, and the committed result figures byte for byte.
  The manuscript tables are selections of these reproduced tables.
- **Not rerun:** the hyperparameter searches, i.e. the strict leave-one-subject-out inner search for RAW and the
  480-run inner search for the feature families. Their selections were reused as committed. The reproduction is
  therefore not an end-to-end rerun of every experiment.
- **Post-hoc analyses (Section 3.5.5):** rerun from the frozen models into a separate output directory. The rerun
  reproduced every table exactly and the nine control models bitwise. These analyses were not part of the
  reproduction from the release package.
- **Software:** Python 3.12.1, PyTorch 2.12.0 with CUDA 12.6, NumPy 2.4.4, PyArrow 24.0.0 and Matplotlib 3.10.9, with
  deterministic settings; bitwise equality of reruns was verified on the recorded GPU stack. The availability of the
  code is stated in the Data Availability Statement.

### 3.8. Use of Generative AI

Generative AI-assisted tools were used during the research workflow to support research planning, review of the
analysis and protocol documentation, code drafting and debugging, the organization and orchestration of analysis
procedures, research documentation, literature screening and reference-metadata checks, manuscript architecture and
drafting, language refinement and consistency review. The experimental protocol, the dataset policies, the
model-selection rules, the statistical procedures and the interpretation boundaries were determined and reviewed by
the authors, who are also responsible for the final scientific interpretation and for every reported numerical
result. All executable code and reported numerical results were validated independently of the generative-AI
output, through automated tests, frozen-result consistency checks, deterministic table generation and clean-checkout
reproduction (Section 3.7). Every retained reference was checked against its DOI or publisher record. No numerical
result was accepted solely from generative-AI output. The tools and their versions are listed in the
Acknowledgments.

## 4. Results

### 4.1. Strict Leave-One-Subject-Out Generalization

Table 2 reports the held-out errors.

**Table 2.** Strict leave-one-subject-out results. MAE, RMSE and bias (predicted minus observed) of the
training-mean predictor and of the RAW-TCN for temperature (°C) and humidity (%RH), for each of the three held-out
subjects (one outer fold each, evaluated once) and as the unweighted mean across three held-out subjects
(descriptive).
TCN values are means over three model seeds (0, 1, 2); per-seed values are in Table S1. All windows of the
held-out subject are evaluated; both User02 mats are pooled.

| Target | Metric | Predictor | User01 | User02 | User07 | Unweighted mean across three held-out subjects |
|---|---|---|---|---|---|---|
| Temperature (°C) | MAE | Training-mean predictor | 2.73 | 4.59 | 1.82 | 3.05 |
| Temperature (°C) | MAE | RAW-TCN | 3.12 | 4.82 | 2.04 | 3.33 |
| Temperature (°C) | RMSE | Training-mean predictor | 3.18 | 4.99 | 2.17 | 3.44 |
| Temperature (°C) | RMSE | RAW-TCN | 3.79 | 5.26 | 2.53 | 3.86 |
| Temperature (°C) | Bias | Training-mean predictor | +2.64 | −4.59 | +1.10 | −0.29 |
| Temperature (°C) | Bias | RAW-TCN | +1.86 | −4.82 | +1.40 | −0.52 |
| Humidity (%RH) | MAE | Training-mean predictor | 23.06 | 27.63 | 7.99 | 19.56 |
| Humidity (%RH) | MAE | RAW-TCN | 20.28 | 24.59 | 9.97 | 18.28 |
| Humidity (%RH) | RMSE | Training-mean predictor | 24.67 | 31.08 | 9.61 | 21.79 |
| Humidity (%RH) | RMSE | RAW-TCN | 23.24 | 28.98 | 12.29 | 21.51 |
| Humidity (%RH) | Bias | Training-mean predictor | +22.23 | −27.49 | −2.12 | −2.46 |
| Humidity (%RH) | Bias | RAW-TCN | +19.04 | −24.17 | +3.09 | −0.68 |

Notes:

- RAW-TCN MAE higher than the training-mean MAE: temperature in 3 of 3 subjects; humidity in 1 of 3 (User07). Comparison of the MAE rows above.
- Each subject column is one outer fold, evaluated once on all labelled windows of the held-out subject (both User02 mats pooled). RAW-TCN values are means over model seeds 0, 1 and 2 (per seed: Table S1).
- Bias = mean of (predicted − observed); negative values mean under-estimation.
- The unweighted mean across three held-out subjects is descriptive, not a population estimate.

- **Heterogeneity:** the RAW-TCN errors differ strongly between subjects.
  - Temperature MAE: 3.12 °C
    (User01), 4.82 °C (User02) and
    2.04 °C (User07).
  - Humidity MAE: 20.28,
    24.59 and
    9.97 %RH.
- **Temperature: the neural model had a higher MAE than the training-mean predictor for all three held-out
  subjects.**
  - Training-mean MAE: 2.73,
    4.59 and
    1.82 °C.
  - Unweighted means:
    3.33 °C vs
    3.05 °C.
- **Humidity:** the TCN was better than the training mean for User01 and User02 and worse for User07.
  - Training-mean MAE:
    23.06,
    27.63 and
    7.99 %RH.
- **Systematic level offsets:** the errors are largely systematic, and their signs differ between subjects.
  - User02 temperature bias −4.82 °C
    and humidity bias −24.17 %RH.
    For this subject the bias accounts for essentially the whole MAE.
  - User01 humidity bias +19.04 %RH.
- **Seeds:** the spread across the three seeds was much smaller than the differences between subjects (Table S1).
- **Residual variation (post hoc, Table 6):** beyond the level offset, the RAW-TCN's errors varied more than the
  target itself for every subject and target. R ranged from
  1.08
  (User02 temperature) to
  1.86
  (User01 temperature), against R = 1 for the training-mean predictor. The network's pressure-driven variation did
  not follow the target within the held-out subject.

### 4.2. Feature-Family Comparison (Secondary)

This secondary analysis asks whether another representation of the pressure signal removes the level offsets of
Section 4.1. Table 3 compares the six families.

**Table 3.** Feature-family comparison under strict leave-one-subject-out evaluation (secondary analysis). MAE of
the training-mean predictor and of the six TCN feature families for temperature (°C) and humidity (%RH), as the
unweighted mean across three held-out subjects; change relative to RAW (negative = lower error) with the number of
subjects improved, of three; the seed-level consistency of that change (fold–seed pairs, of nine, with a lower MAE
than RAW, and the range of the per-pair change); and the User02 bias, which shows the remaining domain-level offset.
Each family has its own pre-declared nested selection, so the comparison is between selected representations, not a
fixed-model ablation. Seed means over three model seeds; per-subject values are in Tables S4–S7.

| Representation | Temperature MAE (°C) | Δ vs RAW, °C (improved) | Fold–seed pairs improved; Δ range, °C | Humidity MAE (%RH) | Δ vs RAW, %RH (improved) | Fold–seed pairs improved; Δ range, %RH | User02 bias, °C | User02 bias, %RH |
|---|---|---|---|---|---|---|---|---|
| Training-mean predictor | 3.05 | — | — | 19.56 | — | — | −4.59 | −27.49 |
| RAW (reference) | 3.33 | — | — | 18.28 | — | — | −4.82 | −24.17 |
| MOVEMENT | 3.09 | −0.25 (3/3) | 9/9; −0.54 to −0.04 | 19.61 | +1.33 (1/3) | 3/9; −0.41 to +3.52 | −4.73 | −26.49 |
| CONTACT | 3.24 | −0.09 (3/3) | 7/9; −0.37 to +0.10 | 18.01 | −0.27 (2/3) | 4/9; −2.06 to +0.97 | −4.81 | −24.14 |
| RAW+MOVEMENT | 3.12 | −0.21 (3/3) | 8/9; −0.86 to +0.01 | 18.38 | +0.09 (1/3) | 3/9; −1.47 to +2.28 | −4.75 | −23.97 |
| RAW+CONTACT | 3.36 | +0.03 (1/3) | 3/9; −0.18 to +0.26 | 17.73 | −0.55 (3/3) | 7/9; −2.37 to +0.53 | −4.77 | −23.83 |
| RAW+MOVEMENT+CONTACT | 3.30 | −0.03 (2/3) | 5/9; −0.32 to +0.22 | 18.00 | −0.28 (2/3) | 6/9; −1.47 to +1.28 | −4.69 | −23.62 |

Notes:

- Secondary analysis (RQ3).
- MAE: unweighted mean across three held-out subjects of the seed means (seeds 0, 1, 2); descriptive.
- Δ vs RAW = family MAE − RAW MAE (negative = lower error); in brackets the number of subjects, of three, whose MAE improved.
- Seed variation: the family is compared with RAW separately for each held-out subject and model seed (nine fold–seed pairs, same seed for both); the column gives the pairs with a lower MAE and the smallest and largest per-pair Δ.
- Each representation has its own pre-declared nested selection; the comparison is between selected representations, not a fixed-model ablation.
- User02 bias (predicted − observed) shows the domain-level offset that remains in every representation.
- Per-subject values, RMSE and all pre-declared comparisons: Tables S4–S7.

- **Movement → temperature:** movement information helped temperature.
  - MOVEMENT changed the unweighted temperature MAE by
    −0.25 °C relative to
    RAW, improving 3 of three
    subjects.
  - Its humidity MAE worsened by
    +1.33 %RH.
- **Contact → humidity:** RAW+CONTACT changed the unweighted humidity MAE by
  −0.55 %RH, improving
  3 of three subjects.
- **Not additive:** the model with all features ranked
  4
  of six for temperature and
  2 for
  humidity.
- **Effect sizes:** the gains came mostly from User01 and were small compared with the differences between subjects.
- **No representation removed the domain-level offset.**
  - The best temperature family (MOVEMENT,
    3.09 °C) did
    not reach the training-mean predictor
    (3.05 °C).
  - User02 temperature bias ranged from
    −4.82 to
    −4.69 °C across
    the TCN families.
  - User02 humidity bias ranged from
    −26.49 to
    −23.62 %RH (Table S7).

### 4.3. Chronological Personalization

Table 4 and Figures 2 and 3 show the primary-span MAE by subject and budget. The b = 0 values are the base models on
the primary span (nights ≥ 16) only, so they differ from Table 2, which covers all nights. Table 4 also lists the
post-hoc comparators of Section 3.5.5 next to the pre-declared models; they are discussed in Section 4.7.

**Table 4.** Chronological personalization on the common primary test span (nights ≥ 16, identical for every
budget): MAE for temperature (°C) and humidity (%RH) per held-out subject and adaptation budget b of five
predictors. The pre-declared RQ2 models are C (the RAW-TCN base model, b = 0) and E (full fine-tuning, b = 1, 3, 7
and 14 nights), with the adaptation gain G_b = (E_0 − E_b)/E_0 of E (positive = improvement; negative = negative
transfer) and the number of seeds improved, of three. The post-hoc comparators are A (training mean), B (A plus the
adaptation-window offset, i.e. the mean target of the adaptation nights) and D (C plus the adaptation-window offset).
Neural predictors: mean ± standard deviation over three model seeds. Bias and RMSE by budget are in Tables S10 and
S20.

| Target | Subject | b | A: training mean | B: adaptation-target mean | C: RAW-TCN base | D: RAW-TCN + offset | E: full fine-tuning | G_b of E, % (seeds improved) |
|---|---|---|---|---|---|---|---|---|
| Temperature (°C) | User01 | 0 | 2.84 | — | 3.09 ± 0.26 | — | = C | — |
| Temperature (°C) | User01 | 1 | 2.84 | 2.31 | 3.09 ± 0.26 | 4.92 ± 0.29 | 3.14 ± 0.31 | −1.7 (0/3) |
| Temperature (°C) | User01 | 3 | 2.84 | 2.27 | 3.09 ± 0.26 | 3.67 ± 0.22 | 2.85 ± 0.10 | +7.7 (3/3) |
| Temperature (°C) | User01 | 7 | 2.84 | 2.16 | 3.09 ± 0.26 | 2.88 ± 0.20 | 2.31 ± 0.10 | +25.5 (3/3) |
| Temperature (°C) | User01 | 14 | 2.84 | 1.87 | 3.09 ± 0.26 | 2.62 ± 0.14 | 1.75 ± 0.05 | +43.3 (3/3) |
| Temperature (°C) | User02 | 0 | 4.85 | — | 5.06 ± 0.07 | — | = C | — |
| Temperature (°C) | User02 | 1 | 4.85 | 1.98 | 5.06 ± 0.07 | 2.08 ± 0.02 | 4.34 ± 0.03 | +14.3 (3/3) |
| Temperature (°C) | User02 | 3 | 4.85 | 1.81 | 5.06 ± 0.07 | 1.89 ± 0.01 | 2.76 ± 0.32 | +45.5 (3/3) |
| Temperature (°C) | User02 | 7 | 4.85 | 1.81 | 5.06 ± 0.07 | 1.90 ± 0.01 | 1.96 ± 0.04 | +61.3 (3/3) |
| Temperature (°C) | User02 | 14 | 4.85 | 1.49 | 5.06 ± 0.07 | 1.61 ± 0.00 | 1.55 ± 0.03 | +69.4 (3/3) |
| Temperature (°C) | User07 | 0 | 1.59 | — | 1.89 ± 0.16 | — | = C | — |
| Temperature (°C) | User07 | 1 | 1.59 | 2.41 | 1.89 ± 0.16 | 2.12 ± 0.02 | 2.16 ± 0.01 | −14.4 (0/3) |
| Temperature (°C) | User07 | 3 | 1.59 | 2.45 | 1.89 ± 0.16 | 2.18 ± 0.02 | 2.37 ± 0.00 | −25.0 (0/3) |
| Temperature (°C) | User07 | 7 | 1.59 | 2.37 | 1.89 ± 0.16 | 2.10 ± 0.01 | 2.33 ± 0.01 | −23.3 (0/3) |
| Temperature (°C) | User07 | 14 | 1.59 | 2.33 | 1.89 ± 0.16 | 2.07 ± 0.01 | 2.36 ± 0.01 | −25.0 (0/3) |
| Humidity (%RH) | User01 | 0 | 23.72 | — | 20.68 ± 1.34 | — | = C | — |
| Humidity (%RH) | User01 | 1 | 23.72 | 44.63 | 20.68 ± 1.34 | 51.35 ± 0.45 | 27.83 ± 2.28 | −34.6 (0/3) |
| Humidity (%RH) | User01 | 3 | 23.72 | 44.16 | 20.68 ± 1.34 | 47.16 ± 0.96 | 34.19 ± 1.22 | −65.3 (0/3) |
| Humidity (%RH) | User01 | 7 | 23.72 | 35.52 | 20.68 ± 1.34 | 36.09 ± 1.20 | 29.95 ± 0.51 | −44.8 (0/3) |
| Humidity (%RH) | User01 | 14 | 23.72 | 19.09 | 20.68 ± 1.34 | 18.54 ± 0.72 | 16.03 ± 0.42 | +22.5 (3/3) |
| Humidity (%RH) | User02 | 0 | 25.05 | — | 21.98 ± 0.50 | — | = C | — |
| Humidity (%RH) | User02 | 1 | 25.05 | 13.72 | 21.98 ± 0.50 | 15.08 ± 0.04 | 17.29 ± 0.45 | +21.4 (3/3) |
| Humidity (%RH) | User02 | 3 | 25.05 | 15.53 | 21.98 ± 0.50 | 16.71 ± 0.02 | 12.70 ± 0.84 | +42.2 (3/3) |
| Humidity (%RH) | User02 | 7 | 25.05 | 16.69 | 21.98 ± 0.50 | 17.60 ± 0.03 | 14.99 ± 0.21 | +31.8 (3/3) |
| Humidity (%RH) | User02 | 14 | 25.05 | 13.42 | 21.98 ± 0.50 | 14.70 ± 0.04 | 12.23 ± 0.16 | +44.3 (3/3) |
| Humidity (%RH) | User07 | 0 | 8.39 | — | 10.25 ± 0.30 | — | = C | — |
| Humidity (%RH) | User07 | 1 | 8.39 | 8.34 | 10.25 ± 0.30 | 9.89 ± 0.22 | 8.56 ± 0.06 | +16.5 (3/3) |
| Humidity (%RH) | User07 | 3 | 8.39 | 8.31 | 10.25 ± 0.30 | 9.94 ± 0.22 | 8.35 ± 0.05 | +18.6 (3/3) |
| Humidity (%RH) | User07 | 7 | 8.39 | 8.38 | 10.25 ± 0.30 | 9.84 ± 0.22 | 8.38 ± 0.03 | +18.2 (3/3) |
| Humidity (%RH) | User07 | 14 | 8.39 | 8.29 | 10.25 ± 0.30 | 10.28 ± 0.25 | 8.28 ± 0.01 | +19.2 (3/3) |

Notes:

- Primary test span: nights ≥ 16, identical for every budget b (it differs from Table 2, which covers all nights). MAE in °C (temperature) or %RH (humidity).
- C and E are the pre-declared RQ2 models (base model and full fine-tuning); their values and G_b are the primary results. A, B and D are post-hoc comparators (protocol addendum, Section 3.6): A predicts the base model's training-pool mean; D adds to C the offset c_b = mean(y − C) over the labelled adaptation windows of budget b; B adds the same kind of offset to A, which equals the mean target of the adaptation windows. No offset uses a test label; User02 uses one offset for both mats. A and C do not depend on b and are repeated in every row.
- Neural predictors (C, D, E): mean ± standard deviation over model seeds 0, 1 and 2; A and B are deterministic.
- G_b = (MAE_0 − MAE_b) / MAE_0 × 100 % for E, from the seed-mean MAE; G_b > 0 is an improvement and G_b < 0 is negative transfer (the adapted model is worse than its own base model on the same nights). In brackets: seeds, of three, with G_b > 0.
- Unweighted means across the three subjects: Section 4.3 and Figures 2–3. Bias and RMSE by budget: Tables S10 and S20.

![Figure 2](../figures/figure2_temperature_personalization.png)

**Figure 2.** Temperature MAE (°C) of full fine-tuning on the common primary test span versus the adaptation budget
b (b = 0 is the base model; budgets are plotted at their numeric value in nights), for each held-out subject and the
unweighted mean across three held-out subjects (descriptive). Markers: means over three model seeds; bars: seed
minimum–maximum.

![Figure 3](../figures/figure3_humidity_personalization.png)

**Figure 3.** Humidity MAE (%RH) on the common primary test span versus the adaptation budget b, as in Figure 2.

**Cohort curves** (unweighted means, descriptive):
- Temperature MAE:
  3.35,
  3.22,
  2.66,
  2.20 and
  1.89 °C for
  b = 0, 1, 3, 7 and 14.
- Humidity MAE:
  17.64,
  17.89,
  18.41,
  17.77 and
  12.18 %RH. The
  humidity curve is not monotone and improves only at 14 nights.

**The cohort curves hide opposite subject-level effects.**
- **User02 (offset correction):** improved on both targets at every budget.
  - Temperature G reached
    +69.4 % at b = 14.
  - The temperature bias moved from
    −5.06 °C to
    −1.21 °C.
  - Humidity G at b = 14 was
    +44.3 %.
- **User07 temperature (negative transfer):** the seed-mean MAE was higher than that of the base model at every
  adaptation budget.
  - G was −14.4 % at b = 1
    and −25.0 % at b = 14.
  - Seed by seed, each adapted model was worse than its own base model at every budget: seeds improved, of three,
    were 0,
    0,
    0 and
    0 at
    b = 1, 3, 7 and 14. The seed-specific G at b = 14 ranged from
    −35.0 to
    −13.7 %.
  - The night-level interval support for this loss depended on the seed (Section 4.4).
  - Its bias changed sign, from
    +1.13 to
    −2.14 °C.
  - User07 humidity, in contrast, improved (b = 14:
    +19.2 %).
- **User01 humidity (negative transfer, then recovery):** worse than the base model up to seven nights.
  - G was −34.6,
    −65.3 and
    −44.8 % at b = 1, 3 and 7.
  - It was +22.5 % at b = 14.
  - More adaptation data did not improve the result monotonically.
- **User01 temperature:**
  - slightly worse at b = 1
    (−1.7 %);
  - better from b = 3 (+7.7 %);
  - +43.3 % at b = 14.
- **Error decomposition, descriptive:**
  - the User02 temperature gain is almost pure offset correction;
  - User01 temperature at b = 3 and 7 improves mainly through a lower error spread;
  - the User07 temperature loss is a newly introduced offset;
  - humidity changes are dominated by the offset in both directions (Table S9; Figure S1).
- **Low budgets:** one to three adaptation nights did not provide reliable improvement across subjects and targets.

### 4.4. Night-Level Uncertainty and Robustness

Table 5 and Figure 4 give the night-level paired bootstrap intervals of the MAE change (base − adapted; positive =
improvement) for model seed 0.

**Table 5.** Night-level paired cluster bootstrap of the MAE change (base − adapted; positive = improvement) for all
24 subject × target × budget cells (three held-out subjects, two targets, b = 1, 3, 7 and 14). For model seed 0: the
point estimate, the 95 % percentile interval from 2,000 resamples of test nights, and whether the interval lies
above zero, below zero or includes zero. For seeds 1 and 2: the side of zero only (sensitivity). Units: °C for
temperature and %RH for humidity. The intervals describe within-subject night-level uncertainty on the primary span;
they are not population inference.

| Subject | Target | b | ΔMAE | 95 % interval | Seed 0 interval | Seeds 1 / 2 |
|---|---|---|---|---|---|---|
| User01 | Temperature (°C) | 1 | −0.01 | [−0.10, +0.10] | includes zero | 0 / 0 |
| User01 | Temperature (°C) | 3 | +0.02 | [−0.17, +0.21] | includes zero | + / 0 |
| User01 | Temperature (°C) | 7 | +0.56 | [+0.40, +0.72] | above zero | + / + |
| User01 | Temperature (°C) | 14 | +1.10 | [+0.97, +1.24] | above zero | + / + |
| User01 | Humidity (%RH) | 1 | −5.94 | [−6.26, −5.64] | below zero | − / − |
| User01 | Humidity (%RH) | 3 | −13.76 | [−14.19, −13.37] | below zero | − / − |
| User01 | Humidity (%RH) | 7 | −10.49 | [−10.98, −10.05] | below zero | − / − |
| User01 | Humidity (%RH) | 14 | +3.48 | [+2.86, +4.08] | above zero | + / + |
| User02 | Temperature (°C) | 1 | +0.64 | [+0.62, +0.66] | above zero | + / + |
| User02 | Temperature (°C) | 3 | +1.97 | [+1.95, +1.99] | above zero | + / + |
| User02 | Temperature (°C) | 7 | +3.08 | [+3.01, +3.14] | above zero | + / + |
| User02 | Temperature (°C) | 14 | +3.47 | [+3.35, +3.57] | above zero | + / + |
| User02 | Humidity (%RH) | 1 | +4.50 | [+3.64, +5.20] | above zero | + / + |
| User02 | Humidity (%RH) | 3 | +9.69 | [+6.39, +12.64] | above zero | + / + |
| User02 | Humidity (%RH) | 7 | +6.78 | [+1.43, +11.75] | above zero | + / + |
| User02 | Humidity (%RH) | 14 | +9.64 | [+4.86, +14.00] | above zero | + / + |
| User07 | Temperature (°C) | 1 | −0.42 | [−0.80, −0.03] | below zero | 0 / 0 |
| User07 | Temperature (°C) | 3 | −0.61 | [−1.03, −0.16] | below zero | 0 / − |
| User07 | Temperature (°C) | 7 | −0.58 | [−1.01, −0.14] | below zero | 0 / 0 |
| User07 | Temperature (°C) | 14 | −0.61 | [−1.06, −0.16] | below zero | 0 / − |
| User07 | Humidity (%RH) | 1 | +1.48 | [+0.52, +2.43] | above zero | + / + |
| User07 | Humidity (%RH) | 3 | +1.73 | [+0.98, +2.50] | above zero | + / + |
| User07 | Humidity (%RH) | 7 | +1.68 | [+0.84, +2.53] | above zero | + / + |
| User07 | Humidity (%RH) | 14 | +1.79 | [+1.22, +2.36] | above zero | + / + |

Notes:

- ΔMAE = MAE(base) − MAE(adapted) on the primary test span (nights ≥ 16); ΔMAE > 0 means improvement, ΔMAE < 0 negative transfer. Units as in the Target column.
- Seed 0 (primary model seed): full-sample point estimate and 95 % percentile interval from 2,000 paired night-cluster bootstrap resamples of the test nights.
- Seeds 1 / 2: side of zero of their intervals (sensitivity, never pooled): + above zero, − below zero, 0 includes zero.
- All 24 subject × target × budget cells are shown. The intervals describe within-subject night-level uncertainty; an interval that excludes zero is not population-level statistical significance.

![Figure 4](../figures/figure4_night_robustness.png)

**Figure 4.** Night-level paired bootstrap change in MAE, ΔMAE = MAE(base) − MAE(adapted) (ΔMAE > 0: adaptation
better), for model seed 0, with 95 % night-cluster bootstrap percentile intervals, per held-out subject and budget b
(plotted at its numeric value in nights, with the subjects offset slightly for legibility): (a) temperature (°C);
(b) humidity (%RH). The intervals describe within-subject night-level uncertainty only.

- **User02 temperature at b = 14:**
  +3.47 °C
  [+3.35,
  +3.57].
  - Every User02 interval lay above zero, for both targets and all budgets.
  - For humidity at b = 14:
    +9.64 %RH
    [+4.86,
    +14.00].
- **User01 temperature:**
  - the changes at b = 1 and 3 were within night-level uncertainty; at b = 1:
    −0.01 °C
    [−0.10,
    +0.10];
  - the gains at b = 7 and 14 had intervals above zero; at b = 14:
    +1.10 °C
    [+0.97,
    +1.24].
- **User01 humidity:**
  - intervals below zero at b = 1, 3 and 7; at b = 3:
    −13.76 %RH
    [−14.19,
    −13.37];
  - above zero at b = 14:
    +3.48 %RH
    [+2.86,
    +4.08].
- **User07 temperature: the negative-transfer direction was dominant across seeds and start-span analyses, but it was
  not literally invariant for every seed–start combination.**
  - Seed 0: the intervals lay below zero at
    4 of four budgets.
  - Seed 1: at 0
    of four.
  - Seed 2: at 2
    of four.
  - The interval support for this negative transfer therefore depends on the model seed.
- **Start of the test span (post hoc):** moving the start among nights 12, 14, 16, 18 and 21 changed the magnitude of
  the gains, but at the aggregated subject–target–budget level the principal directional findings were stable across
  these start points (Table S17; Figure S2). Seed-level exceptions occurred in borderline cases.
  - For User07 temperature at start night 12 and b = 1,
    1
    of 3
    seeds showed a positive gain.
  - The seed-mean gain was negative there
    (−8.1 %).
  - The User07 temperature loss grew as the test span moved later.

### 4.5. Temporal Level Mismatch (Post Hoc, Descriptive)

Using the targets only (no model), we compared the mean target level of each adaptation span with that of the
primary span (Table S15; Figure S3). Values below are span mean minus primary-span mean.

- **User07 temperature:**
  - the earliest night: −2.22 °C;
  - the 14-night adaptation span:
    −2.09 °C;
  - the base model's training pool:
    +0.71 °C.
  The early nights were cooler than the later period, whereas the training pool was close to it.
- **User01 humidity:** the adaptation spans lay far above the later level:
  - +44.16 %RH
    for b = 3;
  - +19.05 %RH
    for b = 14.
- **User02 temperature:** the adaptation spans were much closer to the later level than the training pool:
  - b = 14: −0.88 °C;
  - training pool: −4.85 °C.
- **Retrospective descriptive rule:** adaptation is expected to help when the adaptation-span level lies closer to the
  later level than the base model's bias.
  - It agreed with the observed direction in
    23 of 24 subject–target–budget cells.
  - The exception was User01 temperature at b = 3, where the gain came from a lower error spread.
  - The rule was formulated after the personalization results were known. The agreement is an association within
    three subjects, not a test of a mechanism.
  - The rule needs the target level of the later nights, which is unknown when a model is adapted. It describes the
    results after the fact and is not a safeguard that a deployment could apply.

### 4.6. Device-Level Residual (User02)

- **Mat 22482 temperature:** a negative residual persisted after adaptation.
  - Bias at b = 14 (seed mean):
    −1.97 °C.
  - Seed-0 night-level interval:
    −1.92 °C
    [−2.23,
    −1.60].
- **Mat 22480:** bias at b = 14 of
  −0.01 °C
  [−0.24,
  +0.23];
  the interval includes zero.
- **Strata:** the 22482 under-estimation persisted in every quality-phase and heater-context stratum with at least ten
  nights (Table S18; Figure S4). Its size differed between heater contexts. For example, the seed-0 bias at b = 14 was
  −1.16 °C
  within 60 min after a heater-off code and
  −2.06 °C
  without a heater code in the preceding 60 min.
- **Per-mat offset (post-hoc diagnostic, added after the primary results were known; Table S22):** an offset
  estimated separately for each mat, instead of one offset for both, lowered the 22482 temperature MAE of the
  adaptation-target mean at b = 14 from
  1.92
  to
  1.41 °C.
  It did not help uniformly: for humidity it lowered the 22480 error and raised the 22482 error at every budget.
  The two mats carry different level offsets, which one pooled offset or one adapted model cannot both remove.
- **Interpretation:** the mats differ in microclimate and control history, and their physical placement is unknown;
  these factors cannot be separated here. The residual is therefore reported as a device-level observation, not as
  evidence of a sensor defect or a heater effect. Heater and controller state, excluded from the inputs, is an
  unobserved contextual factor that may contribute to the microclimate variation the pressure input does not carry.

### 4.7. Post-Hoc Comparators: Level Correction versus Tracking

Table 4 (predictors A, B and D), Table 6, Table 7 and Figure 5 report the post-hoc comparators of Section 3.5.5. They
were added after the primary results were known.

**Table 6.** Residual variation (post hoc): target standard deviation and R = error standard deviation / target
standard deviation for the RAW-TCN under strict leave-one-subject-out evaluation (all labelled windows, the Table 2
setting) and, on the primary test span (nights ≥ 16), for the base model (b = 0), full fine-tuning at b = 14 and the
scratch initialization control at b = 14. A constant predictor has R = 1. Neural models: seed mean, in brackets the
seed range. Target SD in °C for temperature and %RH for humidity.

| Target | Subject | Strict LOSO: target SD | Strict LOSO: R, RAW-TCN | Primary span: target SD | R, base (b = 0) | R, full fine-tuning (b = 14) | R, scratch control (b = 14) |
|---|---|---|---|---|---|---|---|
| Temperature (°C) | User01 | 1.78 | 1.86 (1.73–2.00) | 1.77 | 1.83 (1.70–1.96) | 1.00 (0.99–1.01) | 0.99 (0.99–0.99) |
| Temperature (°C) | User02 | 1.94 | 1.08 (1.07–1.08) | 1.71 | 1.09 (1.08–1.09) | 0.96 (0.94–0.98) | 0.94 (0.93–0.95) |
| Temperature (°C) | User07 | 1.87 | 1.12 (1.09–1.14) | 1.81 | 1.14 (1.11–1.16) | 1.02 (1.02–1.02) | 1.02 (1.02–1.02) |
| Humidity (%RH) | User01 | 10.68 | 1.25 (1.21–1.29) | 8.58 | 1.37 (1.30–1.45) | 1.32 (1.26–1.37) | 1.30 (1.29–1.31) |
| Humidity (%RH) | User02 | 14.49 | 1.10 (1.10–1.11) | 13.76 | 1.09 (1.09–1.10) | 0.99 (0.98–1.00) | 0.97 (0.97–0.97) |
| Humidity (%RH) | User07 | 9.37 | 1.26 (1.23–1.28) | 9.74 | 1.23 (1.19–1.26) | 1.00 (1.00–1.00) | 1.00 (1.00–1.00) |

Notes:

- Post-hoc analysis (Section 3.5.5). R = error SD / target SD, with population standard deviations (error = predicted − observed); R is a descriptive ratio of residual to target variation, not explained variance.
- A constant predictor (the training mean A or the adaptation-target mean B) has R = 1 by construction, and a constant offset leaves R unchanged (D has the R of C). R < 1 means less residual variation than a constant predictor; R > 1 means more.
- Strict LOSO: all labelled windows of the held-out subject (the Table 2 setting). Primary span: nights ≥ 16. Target SD in °C (temperature) or %RH (humidity).
- Neural models: mean over model seeds 0, 1 and 2, in brackets the seed range. Scratch control: the same architecture and fine-tuning recipe as full fine-tuning, randomly initialised and trained on nights 1–14 only. All values: Table S23.

**Table 7.** Post-hoc comparators at b = 14 on the primary test span: MAE of the adaptation-target mean (B), full
fine-tuning (E) and the scratch initialization control (S), and the night-level paired bootstrap differences
ΔMAE = MAE(first) − MAE(second) for B − E, D − E, S − E and B − S (Δ > 0: the second predictor has the lower
error). Seed 0: point estimate and 95 % interval from 2,000 resamples; then the side of zero for seeds 0 / 1 / 2.
Units: °C for temperature and %RH for humidity. The intervals describe within-subject night-level uncertainty only.

| Target | Subject | MAE, B: adaptation-target mean | MAE, E: full fine-tuning | MAE, S: scratch control | Δ B − E | Δ D − E | Δ S − E | Δ B − S |
|---|---|---|---|---|---|---|---|---|
| Temperature (°C) | User01 | 1.87 | 1.75 ± 0.05 | 1.78 ± 0.01 | +0.16 [+0.11, +0.21] +/+/+ | +0.75 [+0.58, +0.91] +/+/+ | +0.06 [+0.03, +0.08] +/−/+ | +0.10 [+0.07, +0.13] +/+/+ |
| Temperature (°C) | User02 | 1.49 | 1.55 ± 0.03 | 1.57 ± 0.05 | −0.04 [−0.10, +0.02] 0/0/− | +0.09 [−0.00, +0.17] 0/0/0 | −0.01 [−0.02, +0.00] 0/+/0 | −0.03 [−0.10, +0.04] 0/−/− |
| Temperature (°C) | User07 | 2.33 | 2.36 ± 0.01 | 2.36 ± 0.03 | −0.04 [−0.06, −0.03] −/−/− | −0.29 [−0.47, −0.11] −/−/− | +0.00 [−0.01, +0.01] 0/−/+ | −0.04 [−0.06, −0.03] −/0/− |
| Humidity (%RH) | User01 | 19.09 | 16.03 ± 0.42 | 15.76 ± 0.31 | +3.31 [+2.75, +3.85] +/+/+ | +3.55 [+2.93, +4.16] +/+/+ | +0.10 [−0.11, +0.32] 0/−/+ | +3.20 [+2.81, +3.59] +/+/+ |
| Humidity (%RH) | User02 | 13.42 | 12.23 ± 0.16 | 11.55 ± 0.28 | +1.35 [+1.03, +1.65] +/+/+ | +2.64 [+2.25, +3.03] +/+/+ | −0.20 [−0.31, −0.08] −/−/− | +1.55 [+1.19, +1.89] +/+/+ |
| Humidity (%RH) | User07 | 8.29 | 8.28 ± 0.01 | 8.28 ± 0.01 | +0.02 [−0.06, +0.11] 0/0/0 | +2.20 [+1.34, +3.04] +/+/+ | +0.02 [−0.02, +0.05] 0/0/0 | +0.01 [−0.06, +0.07] 0/0/0 |

Notes:

- Post-hoc analysis (Section 3.5.5) at b = 14 on the primary span (nights ≥ 16). MAE in °C (temperature) or %RH (humidity); neural models: mean ± standard deviation over model seeds 0, 1 and 2.
- Δ X − Y = MAE(X) − MAE(Y): Δ > 0 means that Y has the lower error. Seed 0: full-sample point estimate and 95 % interval from 2,000 paired night-cluster bootstrap resamples (the Table 5 procedure, with the same resampled nights). Then the side of zero for seeds 0 / 1 / 2: + above zero, − below zero, 0 includes zero.
- D: RAW-TCN base plus the adaptation-window offset (Table 4). S: randomly initialised RAW-TCN of the same architecture, trained on nights 1–14 with the full fine-tuning recipe; only the initialisation differs from E. It is an initialization control, not an upper bound on within-subject learning.
- The intervals describe within-subject night-level uncertainty, not population-level statistical significance. All budgets: Table S25.

![Figure 5](../figures/figure5_posthoc_comparators.png)

**Figure 5.** Post-hoc comparators versus the adaptation budget b (plotted at its numeric value in nights), per
held-out subject: (a–c) temperature MAE (°C); (d–f) humidity MAE (%RH). E: full fine-tuning, starting at the base
model C at b = 0; D: the base model plus the adaptation-window offset, also starting at C; B: the mean target of the
adaptation windows, starting at the training mean A at b = 0; S: the scratch initialization control at b = 14, drawn
slightly to the right of b = 14 for legibility. Markers: seed means; bars: seed minimum–maximum.

- **A personalized constant often matched full fine-tuning.**
  - The adaptation-target mean (B) had a seed-mean MAE no higher than full fine-tuning (E) in
    12 of 24 subject–target–budget cells
    (2 of six at b = 14).
  - By the rule of Section 3.5.5, B was better than E in
    7 cells and E better than B in
    11.
  - **User02 temperature,** the largest correction of Section 4.3: B had the lower seed-mean MAE at every budget. At
    b = 14 it was
    1.49 versus
    1.55 °C
    (ΔMAE B − E
    −0.04 °C
    [−0.10,
    +0.02]).
  - **User01 temperature:** B was better than E up to b = 7, and E was better at b = 14.
  - **Humidity:** E was better than B for User01 at every budget and for User02 from b = 3; for User07, B and E did
    not differ.
  - **Where E was better than B,** its bias on the later span was closer to zero, not its error spread. For User01
    humidity at b = 14 the bias was
    +15.45 %RH for
    E and
    +19.05 %RH for
    B (Table S20).
- **Shifting the base model was not enough, for a revealing reason.**
  - E was better than the offset-calibrated base model D in
    15 of 24 cells. D and E did not differ in
    4, and D was better in
    5.
  - D keeps the base model's residual variation, which exceeded the target variation in every cell. R of the base
    model on the primary span ranged from
    1.09
    to
    1.83
    (Table 6).
  - Full fine-tuning removed most of this excess variation rather than adding tracking.
- **No demonstrable within-subject tracking.** No pressure-based model reduced the error standard deviation clearly
  below the target standard deviation.
  - After 14 nights, R ranged from
    0.96
    to
    1.32
    for full fine-tuning and from
    0.94
    to
    1.30
    for the scratch control.
  - Where the adapted networks had a lower error than the constant, the difference came from their level on the
    later span, not from following the variation within it.
- **Pretraining added little (b = 14; Table 7).**
  - The scratch control (S) was not worse than full fine-tuning in
    5 of six cells.
  - E was better only for User01 temperature: ΔMAE S − E
    +0.06 °C
    [+0.03,
    +0.08];
    for model seed 1 the interval lay below zero instead.
  - S was better than E for User02 humidity.
  - S was better than the adaptation-target mean in
    3 of six cells, the same cells in which E was.
- **User07 temperature: negative transfer without fine-tuning dynamics.**
  - D and E both had a higher seed-mean MAE than the base model C at
    4 of four budgets.
  - The constant B was worse than the training mean A at every budget.
  - An offset estimated from the early nights therefore degraded the later span on its own. D was less harmful than
    E from b = 3 (ΔMAE D − E at b = 14:
    −0.29 °C
    [−0.47,
    −0.11]).

### 4.8. Dynamic-Signal Diagnostic (Second-Order Post Hoc)

Table 8 reports the diagnostic of Section 3.5.6 for the base model, and for full fine-tuning and the scratch control at
b = 14. All budgets and seeds are in Tables S27–S31.

**Table 8.** Dynamic-signal diagnostic (second-order post hoc) on the primary test span: R = error SD / target SD,
Q = prediction SD / target SD, the pooled correlation, the within-night correlation (night-centred values) and the
night × mat-centred variant, and the retrospective oracle ratio R_oracle = √(1 − r²). Values: means over three model
seeds, which are the basis of the case classification; intervals: model seed 0, 95 % night-cluster bootstrap with
2,000 resamples. R_oracle refers to an affine map fitted on the test labels and is therefore a retrospective
diagnostic only.

| Target | Subject | Model | R | Q | r pooled [95 %] | r within night [95 %] | r within night × mat | R_oracle |
|---|---|---|---|---|---|---|---|---|
| Temperature (°C) | User01 | Base model (b = 0) | 1.83 | 1.59 | +0.06 [+0.01, +0.10] | +0.02 [−0.02, +0.04] | +0.02 | 1.00 |
| Temperature (°C) | User01 | Full fine-tuning (b = 14) | 1.00 | 0.26 | +0.14 [+0.11, +0.22] | −0.00 [−0.03, +0.01] | −0.00 | 0.99 |
| Temperature (°C) | User01 | Scratch control (b = 14) | 0.99 | 0.15 | +0.14 [+0.07, +0.16] | +0.01 [−0.02, +0.03] | +0.01 | 0.99 |
| Temperature (°C) | User02 | Base model (b = 0) | 1.09 | 0.24 | −0.26 [−0.33, −0.19] | −0.28 [−0.36, −0.21] | −0.05 | 0.97 |
| Temperature (°C) | User02 | Full fine-tuning (b = 14) | 0.96 | 0.30 | +0.28 [+0.27, +0.40] | +0.31 [+0.30, +0.43] | +0.09 | 0.96 |
| Temperature (°C) | User02 | Scratch control (b = 14) | 0.94 | 0.26 | +0.36 [+0.32, +0.44] | +0.40 [+0.36, +0.47] | +0.12 | 0.93 |
| Temperature (°C) | User07 | Base model (b = 0) | 1.14 | 0.69 | +0.13 [+0.05, +0.18] | −0.02 [−0.05, +0.02] | −0.02 | 0.99 |
| Temperature (°C) | User07 | Full fine-tuning (b = 14) | 1.02 | 0.13 | −0.11 [−0.18, −0.08] | +0.04 [−0.01, +0.07] | +0.04 | 0.99 |
| Temperature (°C) | User07 | Scratch control (b = 14) | 1.02 | 0.10 | −0.14 [−0.20, −0.07] | +0.04 [−0.02, +0.08] | +0.04 | 0.99 |
| Humidity (%RH) | User01 | Base model (b = 0) | 1.37 | 0.94 | +0.01 [−0.04, +0.04] | −0.02 [−0.03, +0.02] | −0.02 | 1.00 |
| Humidity (%RH) | User01 | Full fine-tuning (b = 14) | 1.32 | 0.72 | −0.15 [−0.24, −0.08] | −0.04 [−0.07, −0.02] | −0.04 | 0.99 |
| Humidity (%RH) | User01 | Scratch control (b = 14) | 1.30 | 0.73 | −0.11 [−0.16, −0.05] | −0.07 [−0.10, −0.04] | −0.07 | 0.99 |
| Humidity (%RH) | User02 | Base model (b = 0) | 1.09 | 0.26 | −0.26 [−0.33, −0.19] | −0.37 [−0.45, −0.30] | −0.11 | 0.97 |
| Humidity (%RH) | User02 | Full fine-tuning (b = 14) | 0.99 | 0.24 | +0.17 [+0.14, +0.29] | +0.27 [+0.25, +0.39] | +0.01 | 0.99 |
| Humidity (%RH) | User02 | Scratch control (b = 14) | 0.97 | 0.25 | +0.24 [+0.17, +0.31] | +0.37 [+0.31, +0.43] | +0.02 | 0.97 |
| Humidity (%RH) | User07 | Base model (b = 0) | 1.23 | 0.73 | +0.02 [−0.08, +0.08] | −0.04 [−0.13, +0.01] | −0.04 | 1.00 |
| Humidity (%RH) | User07 | Full fine-tuning (b = 14) | 1.00 | 0.14 | +0.09 [+0.03, +0.16] | +0.04 [−0.00, +0.12] | +0.04 | 1.00 |
| Humidity (%RH) | User07 | Scratch control (b = 14) | 1.00 | 0.10 | +0.08 [+0.00, +0.15] | +0.06 [−0.00, +0.12] | +0.06 | 1.00 |

Notes:

- Second-order post-hoc diagnostic (Section 3.5.6) on the primary span (nights ≥ 16). R, Q, R_oracle and the correlations are means over model seeds 0, 1 and 2, the values the case classification uses; intervals: model seed 0, 2,000 night-cluster bootstrap resamples.
- R = error SD / target SD and Q = prediction SD / target SD (population SDs), with R² = 1 + Q² − 2·r·Q for the pooled correlation r. r within night: correlation of night-centred predictions and targets (primary tracking diagnostic); r within night × mat: centred within night and mat (differs only for User02, whose two mats share each night).
- R_oracle = √(1 − r²) for the pooled r: the smallest R that an affine recalibration fitted on the same test labels could reach. It is a retrospective oracle, not a result: fitting on test labels would be leakage.
- The base model plus the adaptation offset (D in Table 4) has exactly the base model's values; the constant predictors A and B have R = 1, Q = 0 and undefined correlations. All budgets and seeds: Tables S27–S31.

- **No consistent within-night co-variation.** Under the pre-registered rule, the within-night correlation was
  positive in:
  - 0 of six subject–target cells for the base model;
  - 0 of 24 cells for full fine-tuning (all budgets);
  - 1 of six for the scratch control. This was User02
    temperature, with a night × mat-centred correlation of +0.12.
- **Base model: variation without co-variation.**
  - The base model's predictions varied: for User01 temperature they varied more than the target
    (Q = 1.59).
  - Their within-night correlations were near zero for User01 and User07.
  - For User02, the pooled and night-centred correlations were negative, for example
    −0.26 (pooled) for temperature. Centring within night and
    mat left −0.05: most of the association came from the two
    mats' level difference.
- **After adaptation: level alignment between nights or mats.** At b = 14:
  - for User01 temperature, the pooled correlation of full fine-tuning was
    +0.14, and its within-night correlation
    −0.00;
  - for User02 temperature, the night-centred correlation +0.31 fell to
    +0.09 when centred within night and mat.
  These are level alignments between nights or between mats, not within-night tracking. For User07 temperature and
  User01 humidity, the pooled correlations were negative.
- **Little linear headroom.**
  - R_oracle was at least 0.93 in every neural cell (Table S30). Even an affine map fitted on the
    test labels could not have brought the residual standard deviation far below the target standard deviation.
  - The pre-specified trigger for an adaptation-only affine calibration fired for
    0 of two targets, so that comparator was not run.
- **Cases (Table S31):**
  - the cells fell under the pre-registered cases of variation without linear co-variation, between-night association
    only, misaligned association and little calibration headroom;
  - the case of within-night co-variation held in 1 cell;
  - linearly recoverable structure (R_oracle at most 0.90) held in 0.

## 5. Discussion

### 5.1. What Did Personalization Correct?

The post-hoc comparators (Section 4.7) change how the personalization results should be read.
- **Level correction, matched by a constant.** Under strict evaluation, most of the error was a level offset
  (Section 4.1). Chronological personalization reduced this offset when the adaptation nights were representative.
  A constant computed from the same adaptation labels, with no pressure input, did the same: it was not worse than
  full fine-tuning in 12 of 24 cells, including the study's largest correction (User02 temperature).
- **No demonstrable tracking.** The unadapted network's errors varied more than the targets themselves, and after
  fine-tuning the error spread was about that of a constant (Table 6).
  - A direct correlation diagnostic (Section 4.8) found no consistent within-night co-variation.
  - Pooled associations after adaptation reflected level alignment between nights or between mats.
  - Even a retrospective affine recalibration on the test labels would have left the residual variation close to the
    target variation.
  - Where the adapted networks beat the constant, they did so through a different level on the later span. Whether
    that level difference reflects a relation between pressure and microclimate or an incidental association cannot
    be decided with three subjects.
- **Limited value of pretraining.** A randomly initialised network of the same architecture, trained on the
  adaptation nights with the same recipe, reached the error of the pretrained fine-tuning in most cells.
- **Consequence.** Under the tested 40-s RAW-pressure representation, TCN architecture and fixed training and
  adaptation schedules, we found no consistent evidence of superiority over simple level baselines.
  - In this cohort, the evidence supports chronological personalization as a level correction, which simpler
    predictors achieve as well.
  - It does not support within-subject microclimate tracking by this formulation.
  This is the main negative result of the study. It is a result about the tested formulation, not a statement that
  pressure cannot carry microclimate information.

### 5.2. Why Did the Same Recipe Help One Held-Out Domain and Hurt Another?

The results suggest one descriptive account, built from four observations:
- **Offsets dominate the unseen-domain error.** Under strict leave-one-subject-out evaluation, a large part of the
  error is a systematic level offset between the held-out domain and the training pool. For temperature, the
  network did not outperform a training-mean predictor for any held-out subject (Section 4.1).
- **Adaptation moves the level.** Full fine-tuning on a subject's earliest nights tended to move the predictions
  towards the target level of those nights: the bias shifted in the direction of the early-night level for User07
  temperature and User01 humidity (Section 4.3; Table S10). The offset comparators move the level there by
  construction.
- **Representative early levels were associated with improvement; mismatched ones with negative transfer.**
  - When the early level was close to the level of the later nights, the offset shrank: the User02 case, and User01
    humidity once 14 nights were used.
  - When the early level was far from the later one, the model acquired a new offset: User07 temperature at every
    budget and User01 humidity at up to seven nights.
- **Failure of chronological level calibration, not only of fine-tuning.** For User07 temperature, the
  offset-calibrated base model and the adaptation-target mean were also worse than the unadapted predictors
  (Section 4.7). The early nights were not representative of the later period, and every predictor that adopted their
  level failed there. Full fine-tuning's negative transfer (a higher error than its own base model on the same nights)
  is one instance of this.
  - The loss does not arise from the fine-tuning procedure alone: the early nights' level was itself misleading for
    the later period.
  - Fine-tuning added a further loss.

The retrospective level comparison agrees with this account in
23 of 24 cells (Section 4.5). It was formulated after the
results were known and uses the later span's labels, which a deployment does not have. It is descriptive evidence
after the fact, not a confirmatory test and not a deployable safeguard. These observations are consistent with
temporal representativeness being an important condition for successful personalization.

The role of such offsets resembles that of calibration in deployed environmental sensing, where field calibration
corrects systematic sensor errors [29,30]. The pattern also parallels two ideas
from the literature:
- concept drift, a change over time in the relation between inputs and target [14];
- negative transfer from a less related source [15]. Here, the less related data would be the user's
  own earliest nights.
These parallels are interpretive and are not tested in this study. The association is not causation: the
observations do not show that temporal drift causes negative transfer. Three subjects, confounded periods and one
adaptation recipe allow association only.

### 5.3. What the Tested Pressure Formulation Can and Cannot Carry

- **What pressure records:** the body on the mat. Pressure sequences carry information about the person, their
  contact with the mat and their movement (Section 2.1), all of which relate to the microclimate through body heat
  and moisture.
- **What it does not record:** contextual factors that also shape the microclimate:
  - the room's temperature and humidity;
  - bedding and clothing;
  - the heater and its controller;
  - the seasonal climate.
  These factors were unobserved here, and the heater state was excluded from the inputs by design (Section 3.1).
- **Consistency with the results:** within a subject, the pressure-based models did not follow the target variation
  (Table 6), and their within-night correlations with the targets were not consistently positive (Table 8).
- **A plausible limitation (not a demonstrated mechanism): temporal-scale mismatch.**
  - The 40-s pressure window captures short-term contact and movement.
  - The mat microclimate may also depend on longer occupancy history, accumulated thermal conditions, heater and
    controller state, ventilation and other contextual variables unavailable to the model.
  - This study does not test the explanation.
- **Consequence:** in this cohort, a pressure-only input under the tested formulation did not suffice for
  within-subject microclimate estimation.
  - Other formulations were not tested: longer occupancy or history windows, state-space or long-context temporal
    models, contextual variables that are not derived from the target, and explicitly designed calibration
    mechanisms.
  - Contextual measurements would also reduce the sensor savings that motivate the approach.

### 5.4. Feature Engineering and Personalization Address Different Problems

- **Features:** movement and contact features lowered a single subject's error by at most
  −0.50 °C (movement added to
  RAW, User01) and
  −1.29 %RH (contact added to
  RAW, User01). They did so for one target each, mostly for one subject, and they did not reduce the level offsets.
- **Personalization:** changed the level itself, by several degrees for User02, as did a constant computed from the
  adaptation labels.
- **Consequence:** in this setting, a better representation of pressure dynamics is not a substitute for
  information about the target user's level, and that level information did not require the pressure signal.
- **Relation to the conference study:**
  - The previous conference study found relative improvements from movement- and contact-aware pressure
    representations under its original evaluation setting.
  - Table 3 shows the same kind of relative differences between representations under the strict protocol, but no
    representation reached the training-mean predictor for temperature.
  - Relative improvements among neural representations therefore do not, by themselves, establish superiority over
    simple level baselines or unseen-domain validity under subject-wise and chronological evaluation.
  - The present data do not show that the conference results were wrong or caused by leakage.

### 5.5. Personalization Is Not Intrinsically Beneficial

- **Same recipe, both outcomes:** the same frozen recipe produced the largest gain in the study and clear negative
  transfer.
- **Cohort mean:** the unweighted cohort mean improved for temperature but hid a subject that became worse at every
  budget, and for humidity it improved only at 14 nights.
- **Negative results reported in full:**
  - for temperature, the strict leave-one-subject-out TCN was worse than the training-mean predictor for all three
    subjects (Section 4.1);
  - for User07 temperature, the seed-mean MAE was higher than that of the base model at every adaptation budget
    (Sections 4.3–4.4);
  - User01 humidity was worse than its base model at one to seven nights (Sections 4.3–4.4);
  - one to three adaptation nights did not provide reliable improvement (Section 4.3);
  - the interval support for the User07 temperature loss depended on the model seed (Section 4.4);
  - a temperature residual remained on User02's mat 22482 after 14 nights (Section 4.6);
  - a personalized constant was not worse than full fine-tuning in 12 of 24 cells, and no
    pressure-based model showed demonstrable within-subject tracking (Section 4.7);
  - cross-subject pretraining gave limited benefit over the scratch initialization control (Section 4.7).
- **Reporting:** a personalization study that reported only cohort means, or compared only with the unadapted model,
  would miss these failures. Subject-level reporting with night-level uncertainty and personalized constant
  baselines is needed to see them.

### 5.6. More Adaptation Data Can Help, but Not Monotonically

- **User01 humidity:** recovered at 14 nights after being worse at one to seven nights. As the adaptation span grows,
  its level moves closer to the later level (Section 4.5).
- **User07 temperature:** did not recover within 14 nights. Its early nights stayed cooler than the later period
  throughout.
- **Consequence:** how much adaptation data is enough depends on the subject and the target, and in this cohort it
  could not be predicted from the budget alone.

### 5.7. A Device-Level Residual Remains

User02 temperature illustrates both sides:
- a large zero-shot negative bias was mostly corrected;
- the night-level interval of the improvement was narrow and above zero;
- yet one mat kept a negative residual after 14 nights.
Both mats belong to one subject and were adapted jointly. The residual is consistent with one adapted model having to
serve two mat microclimates at once, and a post-hoc per-mat offset reduced it (Section 4.6). Differences between
devices are a known source of error in mobile sensing [12]; here, the mat cannot be separated from its
microclimate and its heater history. The heater and controller state, excluded from the inputs, remains an unobserved
contextual factor. We do not attribute the residual to a device defect, to the heater or to a property of the user.

### 5.8. Practical Implications (Not Tested)

- **Baselines:** an adaptive smart-mat estimator should be compared with a personalized constant computed from the
  same adaptation labels, and its within-night co-variation with the target should be reported. In this cohort, that
  constant was a strong competitor.
- **Commissioning:** in the commissioning scenario of Section 1, the reference labels of the first nights already
  yield the personalized constant. A pressure model adds value only if it improves on that constant in the later
  period, which was not shown here.
- **Safeguards:** the level-mismatch rule of Section 4.5 needs future labels and cannot be applied at deployment.
  Candidates that use only information available at the time exist in neighbouring fields:
  - monitoring drift after adaptation [14], or using adaptive estimators, as for data-driven soft
    sensors [28];
  - periodic recalibration against reference measurements, as for deployed environmental sensors
    [30];
  - selecting or weighting adaptation data.
None of these safeguards was evaluated here; they are future work.

## 6. Limitations

- **Cohort and inference:** the study has three independent primary subjects. Their recording periods do not
  overlap, so subject, recording period, season, mat and microclimate are confounded in every fold. The results
  therefore describe three combined domain shifts; they support no population-level inference and no statistical
  significance across subjects.
- **Post-hoc comparators:**
  - They were designed after the primary results and a draft of this article were known. Their design was fixed
    before they were computed, but the decision to run them was motivated by the results.
  - The initialization control used the short, fixed fine-tuning schedule, one architecture and only b = 14; it is
    not an upper bound on what a within-subject model could learn.
  - R is a descriptive ratio of population standard deviations over spans with drifting levels. R ≈ 1 does not
    exclude a small tracking component masked by noise.
  - The dynamic-signal diagnostic is second-order post hoc: it was added after the comparator results were known,
    although its rules were fixed before it was computed. Its correlations and the oracle ratio are linear
    diagnostics. They do not exclude a nonlinear relation or one at a longer time scale than the 40-s window, and
    night-centring removes between-night trends by design.
- **Inputs and scope:** only pressure was used, in one representation (40-s RAW windows), one model family (TCN)
  and fixed training and adaptation schedules. The negative result is scoped to this formulation. Room climate,
  bedding and the heater and controller state were unobserved; the heater codes were excluded from the inputs under
  the leakage policy.
- **Adaptation design:**
  - One frozen full fine-tuning recipe was evaluated (learning rate, epochs and scope fixed in advance).
  - Adaptation always used the earliest recorded nights, as a deployment would, so its effect is tied to how
    representative those nights are; other samplings of adaptation data were not studied.
  - The commissioning scenario was emulated with the mats' own sensors and not evaluated operationally.
- **Confounded labels:** User01's sensor phases coincide with a change in time and season, so their effects cannot
  be separated. The differences between the two User02 mats have no causal interpretation.
- **Statistics:** the night-level bootstrap resamples nights independently. Consecutive nights are correlated
  through drift, so the intervals may be too narrow for trending series, and the serial dependence between nights is
  not fully captured. The level-mismatch rule was formulated post hoc and uses the later span's labels.
- **Analyses not run:** the declared 20-s and 30-s window sensitivity analyses and a sensitivity analysis for the
  4095 saturation value were not run; the procedures they would need were not fixed in advance.
- **Reproduction scope:** the hyperparameter searches were not rerun; the reproduction reuses their committed
  selections (Section 3.7). The post-hoc analyses were reproduced from the frozen models, not from the release
  package.
- **Release:** the release candidate is derived and model-ready. It contains 40-s windows, not the raw logs, so it
  reproduces this study's analyses but does not support new row-level preprocessing.

## 7. Conclusions

- **Strict evaluation:** in this cohort, smart-mat pressure sequences supported temperature and humidity estimation
  for an unseen domain (a new subject with its own recording period and mat) only up to a large, subject-dependent
  level offset. For temperature, the network did not outperform a training-mean predictor, and alternative pressure
  representations did not remove the offset.
- **Chronological personalization:** removed most of this offset when the earliest nights of the new user
  represented the later period. The same procedure produced negative transfer when they did not, and one to three
  nights were not enough to guarantee benefit.
- **What the gains were:** post-hoc comparators showed that the gains were mainly level corrections.
  - The mean target of the adaptation nights, which needs no pressure input, was not worse than full fine-tuning in
    12 of 24 cells.
  - No pressure-based model showed demonstrable within-subject tracking of temperature or humidity, and the neural
    predictions showed no consistent within-night co-variation with the targets. Where pooled associations appeared,
    they were level alignments between nights or mats.
  - Cross-subject pretraining added little over training on the adaptation nights alone.
- **Consequence:** under the tested 40-s RAW-pressure representation, TCN architecture and fixed training and
  adaptation schedules, pressure-dependent neural prediction did not show a consistent advantage over simple level
  baselines in these three cases. Future work should evaluate other formulations against the same baselines:
  - longer history windows;
  - long-context temporal models;
  - contextual inputs that do not leak the target;
  - explicitly designed calibration;
  - larger cohorts.
  This should happen before pressure-based microclimate estimation is deployed.

## Supplementary Materials

The following supporting information can be downloaded at: https://www.mdpi.com/article/doi/s1, Figure S1: Absolute bias versus the adaptation budget b: (a) temperature, (b) humidity; Figure S2: Start-span
sensitivity of the adaptation gain, post hoc: (a) temperature, (b) humidity, for b = 1, 3, 7 and 14 (for b = 14 only
start nights ≥ 16 are defined); Figure S3: Target-level trajectories over night ordinals for User07 temperature,
User01 humidity and User02 temperature, post hoc and descriptive; Figure S4: User02 MAE by mat (22480, 22482) versus
the adaptation budget b: (a) temperature, (b) humidity; Table S1: Strict leave-one-subject-out results per seed and
training-mean predictor per fold; Table S2: Strict leave-one-subject-out device and phase strata; Table S3: Selected
configurations and inner-selection score ranges; Table S4: Feature families per seed; Table S5: Feature families
versus the training-mean predictor; Table S6: Feature families: per-subject summary, versus RAW and the pre-declared
comparisons A–E; Table S7: Bias and offset by feature family; Table S8: Feature-family device and phase strata;
Table S9: Adaptation gain and error decomposition; Table S10: Personalization RMSE and bias by budget; Table S11:
Personalization on the per-budget later span; Table S12: Personalization per seed; Table S13: Budgets, nights and
windows (night ordinals); Table S14: User02 mat strata and User01 sensor-phase strata; Table S15: Temporal level
mismatch, post hoc and descriptive; Table S16: Night-level bootstrap of RMSE and bias, and seed sensitivity; Table
S17: Start-span sensitivity, post hoc; Table S18: User02 device, quality-phase and heater-context strata; Table S19:
Reproduction record; Table S20: Post-hoc calibration comparators A–E; Table S21: Post-hoc calibration comparators
per seed; Table S22: User02 per-mat calibration diagnostic, post hoc; Table S23: Residual variation, post hoc;
Table S24: Initialization control, post hoc; Table S25: Night-level bootstrap of the comparator differences,
post hoc; Table S26: Pre-registered interpretation map, post hoc; Table S27: Dynamic-signal diagnostic, second-order
post hoc; Table S28: Dynamic-signal diagnostic per seed; Table S29: Night-level bootstrap of the correlations; Table
S30: Retrospective oracle affine ratio and calibration trigger; Table S31: Dynamic-signal cases J1–J8.

## Author Contributions

[CRediT ROLES — CONFIRM] (skeleton in AUTHOR_CONTRIBUTIONS_DRAFT.md; no role is assigned before PI confirmation.)
All authors have read and agreed to the published version of the manuscript. [CONFIRM]

## Funding

[FUNDING TO BE CONFIRMED BY PI] (the conference paper's funding statement is not carried over automatically)

## Institutional Review Board Statement

[ETHICS / IRB INFORMATION REQUIRED FROM PI]

## Informed Consent Statement

[INFORMED CONSENT WORDING REQUIRED FROM PI]

## Data Availability Statement

The raw sensor recordings analysed in this study are not publicly released, and restricted participant metadata is
never released. A de-identified, model-ready derived dataset (`public_release_v1`) has been prepared as a release
candidate. It contains the model-ready windows of the three anonymous participants (four mat streams), the
evaluation splits and the reference digests needed to reproduce the reported results. Time is given only relative to
each participant's first recorded night. External availability of this dataset is pending the choice of a data
license, a repository with a persistent identifier and final approval. [PI DECISION: interim availability on
reasonable request, and from whom.] Data repository: [DATA REPOSITORY]. DOI: [DOI]. License: [LICENSE].

The code for data preparation, model training, evaluation and the reproduction of the reported results is maintained
in a version-controlled research repository. The repository is not released publicly at this stage: its committed
history contains recording-date information outside the de-identified release package, and the scope of a public
code release (for example, a de-identified copy) and its license have not yet been decided. [PI DECISION: public code
release scope and license.] Code repository: [CODE REPOSITORY]. Archive DOI: [DOI]. License: [LICENSE].

From the derived release package and the frozen model selections, a clean
checkout reproduced the selected leave-one-subject-out models (with their weight digests), the predictions of the
feature-family and personalization runs, the night-level analyses and every reproduced result table, bitwise. The
hyperparameter searches were not rerun (Section 3.7).

## Acknowledgments

[OTHER ACKNOWLEDGMENTS — CONFIRM]

During the preparation of this study and manuscript, the authors used Claude Code (Anthropic; CLI versions 2.1.263
and 2.1.270; Claude Opus 5) for assistance with code drafting, debugging, analysis-workflow organization, repository
documentation, reference-metadata checks and manuscript drafting, and ChatGPT (OpenAI; model versions were not
consistently logged across all sessions; GPT-5.6 Sol was used during the final manuscript review) for research
planning, analysis and protocol review, manuscript architecture, manuscript drafting, language refinement, and
consistency review. All AI-assisted outputs were reviewed, edited, and, where applicable, independently verified by
the authors. Experimental protocols, dataset policies, model-selection rules, statistical procedures, reported
numerical results, and scientific interpretations remained under author control. The authors take full
responsibility for the content of this publication.

## Conflicts of Interest

[CONFLICTS OF INTEREST — CONFIRM] (including any funder role, once the funding statement is confirmed)

## Abbreviations

The following abbreviations are used in this manuscript:

| Abbreviation | Definition |
|---|---|
| CRediT | Contributor Roles Taxonomy |
| GenAI | generative artificial intelligence |
| IRB | Institutional Review Board |
| MAE | mean absolute error |
| RAW | the six raw pressure channels (feature family) |
| ReLU | rectified linear unit |
| RH | relative humidity |
| RMSE | root-mean-square error |
| RQ | research question |
| SD | standard deviation |
| TCN | temporal convolutional network |

## References

1. Maeng, D.-H.; Bang, J.-S. Robust Temperature and Humidity Estimation from Smart Bedding Pressure Sequences Using Movement and Contact-Structure Features. In Proceedings of the 18th International Conference on Future Information & Communication Engineering (ICFICE 2026), Sapporo, Japan, 7–10 July 2026; Volume 17, Number 1, pp. 27–30.
2. Liu, J.J.; Xu, W.; Huang, M.-C.; Alshurafa, N.; Sarrafzadeh, M.; Raut, N.; Yadegar, B. A dense pressure sensitive bedsheet design for unobtrusive sleep posture monitoring. In Proceedings of the 2013 IEEE International Conference on Pervasive Computing and Communications (PerCom), San Diego, CA, USA, 18–22 March 2013; pp. 207–215. https://doi.org/10.1109/percom.2013.6526734
3. Yousefi, R.; Ostadabbas, S.; Faezipour, M.; Farshbaf, M.; Nourani, M.; Tamil, L.; Pompeo, M. Bed posture classification for pressure ulcer prevention. In Proceedings of the 2011 Annual International Conference of the IEEE Engineering in Medicine and Biology Society, Boston, MA, USA, 30 August–3 September 2011; pp. 7175–7178. https://doi.org/10.1109/iembs.2011.6091813
4. Carbonaro, N.; Laurino, M.; Arcarisi, L.; Menicucci, D.; Gemignani, A.; Tognetti, A. Textile-Based Pressure Sensing Matrix for In-Bed Monitoring of Subject Sleeping Posture and Breathing Activity. *Appl. Sci.* **2021**, *11*, 2552. https://doi.org/10.3390/app11062552
5. Matar, G.; Lina, J.-M.; Carrier, J.; Kaddoum, G. Unobtrusive Sleep Monitoring Using Cardiac, Breathing and Movements Activities: An Exhaustive Review. *IEEE Access* **2018**, *6*, 45129–45152. https://doi.org/10.1109/ACCESS.2018.2865487
6. Kottner, J.; Black, J.; Call, E.; Gefen, A.; Santamaria, N. Microclimate: A critical review in the context of pressure ulcer prevention. *Clin. Biomech.* **2018**, *59*, 62–70. https://doi.org/10.1016/j.clinbiomech.2018.09.010
7. Mamom, J.; Ratanadecho, P.; Mingmalairak, C.; Rungroungdouyboon, B. Humidity-Sensing Mattress for Long-Term Bedridden Patients with Incontinence-Associated Dermatitis. *Micromachines* **2023**, *14*, 1178. https://doi.org/10.3390/mi14061178
8. Lea, C.; Flynn, M.D.; Vidal, R.; Reiter, A.; Hager, G.D. Temporal Convolutional Networks for Action Segmentation and Detection. In Proceedings of the 2017 IEEE Conference on Computer Vision and Pattern Recognition (CVPR), Honolulu, HI, USA, 21–26 July 2017; pp. 1003–1012. https://doi.org/10.1109/CVPR.2017.113
9. Bai, S.; Kolter, J.Z.; Koltun, V. An Empirical Evaluation of Generic Convolutional and Recurrent Networks for Sequence Modeling. *arXiv* **2018**, arXiv:1803.01271.
10. Hong, J.-H.; Ramos, J.; Dey, A.K. Toward Personalized Activity Recognition Systems With a Semipopulation Approach. *IEEE Trans. Hum. Mach. Syst.* **2016**, *46*, 101–112. https://doi.org/10.1109/THMS.2015.2489688
11. Rokni, S.A.; Nourollahi, M.; Ghasemzadeh, H. Personalized Human Activity Recognition Using Convolutional Neural Networks. *Proc. AAAI Conf. Artif. Intell.* **2018**, *32*. https://doi.org/10.1609/aaai.v32i1.12185
12. Stisen, A.; Blunck, H.; Bhattacharya, S.; Prentow, T.S.; Kjærgaard, M.B.; Dey, A.; Sonne, T.; Jensen, M.M. Smart Devices are Different: Assessing and Mitigating Mobile Sensing Heterogeneities for Activity Recognition. In Proceedings of the 13th ACM Conference on Embedded Networked Sensor Systems, Seoul, South Korea, 2015; pp. 127–140. https://doi.org/10.1145/2809695.2809718
13. Ferrari, A.; Micucci, D.; Mobilio, M.; Napoletano, P. On the Personalization of Classification Models for Human Activity Recognition. *IEEE Access* **2020**, *8*, 32066–32079. https://doi.org/10.1109/ACCESS.2020.2973425
14. Gama, J.; Žliobaitė, I.; Bifet, A.; Pechenizkiy, M.; Bouchachia, A. A survey on concept drift adaptation. *ACM Comput. Surv.* **2014**, *46*, 1–37. https://doi.org/10.1145/2523813
15. Wang, Z.; Dai, Z.; Póczos, B.; Carbonell, J. Characterizing and Avoiding Negative Transfer. In Proceedings of the 2019 IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), Long Beach, CA, USA, 15–20 June 2019; pp. 11285–11294. https://doi.org/10.1109/CVPR.2019.01155
16. Zhang, W.; Deng, L.; Zhang, L.; Wu, D. A Survey on Negative Transfer. *IEEE/CAA J. Autom. Sinica* **2023**, *10*, 305–329. https://doi.org/10.1109/JAS.2022.106004
17. Pouyan, M.B.; Birjandtalab, J.; Zadeh, M.H.; Nourani, M.; Ostadabbas, S. A pressure map dataset for posture and subject analytics. In Proceedings of the 2017 IEEE EMBS International Conference on Biomedical & Health Informatics (BHI), Orlando, FL, USA, 16–19 February 2017; pp. 65–68. https://doi.org/10.1109/BHI.2017.7897206
18. Gefen, A. How do microclimate factors affect the risk for superficial pressure ulcers: A mathematical modeling study. *J. Tissue Viability* **2011**, *20*, 81–88. https://doi.org/10.1016/j.jtv.2010.10.002
19. Yusuf, S.; Okuwa, M.; Shigeta, Y.; Dai, M.; Iuchi, T.; Rahman, S.; Usman, A.; Kasim, S.; Sugama, J.; Nakatani, T.; Sanada, H. Microclimate and development of pressure ulcers and superficial skin changes. *Int. Wound J.* **2015**, *12*, 40–46. https://doi.org/10.1111/iwj.12048
20. Ordóñez, F.; Roggen, D. Deep Convolutional and LSTM Recurrent Neural Networks for Multimodal Wearable Activity Recognition. *Sensors* **2016**, *16*, 115. https://doi.org/10.3390/s16010115
21. Tan, C.W.; Bergmeir, C.; Petitjean, F.; Webb, G.I. Time series extrinsic regression: Predicting numeric values from time series data. *Data Min. Knowl. Discov.* **2021**, *35*, 1032–1060. https://doi.org/10.1007/s10618-021-00745-9
22. Hammerla, N.Y.; Plötz, T. Let's (not) stick together: pairwise similarity biases cross-validation in activity recognition. In Proceedings of the 2015 ACM International Joint Conference on Pervasive and Ubiquitous Computing, Osaka, Japan; pp. 1041–1051. https://doi.org/10.1145/2750858.2807551
23. Saeb, S.; Lonini, L.; Jayaraman, A.; Mohr, D.C.; Kording, K.P. The need to approximate the use-case in clinical machine learning. *GigaScience* **2017**, *6*, gix019. https://doi.org/10.1093/gigascience/gix019
24. Taylor, S.; Jaques, N.; Nosakhare, E.; Sano, A.; Picard, R. Personalized Multitask Learning for Predicting Tomorrow's Mood, Stress, and Health. *IEEE Trans. Affect. Comput.* **2020**, *11*, 200–213. https://doi.org/10.1109/TAFFC.2017.2784832
25. Chang, Y.; Mathur, A.; Isopoussu, A.; Song, J.; Kawsar, F. A Systematic Study of Unsupervised Domain Adaptation for Robust Human-Activity Recognition. *Proc. ACM Interact. Mob. Wearable Ubiquitous Technol.* **2020**, *4*, 1–30. https://doi.org/10.1145/3380985
26. Wilson, G.; Doppa, J.R.; Cook, D.J. Multi-Source Deep Domain Adaptation with Weak Supervision for Time-Series Sensor Data. In Proceedings of the 26th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining, Virtual Event, CA, USA, 2020; pp. 1768–1778. https://doi.org/10.1145/3394486.3403228
27. Pan, S.J.; Yang, Q. A Survey on Transfer Learning. *IEEE Trans. Knowl. Data Eng.* **2010**, *22*, 1345–1359. https://doi.org/10.1109/TKDE.2009.191
28. Kadlec, P.; Grbić, R.; Gabrys, B. Review of adaptation mechanisms for data-driven soft sensors. *Comput. Chem. Eng.* **2011**, *35*, 1–24. https://doi.org/10.1016/j.compchemeng.2010.07.034
29. Maag, B.; Zhou, Z.; Thiele, L. A Survey on Sensor Calibration in Air Pollution Monitoring Deployments. *IEEE Internet Things J.* **2018**, *5*, 4857–4870. https://doi.org/10.1109/JIOT.2018.2853660
30. Delaine, F.; Lebental, B.; Rivano, H. In Situ Calibration Algorithms for Environmental Sensor Networks: A Review. *IEEE Sens. J.* **2019**, *19*, 5968–5978. https://doi.org/10.1109/JSEN.2019.2910317
31. Kaufman, S.; Rosset, S.; Perlich, C.; Stitelman, O. Leakage in data mining: Formulation, detection, and avoidance. *ACM Trans. Knowl. Discov. Data* **2012**, *6*, 1–21. https://doi.org/10.1145/2382577.2382579
