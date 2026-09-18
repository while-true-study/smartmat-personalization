<!--
P13 REVISION: a revised copy of paper/manuscript/manuscript_p10_revision.md, built by
scripts/build_p13_manuscript_revision.py; manuscript.md and manuscript_p10_revision.md are kept unchanged. Changes are
listed in paper/manuscript/REVISION_P13_NOTES.md. New numbers are tokens resolved from paper/tables/p11_*.csv,
p12_*.csv and p13_*.csv (scripts/export_p13_tables.py). Figure 6 and Figure S5 are drawn by
scripts/render_p13_figures.py into paper/manuscript/revision_p13/figures/; Tables S35-S44 are in
paper/manuscript/revision_p13/supplementary/. Render: scripts/render_p13_revision.py; checks:
scripts/validate_p13_revision.py.
P10 REVISION (D-064): a revised copy of paper/manuscript/manuscript.md, which is kept unchanged. Changes are listed in
paper/manuscript/REVISION_P10_NOTES.md. New numbers are tokens resolved from paper/tables/p10_*.csv.
P8 formatting pass: manuscript source of the submission candidate (formatting-complete candidate for PI review).
- Square-bracket items are open placeholders, never facts. Their owners and states are listed in
  docs/P8_FINAL_BLOCKERS.md.
- Result numbers are source tokens {{…}} resolved from paper/tables/ (MANUSCRIPT_NOTES.md). Design parameters of the
  frozen protocol (window length, budgets, resample counts, cohort size) and release facts are written as text.
- {{TABLE:<stem>}} and {{FIGURE:<stem>}} insert the generated assets in paper/manuscript/generated/
  (scripts/export_manuscript_tables.py, scripts/render_manuscript_figures.py).
- The rendered manuscript is paper/submission_candidate/manuscript/manuscript_rendered.md
  (scripts/build_submission_candidate.py); never edit it by hand. scripts/validate_manuscript_results.py checks both.
- Claims follow docs/P8_MANUSCRIPT_PLAN.md §3. Citations are [@key] from references.bib
  (docs/P8_LITERATURE_EVIDENCE_MATRIX.md; audit in docs/P8_CITATION_AUDIT.md).
- No calendar date or month.
-->

<!-- Working title (D-060): neutral evaluation title chosen after the final dynamic-signal diagnostic (v1.2) found no
consistent within-night co-variation, so simple level baselines remain the dominant comparator. PI confirmation
required; the earlier working titles (D-054, D-058) are recorded in docs/P8_TITLE_CANDIDATES.md. -->
# Strict Unseen-Domain Evaluation of Smart-Mat Microclimate Estimation against Simple Level Baselines

<!-- Author metadata: no field is taken from the conference paper; each needs PI confirmation. -->
**Authors:** [AUTHOR NAMES AND ORDER — CONFIRM]

**Affiliations:** [AFFILIATIONS — CONFIRM]

**Corresponding author:** [NAME AND E-MAIL — CONFIRM]

**ORCID:** [ORCID iDs — CONFIRM]

<!-- First-page note: Applied Sciences requires expanded conference papers to cite the conference paper and note it on
the first page (docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md item 15). The wording is the authors'. -->
**Note:** This article is a revised and expanded version of a paper entitled "Robust Temperature and Humidity
Estimation from Smart Bedding Pressure Sequences Using Movement and Contact-Structure Features", which was presented at
the 18th International Conference on Future Information & Communication Engineering (ICFICE 2026), Sapporo, Japan, 7–10 July 2026 [@maeng2026icfice].

<!-- Featured Application: optional in the template. Standalone paragraph, so that it can be removed at formatting
if Applied Sciences does not use it (requirements item 2). No clinical or population claim. -->
**Featured Application:** Smart-mat temperature and humidity estimators should be reported against simple level
baselines under subject-wise and chronological evaluation. In three held-out cases, limited chronological user
adaptation mainly corrected unseen-domain prediction offsets, which a personalized constant often corrected as well,
and no pressure-based model showed within-night co-variation with the measured microclimate beyond a level
difference.

## Abstract

<!-- One paragraph, 190-200 words once the tokens are rendered (checked by scripts/validate_p13_revision.py): problem,
strict design, adaptation design, primary evidence, mixed personalization, the exploratory longer-history result with
the retrained network, the heater competing explanation, and limit. Counts over cells, seeds and audit detail are left
to the body. Every number is a source token. The retrospective level-mismatch agreement is not an abstract headline (D-058):
it uses the later span's labels. -->
Smart-mat pressure could yield bed-microclimate temperature and humidity estimates without extra sensors, but
deployed models face unseen users, periods and mats. We evaluated temporal convolutional networks on 40-s pressure
windows from three subjects (four mat streams) under strict leave-one-subject-out evaluation, each held-out subject being
an unseen domain of subject, period and mat, and fine-tuned them on each subject's earliest 1–14 nights with a fixed
later test span. Errors were dominated by level offsets; for temperature, the network did not beat a training-mean
predictor for any held-out subject. Personalization gave mixed results: a large offset correction in one subject and
degradation in another. A personalized constant was a strong competitor, the adapted predictions were strongly
compressed toward level-dominated behaviour, and no consistent within-night co-variation was found. In exploratory
analyses on endpoints with 15 min of continuous history, gradient-boosted models on 5–15-min pressure summaries
reduced temperature error in {{COUNT:p10_history_interpretation | family=hgb, history_s=900, target=temperature, H_a_beats_training_mean_common=True}} of 3 subjects, and a network retrained on the same endpoints did not change the
primary conclusion. Heater-control context was associated with temperature in the same two subjects, so the
longer-history gain cannot be attributed specifically to pressure. The findings are limited to three retrospective
cases.

<!-- Eight keywords (template: three to ten), chosen to complement the title words rather than repeat them. -->
**Keywords:** smart bedding; pressure sensing; temperature and humidity estimation; temporal convolutional network;
cross-subject generalization; leave-one-subject-out evaluation; negative transfer; baseline comparison

## 1. Introduction

Pressure-sensing mats and bedsheets record a person at rest without wearable devices or cameras. They have been used
to monitor sleep posture [@liu2013dense; @yousefi2011bed] and breathing [@carbonaro2021textile], within a broader
effort to replace laboratory sleep studies by unobtrusive home monitoring [@matar2018unobtrusive]. In care settings,
the microclimate next to the skin (temperature and humidity) is an indirect risk factor for pressure injuries
[@kottner2018microclimate], so the temperature and humidity of the bed microclimate are relevant quantities to
monitor.

These quantities can be measured with sensors built into the mattress [@mamom2023humidity]. Estimating them instead
from signals that a pressure mat already records would avoid adding and maintaining further sensors. Pressure
sequences reflect posture, body contact and movement [@liu2013dense; @carbonaro2021textile]. Whether they also
carry enough information to estimate the local temperature and humidity is not established; it is the question
examined here.

In a previous conference study [@maeng2026icfice], we examined this idea with a temporal convolutional network (TCN)
[@lea2017tcn; @bai2018tcn] that fused raw pressure sequences with movement-derived and contact-structure features.
That study reported gains from both feature types. Because part of the logs lacked second-level timestamps, it
evaluated pragmatic fixed-length sequences, and it stated that its results should not be read as strict elapsed-time
or strict leave-one-subject-out evaluation. It left strict time-based unseen-subject evaluation and user-adaptive
fine-tuning to future work.

These two open questions are the deployment questions. A model trained on some people is used for a new person, in a
new recording period, possibly on another mat and under a different microclimate. Sensor-based models are known to
lose accuracy for new users and on different devices [@hong2016semipopulation; @rokni2018personalized;
@stisen2015smart]. In our data, the new subject, the recording period, the season and the device cannot be
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
[@hong2016semipopulation; @ferrari2020personalization]. It carries a risk that is easy to overlook: the earliest
nights may not represent the later period the model is used in. When the relation between inputs and target changes
over time [@gama2014survey], adaptation can move the model towards a level that no longer holds. Transfer can then
hurt instead of help [@wang2019negative; @zhang2023negative], and adaptation may correct an offset or introduce a new
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
targets (Section 3.5.6). Exploratory analyses then checked whether these readings depend on the choice of constant
(mean or median) and whether simple pressure-summary models with histories of up to 15 min beat the level baseline
under strict leave-one-subject-out evaluation; the network was retrained on the same endpoints, and heater-control
context was examined as a competing explanation (Sections 3.5.8–3.5.9). The question that these
post-hoc analyses address, how much of the personalization gain is level correction and whether pressure adds
tracking beyond it, became explicit only after the primary results were known.

The contributions are:
1. A leakage-controlled strict leave-one-subject-out evaluation of smart-mat temperature and humidity estimation
   across three held-out subjects under a combined subject–period–season–device shift, with a training-mean
   reference (RQ1).
2. A chronological personalization evaluation with 0, 1, 3, 7 and 14 adaptation nights on a common future test span,
   reported per subject and target, which shows both large offset corrections and clear negative transfer (RQ2).
3. A post-hoc comparator analysis showing that the personalization gains were mainly level corrections: a
   personalized constant (the adaptation-night target mean) was a strong competitor to full fine-tuning, the adapted
   predictions were strongly compressed toward level-dominated behaviour, the pressure-based models showed no
   demonstrable within-subject tracking of the targets, and cross-subject pretraining did not provide consistent
   additional predictive value over target-only training under the tested fixed adaptation protocol. A final
   diagnostic found no consistent within-night co-variation between the neural
   predictions and the targets once the level difference between one subject's two mats was removed, and little
   retrospective linear-calibration headroom.
4. An exploratory scope check with median constants and with ridge and gradient-boosted models on 40-s, 5-min and
   15-min pressure summaries, on endpoints with 15 min of continuous history. It narrows the negative result: a
   gradient-boosted model reduced the temperature error relative to the training mean in {{COUNT:p10_history_interpretation | family=hgb, history_s=900, target=temperature, H_a_beats_training_mean_common=True}} of 3 held-out
   subjects, through a smaller offset and without within-night co-variation; the network retrained on the same
   endpoints left the primary conclusion unchanged; and heater-control context, which was associated with
   temperature in the same two subjects, remains a competing explanation that cannot be separated from pressure
   history.
5. A night-level robustness analysis: a paired cluster bootstrap, seed and start-span sensitivity, and post-hoc
   temporal level-mismatch and device-residual diagnostics.
6. A secondary comparison of six pressure feature families under the same protocol. It shows target-dependent,
   non-additive contributions of movement and contact features and a level offset that no representation removes
   (RQ3).
7. A de-identified, model-ready release candidate from which the selected models, the predictions and the result
   tables were reproduced in a clean checkout; the hyperparameter searches were not rerun (Section 3.7).

**Relation to the conference study.** The conference study [@maeng2026icfice] evaluated a late-fusion framework for
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
  [@liu2013dense; @yousefi2011bed], in the latter case explicitly for pressure-injury prevention.
- Public pressure-map data sets support posture and subject analytics [@pouyan2017pressure].
- A textile pressure matrix integrated into a mattress has characterised posture and movement and extracted breathing
  activity [@carbonaro2021textile].
- These systems belong to a wider move towards unobtrusive sleep monitoring outside the laboratory
  [@matar2018unobtrusive].

The bed microclimate has a separate clinical motivation:
- The skin microclimate is regarded as an indirect pressure-injury risk factor
  [@kottner2018microclimate].
- Modelling indicates that higher temperature and humidity lower skin tolerance [@gefen2011microclimate].
- Microclimate differences have been observed between patients who did and did not develop skin damage
  [@yusuf2015microclimate].
- Where the microclimate is monitored, this has been done with dedicated sensors, such as humidity sensors built into
  a mattress [@mamom2023humidity], or as part of a smart bed that also collects environmental data next to its
  pressure layer [@carbonaro2021textile].

These studies use pressure to infer posture, movement or breathing, or they measure temperature and humidity
directly. In the studies reviewed here, the microclimate is measured, not estimated from the pressure signal. Our
conference study examined it with fused pressure representations, but it did not evaluate unseen users or adaptation
[@maeng2026icfice]. The present work treats pressure-based temperature and humidity estimation as an open deployment
problem rather than as an established capability.

### 2.2. Temporal Models for Sensor Regression

- **TCNs:** temporal convolutional networks were introduced as hierarchies of temporal convolutions for fine-grained
  action segmentation [@lea2017tcn]. A generic TCN built from causal and dilated convolutions with residual blocks was
  later evaluated against recurrent networks and performed better on the benchmark tasks studied, with a longer
  effective memory [@bai2018tcn].
- **Wearable sensors:** deep networks that learn features directly from raw sequences and model their temporal
  dynamics have been proposed for sensor-based recognition [@ordonez2016deep].
- **Our task:** estimating the current temperature and humidity from a window of past and present pressure values is
  a regression from a time series to continuous values, known as time series extrinsic regression. It is distinct
  from forecasting and from classification [@tan2021tser].
- **Use in this study:** we use the TCN as a well-studied model family for this setting. We do not claim that it is
  superior to recurrent alternatives, which were not compared.

### 2.3. Cross-Subject Generalization and Personalization

**Evaluation.** How generalization to new people is measured matters:
- Random cross-validation over segmented sensor time series is optimistic, because adjacent segments are not
  independent [@hammerla2015pairwise].
- Record-wise validation can grossly overestimate accuracy for new subjects, whereas subject-wise validation mirrors
  that use case [@saeb2017usecase].

**Generalization failures:**
- Individual diversity limits population models of human activity [@hong2016semipopulation].
- Recognition accuracy drops for new users or when a user's condition changes [@rokni2018personalized].
- One-size-fits-all models perform poorly when outcomes vary between individuals [@taylor2020personalized].
- Heterogeneity between devices [@stisen2015smart] and sensor placements [@chang2020systematic] degrades recognition
  further.

**Responses:**
- personalization with small amounts of the new user's data, or with similar users [@hong2016semipopulation;
  @ferrari2020personalization];
- transfer learning with minimal user supervision [@rokni2018personalized];
- personalized multitask models [@taylor2020personalized];
- domain adaptation for time-series sensor data [@wilson2020multisource]. Its assumptions can fail in practice
  [@chang2020systematic].

**Scope gap:** most of this work concerns activity or state recognition. Less examined is the regression of
continuous environmental quantities for an unseen user under a combined shift of subject, recording period, season
and device. The same holds for personalization data taken chronologically from the start of deployment and evaluated
on a fixed later span. The present study addresses this setting with three subjects, so it describes cases rather
than population effects.

### 2.4. Negative Transfer, Temporal Drift and Calibration

- **Transfer learning** addresses the case in which training data and the data of later use follow different
  distributions [@pan2010survey]. Its benefit is not guaranteed: transfer from a less related source can reduce
  target performance, which is known as negative transfer [@wang2019negative]. This long-standing problem has
  motivated many remedies [@zhang2023negative].
- **Concept drift:** the relation between inputs and target may also change over time [@gama2014survey]. For
  data-driven soft sensors, which estimate quantities indirectly, adaptation mechanisms such as moving windows,
  recursive updates and ensembles have been organised around this concept-drift view [@kadlec2011adaptation].
- **Calibration:** low-cost environmental sensors are error-prone in the field and drift over time. Calibration and
  in situ recalibration have been used to maintain data quality in long-term deployments
  [@maag2018calibration; @delaine2019insitu].

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
leakage policy (Section 3.5.4), so no model in this study observes the heater and controller state. The heater on/off
codes were used only after the fact, as a descriptive stratifier (Section 3.5.9 and Section 3.6). The
temperature–humidity sensor model, its accuracy and response time,
and its position relative to the body and the heater are not documented in the delivered data and are not assumed here
[TEMPERATURE–HUMIDITY SENSOR MODEL, ACCURACY AND PLACEMENT — CONFIRM WITH DATA PROVIDER].

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
  primary protocol. One of them, from a further subject, is used post hoc for an additional external validation
  (Section 3.5.7). The conference study's recordings without second-level timestamps are consistent with this retained
  legacy minute-resolution lineage; exact file-level identity is not assumed.

Table 1 summarises the cohort and the protocol.

**Table 1.** Cohort, data and protocol summary. One row per subject (three subjects, four mat streams); User02's two
mats are one subject and always share a partition. Columns: mat streams; recording sessions (per mat for User02);
the leave-one-subject-out fold in which the subject is held out; labelled 40-s windows; primary test nights
(nights ≥ 16) and primary test windows of chronological personalization. Counts only; no performance values; nights
are counted, never dated.

{{TABLE:table1_dataset_protocol}}

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
  - User01's sensor phases s1 and s2, before and after a documented replacement of the **pressure** sensor (a
    study-log note of the data provider; no replacement of the temperature–humidity sensor is documented). The
    adaptation nights of every budget lie in s1, whereas the primary test span (nights ≥ 16) contains both s1 and s2
    nights. A large change in User01's humidity level, seen in the data audit across a recording gap inside the
    seven-night adaptation span, precedes this replacement; its cause (season, heating, bedding or acquisition) is not
    identified;
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
    independent, and random splits over them would overstate accuracy for new users [@hammerla2015pairwise].
    Windows for personalization are also cut at night boundaries.
- **Target:** the temperature and humidity of the row at the last step (current, not future, conditions). A window
  is labelled only if both validity flags are true there.
- **Input:** the 8 × 6 raw pressure values divided by 4095. This fixed physical range is the same in every fold;
  there is no fitted input scaler.
- **Target scaling:** each target is standardised with the mean and standard deviation of the labelled windows of the
  training partition only. Metrics are computed in the original units.

### 3.4. Model and Training

- **Architecture:** a causal residual TCN following the generic TCN design [@bai2018tcn]: three blocks (dilations 1,
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

{{FIGURE:figure1_study_design}}

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
  Because the number of epochs is fixed, the number of optimizer updates grows with the number of adaptation windows
  (Table S13): budgets differ in both data and update count.

#### 3.5.4. Leakage Control

- **Automated gate:** an automated check runs before every training or evaluation run. It stops the run if any rule
  fails. It targets leakage, i.e. information about the target that would not be available in deployment
  [@kaufman2012leakage], and it enforces subject-wise evaluation as in the intended use [@saeb2017usecase].
- **Rules checked:**
  - held-out subjects and adaptation/test nights are disjoint from the data used for fitting and selection;
  - concurrent mats stay in one partition;
  - adaptation precedes the buffer and test nights;
  - scalers are fitted on training partitions only;
  - no input is a target, a control code, a calendar field or an identifier;
  - no window crosses a partition boundary.

#### 3.5.5. Post-Hoc Validation Comparators (Protocol Addendum)

These analyses were added after the primary results were known, to test simpler
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

#### 3.5.7. Additional External Validation on a Further Subject (Post Hoc)

After the analyses above, one further subject (User03) was evaluated as an additional external sensitivity subject,
under a third protocol addendum written before any of its data were windowed or scored. User03 is not added to the
primary cohort, its results are not pooled with the three primary subjects, and no personalization is evaluated on it.
- **Data:**
  - User03's valid export has minute-resolution timestamps, which the window rule cannot use.
  - A complementary export of the same seven nights carries second-level timestamps. It comes from a source that
    was otherwise excluded after the data provider reported a setting problem.
  - Rows were reconstructed only for minutes in which both exports had the same number of rows and every row pair
    had identical pressure, temperature and humidity values in file order.
  - The second-level timestamp was taken from the complementary export and the values from the valid export.
  - Nothing was interpolated, imputed, re-timed or joined by nearest neighbour.
  - The data provider has since confirmed that the setting problem does not affect that export's second-level
    timestamps for these seven nights, so these results are not conditional on that question. The source remains
    excluded for every other purpose, and no value of it enters the reconstruction.
- **Processing:** the reconstructed rows were processed with the canonical dataset rules and the window rule of
  Section 3.3, as a strict leave-one-subject-out held-out subject.
- **Models:**
  - The three strict leave-one-subject-out folds had selected different configurations, and none could be chosen
    without using the new subject. All three were therefore trained, each with its frozen epoch count, on all
    labelled windows of the three primary subjects, with seeds 0, 1 and 2.
  - Comparator: the training-mean predictor of the same windows.
  - The new subject was used only for evaluation.
- **Metrics:** those of Sections 3.5.5–3.5.6.
- **Rules, fixed in advance:**
  - A predictor is better if every configuration's seed-mean MAE, and its per-night MAE on at least two-thirds of
    the nights, favour it.
  - Within-night co-variation is supported only if every configuration reaches a within-night correlation of at
    least 0.10 with positive per-night correlations on at least two-thirds of the nights.
  - Night-cluster intervals require at least 10 nights (Section 3.6).

#### 3.5.8. Exploratory Analysis: Median Constants and Pressure-Summary Histories (Post Hoc)

A fourth protocol addendum was written with all results above known and before any of its metrics was computed. It is
exploratory and replaces no result above.
- **Reproduction check:** the frozen training-mean, network and control predictions were paired window by window with
  windows rebuilt from the canonical dataset and the frozen splits, and their metrics had to equal the frozen tables to
  an absolute tolerance of 10⁻⁹.
- **Median constants:** the median target of the training pool and of the adaptation nights (User02: both mats pooled),
  evaluated like the means; one deterministic value each.
- **Pressure-summary histories (strict leave-one-subject-out only):** for each 40-s endpoint, histories of 40 s, 300 s
  and 900 s ending at it, built with the window rule of Section 3.3 (5-s bins, last observation per bin, gaps of at most
  5 s, no crossing of session, phase or partition boundaries, no future rows). Per channel, seven statistics of the
  scaled steps (mean, SD, minimum, maximum, last value, net change and the sum of absolute step changes): 42 features.
  No cross-channel, geometric, calendar or control feature.
- **Models:** ridge regression and histogram gradient boosting with small fixed grids, selected with the inner criterion
  of Section 3.5.1 on the training subjects only and refit on the training pool.
- **Common endpoints:** training, selection and evaluation used only endpoints with all three histories available; the
  constants were recomputed on the common training endpoints.
- **RAW-TCN on the common endpoints (training-pool control):** so that every learned model shares one training pool,
  the RAW-TCN was retrained on the common training endpoints. Its input remained the original 40-s window; it is not
  a 900-s network, and only the source training endpoints were restricted to the set with 900 s of continuous history.
  The architecture and hyperparameters selected in Section 3.5.1 were kept; only the number of epochs was re-derived,
  with the unchanged inner rule of Section 3.5.1 on the common inner splits, and the target scaler was fitted on the
  common training endpoints of the two source subjects. Seeds 0, 1 and 2 were trained. The held-out subject was used
  neither for the epoch selection nor for any scaler. The network trained on all 40-s windows is reported as a
  training-pool sensitivity reference (Table S38).
- **Reading, fixed in advance:** a model beats the level baseline if the night-level paired bootstrap interval of
  MAE(training mean) − MAE(model) lies above zero; variation beyond level requires R < 1 and a night-centred
  correlation of at least 0.10 (for User02 also within night and mat). Longer history is associated with lower error
  if the interval of MAE(40 s) − MAE(longer history) lies above zero. The retraining of the network and the same
  reading for it, with model seed 0 primary, were fixed in a separate addendum before the network was retrained. None
  of these readings implies a thermal time constant.

#### 3.5.9. Heater-Context Diagnostic (Post Hoc, Descriptive)

A separate addendum, written with all results above known and before any of its statistics was computed, examined heater
and controller context as a competing explanation of the longer-history results. It is a descriptive confound
diagnostic, not a predictive analysis: no heater or controller information enters any model.
- **Heater context:** for each labelled window, the most recent heater-on or heater-off code on the same mat within
  60 min before the target time (the definition of Section 3.6, applied to all three subjects); windows without such a
  code have an unknown context. The context names the last code, not a reconstructed heater state.
- **Association:** η², the share of the observed target variance associated with the three heater contexts, for the
  raw target and after centring the target within each night; for User02 also after centring within night and mat.
  The night × mat centring is a nuisance-adjusted sensitivity diagnostic: it shows whether the association depends on
  level differences between the two mats. It is not a physical device correction, it does not identify a device
  effect, and it does not show the absence of a dynamic pressure–target relation.
- **Heater-conditioned source constant (diagnostic comparator):** for each held-out subject, the mean target of the
  source training windows in each heater context; windows with an unknown context, and any context absent from the
  source pool, receive the overall source mean. It was compared with the source mean and median on the common
  endpoints of Section 3.5.8. The held-out subject's labels were never used in a fit.
- **Uncertainty:** the night-level paired bootstrap of Section 3.6 for MAE(source mean) − MAE(heater-conditioned
  constant), and night-cluster intervals for η².
- **Reading:** heater codes are issued by the controller in response to the measured thermal state, so they may depend
  on the target itself. The diagnostic is read as an association with the recording and control state, never as a
  causal heater exposure, and the conditioned constant is not an admissible estimator.

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
- **Units of independence:** the three subjects are the independent units. Nights, windows and model seeds are nested
  within them and are not independent replicates. The 24 subject–target–budget cells share subjects, targets and base
  models, so counts over cells are descriptive summaries, not 24 independent tests.
- **Post-hoc analyses:** defined in a written plan before they were computed, but after the personalization results
  were known. They are labelled post hoc and descriptive:
  - robustness of the gains to the start of the test span (nights ≥ 12, 14, 16, 18 or 21);
  - the difference between the mean target level of the adaptation nights and that of the later nights;
  - User02 strata by mat, quality phase and heater context. Heater context is the most recent heater on/off code on
    the same mat within 60 min before the target time, used for stratification only; the heater-context diagnostic of
    Section 3.5.9 applies the same definition to all three subjects;
  - the comparators, the initialization control and the residual-variation ratio of Section 3.5.5, which follow a
    later protocol addendum;
  - the dynamic-signal diagnostic of Section 3.5.6, which follows a second addendum written after those results;
  - the additional external validation of Section 3.5.7, which follows a third addendum;
  - the exploratory analysis of Section 3.5.8 and the heater-context diagnostic of Section 3.5.9.

### 3.7. Reproducibility

- **Release:** a de-identified, model-ready release candidate was derived from the canonical dataset for
  reproduction:
  - 575,265 40-s windows of the three subjects (four mat streams), with raw pressure, targets, validity flags and
    window-set membership;
  - the evaluation splits;
  - User02's heater codes, used for stratification;
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
- **Exploratory analyses (Sections 3.5.8–3.5.9):** they use the canonical dataset, not the release package.
  - The pressure-summary analysis was rerun into a separate output directory, and every table and every prediction
    file was identical; it used scikit-learn 1.8.0 in addition.
  - The network retrained on the common endpoints was trained in one recorded execution, with fixed seeds 0, 1 and 2,
    the frozen configuration and the pre-specified epoch rule; this execution was not repeated.
  - The heater-context diagnostic was run twice into separate output directories, with identical tables. It needs the
    heater codes of all three subjects, which the release candidate does not contain, so it cannot be reproduced from
    the release package alone.
- **Software:** Python 3.12.1, PyTorch 2.12.0 with CUDA 12.6, NumPy 2.4.4, PyArrow 24.0.0 and Matplotlib 3.10.9, with
  deterministic settings; bitwise equality of reruns was verified on the recorded GPU stack. Reproducibility shows
  that the reported numbers follow from the data and code; it does not establish the validity of the measurements or
  any physical explanation. The availability of the
  code is stated in the Data Availability Statement.

### 3.8. Use of Generative AI

<!-- OPEN-28: wording drafted from the recorded tool inventory and the authors' statement; the PI approves it before
submission (D-052). -->
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

{{TABLE:table2_strict_loso}}

- **Heterogeneity:** the RAW-TCN errors differ strongly between subjects.
  - Temperature MAE: `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | User01 | .2f}}` °C
    (User01), `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | User02 | .2f}}` °C (User02) and
    `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | User07 | .2f}}` °C (User07).
  - Humidity MAE: `{{p3_primary_summary | model=tcn_raw, target=humidity, metric=mae | User01 | .2f}}`,
    `{{p3_primary_summary | model=tcn_raw, target=humidity, metric=mae | User02 | .2f}}` and
    `{{p3_primary_summary | model=tcn_raw, target=humidity, metric=mae | User07 | .2f}}` %RH.
- **Temperature: the neural model had a higher MAE than the training-mean predictor for all three held-out
  subjects.**
  - Training-mean MAE: `{{p3_primary_summary | model=training_mean, target=temperature, metric=mae | User01 | .2f}}`,
    `{{p3_primary_summary | model=training_mean, target=temperature, metric=mae | User02 | .2f}}` and
    `{{p3_primary_summary | model=training_mean, target=temperature, metric=mae | User07 | .2f}}` °C.
  - Unweighted means:
    `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | unweighted_subject_mean | .2f}}` °C vs
    `{{p3_primary_summary | model=training_mean, target=temperature, metric=mae | unweighted_subject_mean | .2f}}` °C.
- **Humidity:** the TCN was better than the training mean for User01 and User02 and worse for User07.
  - Training-mean MAE:
    `{{p3_primary_summary | model=training_mean, target=humidity, metric=mae | User01 | .2f}}`,
    `{{p3_primary_summary | model=training_mean, target=humidity, metric=mae | User02 | .2f}}` and
    `{{p3_primary_summary | model=training_mean, target=humidity, metric=mae | User07 | .2f}}` %RH.
- **Systematic level offsets:** the errors are largely systematic, and their signs differ between subjects.
  - User02 temperature bias `{{p3_primary_summary | model=tcn_raw, target=temperature, metric=bias | User02 | +.2f}}` °C
    and humidity bias `{{p3_primary_summary | model=tcn_raw, target=humidity, metric=bias | User02 | +.2f}}` %RH.
    For this subject the bias accounts for essentially the whole MAE.
  - User01 humidity bias `{{p3_primary_summary | model=tcn_raw, target=humidity, metric=bias | User01 | +.2f}}` %RH.
- **Seeds:** the spread across the three seeds was much smaller than the differences between subjects (Table S1).
- **Choice of constant (exploratory, Section 3.5.8):** with the training median instead of the mean, the constant still
  had a lower temperature MAE than the RAW-TCN for User02 and User07, but not for User01
  (`{{p10_loso_metrics | subject_id=User01, target=temperature, predictor=training_median, seed= | mae | .2f}}` °C). The statement for temperature above is
  specific to the mean.
- **Residual variation (post hoc, Table 6):** beyond the level offset, the RAW-TCN's errors varied more than the
  target itself for every subject and target. R ranged from
  `{{p8_residual_variation | setting=strict_loso, subject_id=User02, target=temperature, budget_nights=, predictor=C | R | .2f}}`
  (User02 temperature) to
  `{{p8_residual_variation | setting=strict_loso, subject_id=User01, target=temperature, budget_nights=, predictor=C | R | .2f}}`
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

{{TABLE:table3_feature_family}}

- **MOVEMENT, temperature:** movement-derived features reduced the temperature MAE relative to RAW in
  `{{p4_vs_raw | family=MOVEMENT, target=temperature, metric=mae | improved_subjects | d}}` of three held-out subjects,
  although the unweighted mean remained close to the training-mean baseline (see below).
  - MOVEMENT changed the unweighted temperature MAE by
    `{{p4_vs_raw | family=MOVEMENT, target=temperature, metric=mae | delta_unweighted_mean | +.2f}}` °C relative to
    RAW.
  - Its humidity MAE worsened by
    `{{p4_vs_raw | family=MOVEMENT, target=humidity, metric=mae | delta_unweighted_mean | +.2f}}` %RH.
- **RAW+CONTACT, humidity:** RAW+CONTACT changed the unweighted humidity MAE by
  `{{p4_vs_raw | family=RAW+CONTACT, target=humidity, metric=mae | delta_unweighted_mean | +.2f}}` %RH, improving
  `{{p4_vs_raw | family=RAW+CONTACT, target=humidity, metric=mae | improved_subjects | d}}` of three subjects.
- **Not additive:** the model with all features ranked
  `{{p4_primary_summary | model=RAW+MOVEMENT+CONTACT, target=temperature, metric=mae | rank_among_tcn_families | s}}`
  of six for temperature and
  `{{p4_primary_summary | model=RAW+MOVEMENT+CONTACT, target=humidity, metric=mae | rank_among_tcn_families | s}}` for
  humidity.
- **Effect sizes:** the gains came mostly from User01 and were small compared with the differences between subjects.
- **No representation removed the domain-level offset.**
  - The best temperature family (MOVEMENT,
    `{{p4_primary_summary | model=MOVEMENT, target=temperature, metric=mae | unweighted_subject_mean | .2f}}` °C) did
    not reach the training-mean predictor
    (`{{p4_primary_summary | model=training_mean, target=temperature, metric=mae | unweighted_subject_mean | .2f}}` °C).
  - User02 temperature bias ranged from
    `{{p4_primary_summary | model=RAW, target=temperature, metric=bias | User02 | +.2f}}` to
    `{{p4_primary_summary | model=RAW+MOVEMENT+CONTACT, target=temperature, metric=bias | User02 | +.2f}}` °C across
    the TCN families.
  - User02 humidity bias ranged from
    `{{p4_primary_summary | model=MOVEMENT, target=humidity, metric=bias | User02 | +.2f}}` to
    `{{p4_primary_summary | model=RAW+MOVEMENT+CONTACT, target=humidity, metric=bias | User02 | +.2f}}` %RH (Table S7).

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

{{TABLE:table4_personalization}}

{{FIGURE:figure2_temperature_personalization}}

**Figure 2.** Temperature MAE (°C) of full fine-tuning on the common primary test span versus the adaptation budget
b (b = 0 is the base model; budgets are plotted at their numeric value in nights), for each held-out subject and the
unweighted mean across three held-out subjects (descriptive). Markers: means over three model seeds; bars: seed
minimum–maximum.

{{FIGURE:figure3_humidity_personalization}}

**Figure 3.** Humidity MAE (%RH) on the common primary test span versus the adaptation budget b, as in Figure 2.

**Cohort curves** (unweighted means, descriptive):
- Temperature MAE:
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=0 | seed_mean | .2f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=1 | seed_mean | .2f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=3 | seed_mean | .2f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=7 | seed_mean | .2f}}` and
  `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=14 | seed_mean | .2f}}` °C for
  b = 0, 1, 3, 7 and 14.
- Humidity MAE:
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=0 | seed_mean | .2f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=1 | seed_mean | .2f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=3 | seed_mean | .2f}}`,
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=7 | seed_mean | .2f}}` and
  `{{p5_primary_mae | subject_id=unweighted_mean, target=humidity, budget_nights=14 | seed_mean | .2f}}` %RH. The
  humidity curve is not monotone and improves only at 14 nights.

**The cohort curves hide opposite subject-level effects.**
- **User02 (offset correction):** improved on both targets at every budget.
  - Temperature G reached
    `{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | G_pct | +.1f}}` % at b = 14.
  - The temperature bias moved from
    `{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_0 | +.2f}}` °C to
    `{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_b | +.2f}}` °C.
  - Humidity G at b = 14 was
    `{{p5_adaptation_gain | subject_id=User02, target=humidity, budget_nights=14 | G_pct | +.1f}}` %.
- **User07 temperature (negative transfer, i.e. adaptation-induced degradation relative to its own base model):** the
  seed-mean MAE was higher than that of the base model at every adaptation budget.
  - G was `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=1 | G_pct | +.1f}}` % at b = 1
    and `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=14 | G_pct | +.1f}}` % at b = 14.
  - Seed by seed, each adapted model was worse than its own base model at every budget: seeds improved, of three,
    were `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=1 | seeds_improved | d}}`,
    `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=3 | seeds_improved | d}}`,
    `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=7 | seeds_improved | d}}` and
    `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=14 | seeds_improved | d}}` at
    b = 1, 3, 7 and 14. The seed-specific G at b = 14 ranged from
    `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=14 | seed_G_min | +.1f}}` to
    `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=14 | seed_G_max | +.1f}}` %.
  - The night-level interval support for this loss depended on the seed (Section 4.4).
  - Its bias changed sign, from
    `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=14 | bias_0 | +.2f}}` to
    `{{p5_adaptation_gain | subject_id=User07, target=temperature, budget_nights=14 | bias_b | +.2f}}` °C.
  - User07 humidity, in contrast, improved (b = 14:
    `{{p5_adaptation_gain | subject_id=User07, target=humidity, budget_nights=14 | G_pct | +.1f}}` %).
- **User01 humidity (negative transfer, then recovery):** worse than the base model up to seven nights.
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

{{TABLE:table5_night_robustness}}

{{FIGURE:figure4_night_robustness}}

**Figure 4.** Night-level paired bootstrap change in MAE, ΔMAE = MAE(base) − MAE(adapted) (ΔMAE > 0: adaptation
better), for model seed 0, with 95 % night-cluster bootstrap percentile intervals, per held-out subject and budget b
(plotted at its numeric value in nights, with the subjects offset slightly for legibility): (a) temperature (°C);
(b) humidity (%RH). The intervals describe within-subject night-level uncertainty only.

- **User02 temperature at b = 14:**
  `{{p6_bootstrap_mae | subject_id=User02, target=temperature, budget_nights=14 | point_estimate | +.2f}}` °C
  [`{{p6_bootstrap_mae | subject_id=User02, target=temperature, budget_nights=14 | ci_lower | +.2f}}`,
  `{{p6_bootstrap_mae | subject_id=User02, target=temperature, budget_nights=14 | ci_upper | +.2f}}`].
  - Every User02 interval lay above zero, for both targets and all budgets.
  - For humidity at b = 14:
    `{{p6_bootstrap_mae | subject_id=User02, target=humidity, budget_nights=14 | point_estimate | +.2f}}` %RH
    [`{{p6_bootstrap_mae | subject_id=User02, target=humidity, budget_nights=14 | ci_lower | +.2f}}`,
    `{{p6_bootstrap_mae | subject_id=User02, target=humidity, budget_nights=14 | ci_upper | +.2f}}`].
- **User01 temperature:**
  - the changes at b = 1 and 3 were within night-level uncertainty; at b = 1:
    `{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=1 | point_estimate | +.2f}}` °C
    [`{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=1 | ci_lower | +.2f}}`,
    `{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=1 | ci_upper | +.2f}}`];
  - the gains at b = 7 and 14 had intervals above zero; at b = 14:
    `{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=14 | point_estimate | +.2f}}` °C
    [`{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=14 | ci_lower | +.2f}}`,
    `{{p6_bootstrap_mae | subject_id=User01, target=temperature, budget_nights=14 | ci_upper | +.2f}}`].
- **User01 humidity:**
  - intervals below zero at b = 1, 3 and 7; at b = 3:
    `{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=3 | point_estimate | +.2f}}` %RH
    [`{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=3 | ci_lower | +.2f}}`,
    `{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=3 | ci_upper | +.2f}}`];
  - above zero at b = 14:
    `{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=14 | point_estimate | +.2f}}` %RH
    [`{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=14 | ci_lower | +.2f}}`,
    `{{p6_bootstrap_mae | subject_id=User01, target=humidity, budget_nights=14 | ci_upper | +.2f}}`].
- **User07 temperature: the negative-transfer direction was dominant across seeds and start-span analyses, but it was
  not literally invariant for every seed–start combination.**
  - Seed 0: the intervals lay below zero at
    `{{COUNT:p6_bootstrap_mae | subject_id=User07, target=temperature, interval=below_zero}}` of four budgets.
  - Seed 1: at `{{COUNT:p6_bootstrap_seed_sensitivity | subject_id=User07, target=temperature, metric=mae, seed=1, interval=below_zero}}`
    of four.
  - Seed 2: at `{{COUNT:p6_bootstrap_seed_sensitivity | subject_id=User07, target=temperature, metric=mae, seed=2, interval=below_zero}}`
    of four.
  - The interval support for this negative transfer therefore depends on the model seed.
- **Start of the test span (post hoc):** moving the start among nights 12, 14, 16, 18 and 21 changed the magnitude of
  the gains, but at the aggregated subject–target–budget level the principal directional findings were stable across
  these start points (Table S17; Figure S2). Seed-level exceptions occurred in borderline cases.
  - For User07 temperature at start night 12 and b = 1,
    `{{p6_drift_sensitivity | start_night=12, subject_id=User07, target=temperature, budget_nights=1 | seeds_improved | d}}`
    of `{{p6_drift_sensitivity | start_night=12, subject_id=User07, target=temperature, budget_nights=1 | n_seeds | d}}`
    seeds showed a positive gain.
  - The seed-mean gain was negative there
    (`{{p6_drift_sensitivity | start_night=12, subject_id=User07, target=temperature, budget_nights=1 | G_pct | +.1f}}` %).
  - The User07 temperature loss grew as the test span moved later.

### 4.5. Temporal Level Mismatch (Post Hoc, Descriptive)

Using the targets only (no model), we compared the mean target level of each adaptation span with that of the
primary span (Table S15; Figure S3). Values below are span mean minus primary-span mean.

- **User07 temperature:**
  - the earliest night: `{{p6_level_mismatch_spans | subject_id=User07, target=temperature, span=adaptation_b1 | minus_primary_mean | +.2f}}` °C;
  - the 14-night adaptation span:
    `{{p6_level_mismatch_spans | subject_id=User07, target=temperature, span=adaptation_b14 | minus_primary_mean | +.2f}}` °C;
  - the base model's training pool:
    `{{p6_level_mismatch_spans | subject_id=User07, target=temperature, span=training_pool | minus_primary_mean | +.2f}}` °C.
  The early nights were cooler than the later period, whereas the training pool was close to it.
- **User01 humidity:** the adaptation spans lay far above the later level:
  - `{{p6_level_mismatch_spans | subject_id=User01, target=humidity, span=adaptation_b3 | minus_primary_mean | +.2f}}` %RH
    for b = 3;
  - `{{p6_level_mismatch_spans | subject_id=User01, target=humidity, span=adaptation_b14 | minus_primary_mean | +.2f}}` %RH
    for b = 14.
- **User02 temperature:** the adaptation spans were much closer to the later level than the training pool:
  - b = 14: `{{p6_level_mismatch_spans | subject_id=User02, target=temperature, span=adaptation_b14 | minus_primary_mean | +.2f}}` °C;
  - training pool: `{{p6_level_mismatch_spans | subject_id=User02, target=temperature, span=training_pool | minus_primary_mean | +.2f}}` °C.
- **Retrospective descriptive rule:** adaptation is expected to help when the adaptation-span level lies closer to the
  later level than the base model's bias.
  - It agreed with the observed direction in
    `{{COUNT:p6_level_mismatch_consistency | consistent=True}}` of 24 subject–target–budget cells.
  - The exception was User01 temperature at b = 3, where the gain came from a lower error spread.
  - The rule was formulated after the personalization results were known. The agreement is an association within
    three subjects, not a test of a mechanism.
  - The rule needs the target level of the later nights, which is unknown when a model is adapted. It describes the
    results after the fact and is not a safeguard that a deployment could apply.

### 4.6. Device-Level Residual (User02)

- **Mat 22482 temperature:** a negative residual persisted after adaptation.
  - Bias at b = 14 (seed mean):
    `{{p5_user02_device_strata | subject_id=User02, budget_nights=14, seed=mean, stratum_type=device, stratum=22482, target=temperature, metric=bias | value | +.2f}}` °C.
  - Seed-0 night-level interval:
    `{{p6_user02_device_context_bootstrap | stratum=22482, target=temperature, quantity=bias_b14 | point_estimate | +.2f}}` °C
    [`{{p6_user02_device_context_bootstrap | stratum=22482, target=temperature, quantity=bias_b14 | ci_lower | +.2f}}`,
    `{{p6_user02_device_context_bootstrap | stratum=22482, target=temperature, quantity=bias_b14 | ci_upper | +.2f}}`].
- **Mat 22480:** bias at b = 14 of
  `{{p6_user02_device_context_bootstrap | stratum=22480, target=temperature, quantity=bias_b14 | point_estimate | +.2f}}` °C
  [`{{p6_user02_device_context_bootstrap | stratum=22480, target=temperature, quantity=bias_b14 | ci_lower | +.2f}}`,
  `{{p6_user02_device_context_bootstrap | stratum=22480, target=temperature, quantity=bias_b14 | ci_upper | +.2f}}`];
  the interval includes zero.
- **Strata:** the 22482 under-estimation persisted in every quality-phase and heater-context stratum with at least ten
  nights (Table S18; Figure S4). Its size differed between heater contexts. For example, the seed-0 bias at b = 14 was
  `{{p6_user02_device_context_bootstrap | stratum=22482/after_AHOF_60min, target=temperature, quantity=bias_b14 | point_estimate | +.2f}}` °C
  within 60 min after a heater-off code and
  `{{p6_user02_device_context_bootstrap | stratum=22482/no_AHON_AHOF_60min, target=temperature, quantity=bias_b14 | point_estimate | +.2f}}` °C
  without a heater code in the preceding 60 min.
- **Per-mat offset (post-hoc diagnostic, added after the primary results were known; Table S22):** an offset
  estimated separately for each mat, instead of one offset for both, lowered the 22482 temperature MAE of the
  adaptation-target mean at b = 14 from
  `{{p8_calibration_user02_per_mat | eval_mat=22482, target=temperature, budget_nights=14, predictor=B, calibration=pooled | mae | .2f}}`
  to
  `{{p8_calibration_user02_per_mat | eval_mat=22482, target=temperature, budget_nights=14, predictor=B, calibration=per_mat | mae | .2f}}` °C.
  It did not help uniformly: for humidity it lowered the 22480 error and raised the 22482 error at every budget.
  The two mats carry different level offsets, which one pooled offset or one adapted model cannot both remove.
- **Interpretation:** the mats differ in microclimate and control history, and their physical placement is unknown;
  these factors cannot be separated here. The residual is therefore reported as a device-level observation, not as
  evidence of a sensor defect or a heater effect. Heater context across the three subjects is described in
  Section 4.11.

### 4.7. Post-Hoc Comparators: Level Correction versus Tracking

Table 4 (predictors A, B and D), Table 6, Table 7 and Figure 5 report the post-hoc comparators of Section 3.5.5. They
were added after the primary results were known.

**Table 6.** Residual variation (post hoc): target standard deviation and R = error standard deviation / target
standard deviation for the RAW-TCN under strict leave-one-subject-out evaluation (all labelled windows, the Table 2
setting) and, on the primary test span (nights ≥ 16), for the base model (b = 0), full fine-tuning at b = 14 and the
scratch initialization control at b = 14. A constant predictor has R = 1. Neural models: seed mean, in brackets the
seed range. Target SD in °C for temperature and %RH for humidity.

{{TABLE:table6_residual_variation}}

**Table 7.** Post-hoc comparators at b = 14 on the primary test span: MAE of the adaptation-target mean (B), full
fine-tuning (E) and the scratch initialization control (S), and the night-level paired bootstrap differences
ΔMAE = MAE(first) − MAE(second) for B − E, D − E, S − E and B − S (Δ > 0: the second predictor has the lower
error). MAE of B: a single deterministic value; MAE of E and S: mean ± standard deviation over model seeds 0, 1 and 2.
The Δ point estimates and 95 % intervals refer to model seed 0 only (2,000 resamples); then the side of zero for seeds
0 / 1 / 2.
Units: °C for temperature and %RH for humidity. The intervals describe within-subject night-level uncertainty only.

{{TABLE:table7_posthoc_comparators}}

{{FIGURE:figure5_posthoc_comparators}}

**Figure 5.** Post-hoc comparators versus the adaptation budget b (plotted at its numeric value in nights), per
held-out subject: (a–c) temperature MAE (°C); (d–f) humidity MAE (%RH). E: full fine-tuning, starting at the base
model C at b = 0; D: the base model plus the adaptation-window offset, also starting at C; B: the mean target of the
adaptation windows, starting at the training mean A at b = 0; S: the scratch initialization control at b = 14, drawn
slightly to the right of b = 14 for legibility. Markers: seed means; bars: seed minimum–maximum.

- **A personalized constant often came close to or below full fine-tuning.**
  - The MAE of the adaptation-target mean (B) was no higher than the seed-mean MAE of full fine-tuning (E) in
    `{{COUNT:p8_interpretation_cases | case_A_B_le_E=True}}` of 24 subject–target–budget cells
    (`{{COUNT:p8_interpretation_cases | case_A_B_le_E=True, budget_nights=14}}` of six at b = 14). This compares
    point estimates; it is not a test of equivalence or non-inferiority.
  - With the adaptation-night median instead of the mean (exploratory, Section 3.5.8), the count was `{{p10_point_counts | setting=rq2_primary_span, comparison=B_med MAE <= E (fine-tuning) seed-mean MAE | count | d}}` of 24.
    Many of these cells are close, so the count depends on the choice of constant.
  - By the rule of Section 3.5.5, B was better than E in
    `{{COUNT:p8_interpretation_cases | B_better_than_E=True}}` cells and E better than B in
    `{{COUNT:p8_interpretation_cases | E_better_than_B=True}}`.
  - **User02 temperature,** the largest correction of Section 4.3: B had the lower seed-mean MAE at every budget. At
    b = 14 it was
    `{{p8_calibration_main | subject_id=User02, target=temperature, budget_nights=14, predictor=B | mae | .2f}}` versus
    `{{p8_calibration_main | subject_id=User02, target=temperature, budget_nights=14, predictor=E | mae | .2f}}` °C
    (ΔMAE B − E
    `{{p8_comparator_bootstrap | subject_id=User02, target=temperature, budget_nights=14, first=B, second=E, seed=0 | point_estimate | +.2f}}` °C
    [`{{p8_comparator_bootstrap | subject_id=User02, target=temperature, budget_nights=14, first=B, second=E, seed=0 | ci_lower | +.2f}}`,
    `{{p8_comparator_bootstrap | subject_id=User02, target=temperature, budget_nights=14, first=B, second=E, seed=0 | ci_upper | +.2f}}`]).
  - **User01 temperature:** B was better than E up to b = 7, and E was better at b = 14.
  - **Humidity:** E was better than B for User01 at every budget and for User02 from b = 3; for User07, B and E did
    not differ.
  - **Where E was better than B,** its bias on the later span was closer to zero, not its error spread. For User01
    humidity at b = 14 the bias was
    `{{p8_calibration_main | subject_id=User01, target=humidity, budget_nights=14, predictor=E | bias | +.2f}}` %RH for
    E and
    `{{p8_calibration_main | subject_id=User01, target=humidity, budget_nights=14, predictor=B | bias | +.2f}}` %RH for
    B (Table S20).
- **Shifting the base model was not enough, for a revealing reason.**
  - E was better than the offset-calibrated base model D in
    `{{COUNT:p8_interpretation_cases | case_C_E_better_than_D=True}}` of 24 cells. D and E did not differ in
    `{{COUNT:p8_interpretation_cases | case_B_D_approx_E=True}}`, and D was better in
    `{{COUNT:p8_interpretation_cases | D_better_than_E=True}}`.
  - D keeps the base model's residual variation, which exceeded the target variation in every cell. R of the base
    model on the primary span ranged from
    `{{p8_residual_variation | setting=rq2_primary_span, subject_id=User02, target=temperature, budget_nights=0, predictor=C | R | .2f}}`
    to
    `{{p8_residual_variation | setting=rq2_primary_span, subject_id=User01, target=temperature, budget_nights=0, predictor=C | R | .2f}}`
    (Table 6).
  - Full fine-tuning removed most of this excess variation rather than adding tracking.
- **No demonstrable within-subject tracking.** No pressure-based model reduced the error standard deviation clearly
  below the target standard deviation.
  - After 14 nights, R ranged from
    `{{p8_residual_variation | setting=rq2_primary_span, subject_id=User02, target=temperature, budget_nights=14, predictor=E | R | .2f}}`
    to
    `{{p8_residual_variation | setting=rq2_primary_span, subject_id=User01, target=humidity, budget_nights=14, predictor=E | R | .2f}}`
    for full fine-tuning and from
    `{{p8_residual_variation | setting=rq2_primary_span, subject_id=User02, target=temperature, budget_nights=14, predictor=S | R | .2f}}`
    to
    `{{p8_residual_variation | setting=rq2_primary_span, subject_id=User01, target=humidity, budget_nights=14, predictor=S | R | .2f}}`
    for the scratch control.
  - Where the adapted networks had a lower error than the constant, the difference came from their level on the
    later span, not from following the variation within it.
- **Pretraining added no consistent value (b = 14; Table 7).**
  - The scratch control (S) was not worse than full fine-tuning in
    `{{COUNT:p8_interpretation_cases | case_I_S_approx_or_better_than_E=True}}` of six cells.
  - E was better only for User01 temperature: ΔMAE S − E
    `{{p8_comparator_bootstrap | subject_id=User01, target=temperature, budget_nights=14, first=S, second=E, seed=0 | point_estimate | +.2f}}` °C
    [`{{p8_comparator_bootstrap | subject_id=User01, target=temperature, budget_nights=14, first=S, second=E, seed=0 | ci_lower | +.2f}}`,
    `{{p8_comparator_bootstrap | subject_id=User01, target=temperature, budget_nights=14, first=S, second=E, seed=0 | ci_upper | +.2f}}`];
    for model seed 1 the interval lay below zero instead.
  - S was better than E for User02 humidity.
  - S was better than the adaptation-target mean in
    `{{COUNT:p8_interpretation_cases | case_F_S_better_than_B=True}}` of six cells, the same cells in which E was.
  - Cross-subject pretraining therefore did not provide consistent additional predictive value over target-only
    training under the tested fixed adaptation protocol.
- **User07 temperature: negative transfer without fine-tuning dynamics.**
  - D and E both had a higher seed-mean MAE than the base model C at
    `{{COUNT:p8_interpretation_cases | case_D=True}}` of four budgets.
  - The constant B was worse than the training mean A at every budget.
  - An offset estimated from the early nights therefore degraded the later span on its own. D was less harmful than
    E from b = 3 (ΔMAE D − E at b = 14:
    `{{p8_comparator_bootstrap | subject_id=User07, target=temperature, budget_nights=14, first=D, second=E, seed=0 | point_estimate | +.2f}}` °C
    [`{{p8_comparator_bootstrap | subject_id=User07, target=temperature, budget_nights=14, first=D, second=E, seed=0 | ci_lower | +.2f}}`,
    `{{p8_comparator_bootstrap | subject_id=User07, target=temperature, budget_nights=14, first=D, second=E, seed=0 | ci_upper | +.2f}}`]).

### 4.8. Dynamic-Signal Diagnostic (Second-Order Post Hoc)

Table 8 reports the diagnostic of Section 3.5.6 for the base model, and for full fine-tuning and the scratch control at
b = 14. All budgets and seeds are in Tables S27–S31.

**Table 8.** Dynamic-signal diagnostic (second-order post hoc) on the primary test span: R = error SD / target SD,
Q = prediction SD / target SD, the pooled correlation, the within-night correlation (night-centred values) and the
night × mat-centred variant, and the retrospective oracle ratio R_oracle = √(1 − r²). Values: means over three model
seeds, which are the basis of the case classification; intervals: model seed 0, 95 % night-cluster bootstrap with
2,000 resamples. R_oracle refers to an affine map fitted on the test labels and is therefore a retrospective
diagnostic only.

{{TABLE:table8_dynamic_signal}}

- **No consistent within-night co-variation.** Under the pre-registered rule, the within-night correlation was
  positive in:
  - `{{COUNT:p8_dynamic_cases | condition=C, within_positive_rule=True}}` of six subject–target cells for the base model;
  - `{{COUNT:p8_dynamic_cases | condition=E, within_positive_rule=True}}` of 24 cells for full fine-tuning (all budgets);
  - `{{COUNT:p8_dynamic_cases | condition=S, within_positive_rule=True}}` of six for the scratch control. This was User02
    temperature, with a night × mat-centred correlation of `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=S, budget_nights=14 | r_within_mat | +.2f}}`.
- **Base model: variation without co-variation.**
  - The base model's predictions varied: for User01 temperature they varied more than the target
    (Q = `{{p8_dynamic_summary | subject_id=User01, target=temperature, condition=C, budget_nights=0 | Q | .2f}}`).
  - Their within-night correlations were near zero for User01 and User07.
  - For User02, the pooled and night-centred correlations were negative, for example
    `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=C, budget_nights=0 | r_pooled | +.2f}}` (pooled) for temperature. Centring within night and
    mat left `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=C, budget_nights=0 | r_within_mat | +.2f}}`: most of the association came from the two
    mats' level difference.
- **After adaptation: compressed prediction dynamics.** At b = 14 the prediction standard deviation of full
  fine-tuning was `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=E, budget_nights=14 | Q | .2f}}` times the target standard deviation for User02 temperature and `{{p8_dynamic_summary | subject_id=User07, target=temperature, condition=E, budget_nights=14 | Q | .2f}}`
  times for User07 temperature (Q in Table 8). Prediction dynamics were strongly compressed toward level-dominated
  behaviour.
- **After adaptation, User02: mostly the two mats' level difference.** User02 is the only subject recorded on two
  mats at once, so its within-mat values are the relevant ones. At b = 14:
  - full fine-tuning: the night-centred correlation was
    `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=E, budget_nights=14 | r_within | +.2f}}` for temperature and
    `{{p8_dynamic_summary | subject_id=User02, target=humidity, condition=E, budget_nights=14 | r_within | +.2f}}` for humidity, but only
    `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=E, budget_nights=14 | r_within_mat | +.2f}}` and
    `{{p8_dynamic_summary | subject_id=User02, target=humidity, condition=E, budget_nights=14 | r_within_mat | +.2f}}` when centred within night and mat;
  - scratch control: `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=S, budget_nights=14 | r_within | +.2f}}` →
    `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=S, budget_nights=14 | r_within_mat | +.2f}}` (temperature) and
    `{{p8_dynamic_summary | subject_id=User02, target=humidity, condition=S, budget_nights=14 | r_within | +.2f}}` →
    `{{p8_dynamic_summary | subject_id=User02, target=humidity, condition=S, budget_nights=14 | r_within_mat | +.2f}}` (humidity).
  Most of the night-centred association therefore came from the level difference between the two mats within a night.
  Within a mat, the evidence of linear co-variation is weak: a small positive correlation for temperature, near zero
  for humidity. It does not show that pressure carries no information.
- **After adaptation, User01 and User07.** For User01 temperature, the pooled correlation of full fine-tuning was
  `{{p8_dynamic_summary | subject_id=User01, target=temperature, condition=E, budget_nights=14 | r_pooled | +.2f}}` and its within-night correlation
  `{{p8_dynamic_summary | subject_id=User01, target=temperature, condition=E, budget_nights=14 | r_within | +.2f}}`, a between-night level alignment. For User07
  temperature and User01 humidity, the pooled correlations were negative.
- **Little linear headroom.**
  - R_oracle was at least `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=S, budget_nights=14 | oracle_affine | .2f}}` in every neural cell (Table S30). Even an affine map fitted on the
    test labels could not have brought the residual standard deviation far below the target standard deviation.
  - The pre-specified trigger for an adaptation-only affine calibration fired for
    `{{COUNT:p8_dynamic_trigger | fires=True}}` of two targets, so that comparator was not run.
- **Cases (Table S31):**
  - the cells fell under the pre-registered cases of variation without linear co-variation, between-night association
    only, misaligned association and little calibration headroom;
  - the case of within-night co-variation held in `{{COUNT:p8_dynamic_cases | J3=True}}` cell;
  - linearly recoverable structure (R_oracle at most 0.90) held in `{{COUNT:p8_dynamic_cases | J8_cell=True}}`.

### 4.9. Additional External Validation on a Further Subject (Post Hoc)

Table 9 reports the additional external validation of Section 3.5.7. It is not pooled with the primary results.

**Table 9.** Additional external validation (post hoc) on one further subject that is not part of the primary cohort:
training-mean predictor and the three frozen RAW-TCN configurations, all trained on the three primary subjects
(RAW-TCN: seed means, in brackets the seed range of MAE); MAE, RMSE and bias in °C or %RH, R, Q, pooled and
within-night correlations. No night-bootstrap interval is computed (fewer than 10 nights).

{{TABLE:table9_external_validation}}

- **Data:** `{{p9_user03_qa_totals | protocol_version=v1.3 | reconstructed_rows | ,d}}` of the `{{p9_user03_qa_totals | protocol_version=v1.3 | csv_data_rows | ,d}}` rows of the valid export
  passed the reconciliation. `{{p9_user03_qa_totals | protocol_version=v1.3 | excluded_minutes | d}}` minutes were excluded, most of them covered only
  by the complementary export. The rows gave `{{p9_user03_qa_totals | protocol_version=v1.3 | labelled_windows | ,d}}` labelled windows on
  `{{p9_user03_qa_totals | protocol_version=v1.3 | nights_with_labelled_windows | d}}` nights.
- **The training mean was better for both targets, under the pre-registered rule.**
  - Temperature: `{{p9_user03_summary | model=training_mean, config_fold=, target=temperature | mae | .2f}}` °C for the training mean, against
    `{{p9_user03_summary | model=raw_tcn, config_fold=2, target=temperature | mae | .2f}}` to `{{p9_user03_summary | model=raw_tcn, config_fold=1, target=temperature | mae | .2f}}` °C for the
    three configurations. The training mean was lower on at least `{{p9_user03_interpretation | target=temperature | cfg2_nights_tm_lower_mae | d}}`
    of seven nights for every configuration.
  - Humidity: `{{p9_user03_summary | model=training_mean, config_fold=, target=humidity | mae | .2f}}` against
    `{{p9_user03_summary | model=raw_tcn, config_fold=2, target=humidity | mae | .2f}}` to `{{p9_user03_summary | model=raw_tcn, config_fold=3, target=humidity | mae | .2f}}` %RH. The
    training mean was lower on every night.
  - Both predictors under-estimated the new subject's level, the network more strongly for humidity.
- **No demonstrable within-night co-variation.**
  - The network's humidity predictions varied about twice as much as the target
    (Q = `{{p9_user03_summary | model=raw_tcn, config_fold=1, target=humidity | Q | .2f}}` to `{{p9_user03_summary | model=raw_tcn, config_fold=2, target=humidity | Q | .2f}}`).
  - Its within-night correlations were small: `{{p9_user03_summary | model=raw_tcn, config_fold=3, target=humidity | r_within | +.2f}}` to
    `{{p9_user03_summary | model=raw_tcn, config_fold=2, target=humidity | r_within | +.2f}}` for humidity, below the pre-registered floor, and near
    zero for temperature.
  - Under the rule, within-night co-variation was absent for both targets.
- **Relation to the primary findings:** the pre-registered comparison classifies the external result as strengthening
  both primary conclusions: the advantage of a simple level baseline, and the absence of within-night co-variation.
  It concerns one additional subject; it is not a replication and gives no population inference.

### 4.10. Exploratory Analysis: Median Constants, Pressure-Summary Histories and a Matched Training Pool (Post Hoc)

The held-out subjects differ strongly in their target levels, and User02's two mats differ from each other (Figure 6).
The comparisons below are made against this domain-level structure.

{{FIGURE:figure6_target_distributions}}

**Figure 6.** Distributions of the labelled 40-s window targets of each held-out subject under strict
leave-one-subject-out evaluation (all nights; User02 by mat): (a) temperature (°C), (b) humidity (%RH). Boxes:
interquartile range with the median; whiskers: 5th to 95th percentiles. Dashed lines: the source-training mean of the
fold in which the subject is held out, i.e. the training-mean predictor of Table 2. Descriptive; nights are not dated.

**Table 10.** Exploratory analysis (Section 3.5.8), strict leave-one-subject-out evaluation on the endpoints with 40-s,
300-s and 900-s histories available. MAE in °C (temperature) or %RH (humidity) of the source-training mean and median
of the common training endpoints, of the 40-s RAW-TCN retrained on the common endpoints (mean over model seeds 0, 1
and 2, in brackets the seed range) and of histogram gradient boosting on 40-s, 300-s and 900-s pressure summaries.
Every learned model was trained, selected and evaluated on the same common endpoints. †: the night-level paired
bootstrap interval of MAE(source mean) − MAE(model) lies above zero (model seed 0 for the RAW-TCN). Ridge regression,
bias, R, correlations and all intervals: Table S38; the retrained network per seed and its intervals: Tables S39–S40.

| Subject | Target | Common endpoints (windows / nights) | Source mean | Source median | RAW-TCN 40 s, common pool | Boosting 40 s | Boosting 300 s | Boosting 900 s |
|---|---|---|---|---|---|---|---|---|
| User01 | temperature | {{p13_table10_common_endpoints | subject_id=User01, target=temperature | n_windows | ,d}} / {{p13_table10_common_endpoints | subject_id=User01, target=temperature | n_nights | d}} | {{p13_table10_common_endpoints | subject_id=User01, target=temperature | mae_source_mean | .2f}} | {{p13_table10_common_endpoints | subject_id=User01, target=temperature | mae_source_median | .2f}} | {{p13_table10_common_endpoints | subject_id=User01, target=temperature | mae_tcn_common | .2f}} ({{p13_table10_common_endpoints | subject_id=User01, target=temperature | mae_tcn_common_seed_min | .2f}}–{{p13_table10_common_endpoints | subject_id=User01, target=temperature | mae_tcn_common_seed_max | .2f}}){{p13_table10_common_endpoints | subject_id=User01, target=temperature | mark_tcn_common | s}} | {{p13_table10_common_endpoints | subject_id=User01, target=temperature | mae_hgb_40 | .2f}}{{p13_table10_common_endpoints | subject_id=User01, target=temperature | mark_hgb_40 | s}} | {{p13_table10_common_endpoints | subject_id=User01, target=temperature | mae_hgb_300 | .2f}}{{p13_table10_common_endpoints | subject_id=User01, target=temperature | mark_hgb_300 | s}} | {{p13_table10_common_endpoints | subject_id=User01, target=temperature | mae_hgb_900 | .2f}}{{p13_table10_common_endpoints | subject_id=User01, target=temperature | mark_hgb_900 | s}} |
| User02 | temperature | {{p13_table10_common_endpoints | subject_id=User02, target=temperature | n_windows | ,d}} / {{p13_table10_common_endpoints | subject_id=User02, target=temperature | n_nights | d}} | {{p13_table10_common_endpoints | subject_id=User02, target=temperature | mae_source_mean | .2f}} | {{p13_table10_common_endpoints | subject_id=User02, target=temperature | mae_source_median | .2f}} | {{p13_table10_common_endpoints | subject_id=User02, target=temperature | mae_tcn_common | .2f}} ({{p13_table10_common_endpoints | subject_id=User02, target=temperature | mae_tcn_common_seed_min | .2f}}–{{p13_table10_common_endpoints | subject_id=User02, target=temperature | mae_tcn_common_seed_max | .2f}}){{p13_table10_common_endpoints | subject_id=User02, target=temperature | mark_tcn_common | s}} | {{p13_table10_common_endpoints | subject_id=User02, target=temperature | mae_hgb_40 | .2f}}{{p13_table10_common_endpoints | subject_id=User02, target=temperature | mark_hgb_40 | s}} | {{p13_table10_common_endpoints | subject_id=User02, target=temperature | mae_hgb_300 | .2f}}{{p13_table10_common_endpoints | subject_id=User02, target=temperature | mark_hgb_300 | s}} | {{p13_table10_common_endpoints | subject_id=User02, target=temperature | mae_hgb_900 | .2f}}{{p13_table10_common_endpoints | subject_id=User02, target=temperature | mark_hgb_900 | s}} |
| User07 | temperature | {{p13_table10_common_endpoints | subject_id=User07, target=temperature | n_windows | ,d}} / {{p13_table10_common_endpoints | subject_id=User07, target=temperature | n_nights | d}} | {{p13_table10_common_endpoints | subject_id=User07, target=temperature | mae_source_mean | .2f}} | {{p13_table10_common_endpoints | subject_id=User07, target=temperature | mae_source_median | .2f}} | {{p13_table10_common_endpoints | subject_id=User07, target=temperature | mae_tcn_common | .2f}} ({{p13_table10_common_endpoints | subject_id=User07, target=temperature | mae_tcn_common_seed_min | .2f}}–{{p13_table10_common_endpoints | subject_id=User07, target=temperature | mae_tcn_common_seed_max | .2f}}){{p13_table10_common_endpoints | subject_id=User07, target=temperature | mark_tcn_common | s}} | {{p13_table10_common_endpoints | subject_id=User07, target=temperature | mae_hgb_40 | .2f}}{{p13_table10_common_endpoints | subject_id=User07, target=temperature | mark_hgb_40 | s}} | {{p13_table10_common_endpoints | subject_id=User07, target=temperature | mae_hgb_300 | .2f}}{{p13_table10_common_endpoints | subject_id=User07, target=temperature | mark_hgb_300 | s}} | {{p13_table10_common_endpoints | subject_id=User07, target=temperature | mae_hgb_900 | .2f}}{{p13_table10_common_endpoints | subject_id=User07, target=temperature | mark_hgb_900 | s}} |
| User01 | humidity | {{p13_table10_common_endpoints | subject_id=User01, target=humidity | n_windows | ,d}} / {{p13_table10_common_endpoints | subject_id=User01, target=humidity | n_nights | d}} | {{p13_table10_common_endpoints | subject_id=User01, target=humidity | mae_source_mean | .2f}} | {{p13_table10_common_endpoints | subject_id=User01, target=humidity | mae_source_median | .2f}} | {{p13_table10_common_endpoints | subject_id=User01, target=humidity | mae_tcn_common | .2f}} ({{p13_table10_common_endpoints | subject_id=User01, target=humidity | mae_tcn_common_seed_min | .2f}}–{{p13_table10_common_endpoints | subject_id=User01, target=humidity | mae_tcn_common_seed_max | .2f}}){{p13_table10_common_endpoints | subject_id=User01, target=humidity | mark_tcn_common | s}} | {{p13_table10_common_endpoints | subject_id=User01, target=humidity | mae_hgb_40 | .2f}}{{p13_table10_common_endpoints | subject_id=User01, target=humidity | mark_hgb_40 | s}} | {{p13_table10_common_endpoints | subject_id=User01, target=humidity | mae_hgb_300 | .2f}}{{p13_table10_common_endpoints | subject_id=User01, target=humidity | mark_hgb_300 | s}} | {{p13_table10_common_endpoints | subject_id=User01, target=humidity | mae_hgb_900 | .2f}}{{p13_table10_common_endpoints | subject_id=User01, target=humidity | mark_hgb_900 | s}} |
| User02 | humidity | {{p13_table10_common_endpoints | subject_id=User02, target=humidity | n_windows | ,d}} / {{p13_table10_common_endpoints | subject_id=User02, target=humidity | n_nights | d}} | {{p13_table10_common_endpoints | subject_id=User02, target=humidity | mae_source_mean | .2f}} | {{p13_table10_common_endpoints | subject_id=User02, target=humidity | mae_source_median | .2f}} | {{p13_table10_common_endpoints | subject_id=User02, target=humidity | mae_tcn_common | .2f}} ({{p13_table10_common_endpoints | subject_id=User02, target=humidity | mae_tcn_common_seed_min | .2f}}–{{p13_table10_common_endpoints | subject_id=User02, target=humidity | mae_tcn_common_seed_max | .2f}}){{p13_table10_common_endpoints | subject_id=User02, target=humidity | mark_tcn_common | s}} | {{p13_table10_common_endpoints | subject_id=User02, target=humidity | mae_hgb_40 | .2f}}{{p13_table10_common_endpoints | subject_id=User02, target=humidity | mark_hgb_40 | s}} | {{p13_table10_common_endpoints | subject_id=User02, target=humidity | mae_hgb_300 | .2f}}{{p13_table10_common_endpoints | subject_id=User02, target=humidity | mark_hgb_300 | s}} | {{p13_table10_common_endpoints | subject_id=User02, target=humidity | mae_hgb_900 | .2f}}{{p13_table10_common_endpoints | subject_id=User02, target=humidity | mark_hgb_900 | s}} |
| User07 | humidity | {{p13_table10_common_endpoints | subject_id=User07, target=humidity | n_windows | ,d}} / {{p13_table10_common_endpoints | subject_id=User07, target=humidity | n_nights | d}} | {{p13_table10_common_endpoints | subject_id=User07, target=humidity | mae_source_mean | .2f}} | {{p13_table10_common_endpoints | subject_id=User07, target=humidity | mae_source_median | .2f}} | {{p13_table10_common_endpoints | subject_id=User07, target=humidity | mae_tcn_common | .2f}} ({{p13_table10_common_endpoints | subject_id=User07, target=humidity | mae_tcn_common_seed_min | .2f}}–{{p13_table10_common_endpoints | subject_id=User07, target=humidity | mae_tcn_common_seed_max | .2f}}){{p13_table10_common_endpoints | subject_id=User07, target=humidity | mark_tcn_common | s}} | {{p13_table10_common_endpoints | subject_id=User07, target=humidity | mae_hgb_40 | .2f}}{{p13_table10_common_endpoints | subject_id=User07, target=humidity | mark_hgb_40 | s}} | {{p13_table10_common_endpoints | subject_id=User07, target=humidity | mae_hgb_300 | .2f}}{{p13_table10_common_endpoints | subject_id=User07, target=humidity | mark_hgb_300 | s}} | {{p13_table10_common_endpoints | subject_id=User07, target=humidity | mae_hgb_900 | .2f}}{{p13_table10_common_endpoints | subject_id=User07, target=humidity | mark_hgb_900 | s}} |

Training-pool sensitivity (Table S38): the RAW-TCN trained on all labelled 40-s windows, evaluated on the same
endpoints, had a temperature MAE of {{p13_table10_common_endpoints | subject_id=User01, target=temperature | mae_tcn_full | .2f}}, {{p13_table10_common_endpoints | subject_id=User02, target=temperature | mae_tcn_full | .2f}} and
{{p13_table10_common_endpoints | subject_id=User07, target=temperature | mae_tcn_full | .2f}} °C and a humidity MAE of {{p13_table10_common_endpoints | subject_id=User01, target=humidity | mae_tcn_full | .2f}}, {{p13_table10_common_endpoints | subject_id=User02, target=humidity | mae_tcn_full | .2f}} and
{{p13_table10_common_endpoints | subject_id=User07, target=humidity | mae_tcn_full | .2f}} %RH (User01, User02, User07).

- **Endpoints:** a 900-s history needs 15 min without a recording gap longer than 5 s, so about half of the labelled
  endpoints qualified (Table S37); the comparisons below are on that subset.
- **Temperature, summary models:** gradient boosting with 300-s or 900-s histories had a lower MAE than the
  source-training mean in {{COUNT:p10_history_interpretation | family=hgb, history_s=900, target=temperature, H_a_beats_training_mean_common=True}} of 3 subjects (User01 and User07; night-level intervals above zero) and not for
  User02, where every pressure model was worse than the constant; ridge regression did so in none (Table S38). The
  gains came with a smaller offset, R stayed above 1, and the night-centred correlations were near zero or negative.
  For User07 the source-training median had a lower MAE than the boosted models.
- **Temperature, retrained RAW-TCN:** its MAE was {{p13_table10_common_endpoints | subject_id=User01, target=temperature | mae_tcn_common | .2f}},
  {{p13_table10_common_endpoints | subject_id=User02, target=temperature | mae_tcn_common | .2f}} and {{p13_table10_common_endpoints | subject_id=User07, target=temperature | mae_tcn_common | .2f}} °C (User01,
  User02, User07). Under the pre-specified reading it exceeded both constants for {{COUNT:p11_common_pool_interpretation | target=temperature, exceeds_level_baselines=True}} of 3 subjects. For
  User01 its point estimate was below both constants for each of the three seeds, but the model-seed-0 interval against the source
  mean included zero (for seeds 1 and 2 it lay above zero); for User02 and User07 its MAE was higher than that of the
  source mean. Restricting the training pool moved the individual estimates, but it produced no evidence that the 40-s
  network consistently outperforms a simple level baseline.
- **Humidity:** both summary-model families and the retrained RAW-TCN had a lower MAE than the source-training mean
  for User01 and User02 and a higher one for User07, the same pattern as the 40-s RAW-TCN in Table 2.
- **History length:** for temperature, the 300-s and 900-s histories had a lower error than the 40-s history in all three
  subjects for gradient boosting, mostly through a smaller offset. This is an association on the common endpoints, not
  evidence of a thermal lag.
- **Variation beyond level:** no model met the pre-specified rule (R < 1 with a night-centred correlation of at least
  0.10) for any subject and target; the retrained RAW-TCN had a seed-mean R above 1 in every cell (Table S39).
- **Matched training pool:** with the pool matched, the temperature MAE of the 40-s RAW-TCN and that of the 40-s
  boosted model differed by
  {{p13_summary_values | key=tcn_common_vs_hgb_40_temperature_absdiff_min | value | .2f}} to {{p13_summary_values | key=tcn_common_vs_hgb_40_temperature_absdiff_max | value | .2f}} °C,
  and the sign of the difference depended on the subject (for User01 also on the seed). The lower error of the 300-s
  and 900-s summary models for User01 and User07 is therefore not explained by the original network's larger training
  pool. The difference is not read as a superiority of one architecture, as an effect of history length alone, or as
  overfitting.

### 4.11. Heater-Context Diagnostic (Post Hoc, Descriptive)

Table 11 summarises the diagnostic of Section 3.5.9 for temperature; humidity, both spans and all intervals are in
Tables S41–S44.

**Table 11.** Heater-context diagnostic (post hoc, descriptive), temperature. Labelled windows within 60 min after a
heater-on code, with their share of all labelled windows of the held-out subject; η², the share of the observed
temperature variance associated with the three heater contexts, for the raw target and after centring within night
(all nights; to three decimals); and, on the common endpoints of Table 10, the MAE (°C) of the source-training mean and median, of the
heater-conditioned source constant and of boosting at 900 s, with the night-level paired bootstrap difference
ΔMAE = MAE(source mean) − MAE(heater-conditioned constant) and its 95 % interval (2,000 resamples). The
heater-conditioned source constant is a diagnostic comparator, not an admissible estimator: the heater codes are
controller output that may depend on the measured temperature, and the constant mixes heater context with the
composition of the source subjects. User02 had heater-on context in only {{p13_table11_heater | subject_id=User02 | on_windows_full | ,d}}
windows, so inference about its heater-on state is very limited; its η² after centring within night and mat was
{{p13_table11_heater | subject_id=User02 | eta_night_x_mat_centred_full | .3f}}.

| Subject | Heater-on windows (share) | η² raw | η² within night | Source mean | Source median | Heater-conditioned source constant | ΔMAE [95 % interval] | Boosting 900 s |
|---|---|---|---|---|---|---|---|---|
| User01 | {{p13_table11_heater | subject_id=User01 | on_windows_full | ,d}} ({{p13_table11_heater | subject_id=User01 | on_share_pct_full | .1f}} %) | {{p13_table11_heater | subject_id=User01 | eta_raw_full | .3f}} | {{p13_table11_heater | subject_id=User01 | eta_night_centred_full | .3f}} | {{p13_table11_heater | subject_id=User01 | mae_source_mean_common | .2f}} | {{p13_table11_heater | subject_id=User01 | mae_source_median_common | .2f}} | {{p13_table11_heater | subject_id=User01 | mae_heater_conditioned_common | .2f}} | {{p13_table11_heater | subject_id=User01 | delta_mae | +.2f}} [{{p13_table11_heater | subject_id=User01 | ci_lower | +.2f}}, {{p13_table11_heater | subject_id=User01 | ci_upper | +.2f}}] | {{p13_table11_heater | subject_id=User01 | mae_hgb_900_common | .2f}} |
| User02 | {{p13_table11_heater | subject_id=User02 | on_windows_full | ,d}} ({{p13_table11_heater | subject_id=User02 | on_share_pct_full | .2f}} %) | {{p13_table11_heater | subject_id=User02 | eta_raw_full | .3f}} | {{p13_table11_heater | subject_id=User02 | eta_night_centred_full | .3f}} | {{p13_table11_heater | subject_id=User02 | mae_source_mean_common | .2f}} | {{p13_table11_heater | subject_id=User02 | mae_source_median_common | .2f}} | {{p13_table11_heater | subject_id=User02 | mae_heater_conditioned_common | .2f}} | {{p13_table11_heater | subject_id=User02 | delta_mae | +.2f}} [{{p13_table11_heater | subject_id=User02 | ci_lower | +.2f}}, {{p13_table11_heater | subject_id=User02 | ci_upper | +.2f}}] | {{p13_table11_heater | subject_id=User02 | mae_hgb_900_common | .2f}} |
| User07 | {{p13_table11_heater | subject_id=User07 | on_windows_full | ,d}} ({{p13_table11_heater | subject_id=User07 | on_share_pct_full | .1f}} %) | {{p13_table11_heater | subject_id=User07 | eta_raw_full | .3f}} | {{p13_table11_heater | subject_id=User07 | eta_night_centred_full | .3f}} | {{p13_table11_heater | subject_id=User07 | mae_source_mean_common | .2f}} | {{p13_table11_heater | subject_id=User07 | mae_source_median_common | .2f}} | {{p13_table11_heater | subject_id=User07 | mae_heater_conditioned_common | .2f}} | {{p13_table11_heater | subject_id=User07 | delta_mae | +.2f}} [{{p13_table11_heater | subject_id=User07 | ci_lower | +.2f}}, {{p13_table11_heater | subject_id=User07 | ci_upper | +.2f}}] | {{p13_table11_heater | subject_id=User07 | mae_hgb_900_common | .2f}} |

- **Association:** for User01 and User07, heater context was associated with temperature, and the association
  remained after centring within night (η² {{p13_table11_heater | subject_id=User01 | eta_raw_full | .3f}} raw and
  {{p13_table11_heater | subject_id=User01 | eta_night_centred_full | .3f}} within night for User01; {{p13_table11_heater | subject_id=User07 | eta_raw_full | .3f}} and
  {{p13_table11_heater | subject_id=User07 | eta_night_centred_full | .3f}} for User07). For User02 it was negligible
  ({{p13_table11_heater | subject_id=User02 | eta_raw_full | .3f}}, {{p13_table11_heater | subject_id=User02 | eta_night_centred_full | .3f}} and
  {{p13_table11_heater | subject_id=User02 | eta_night_x_mat_centred_full | .3f}} within night and mat), but with
  {{p13_table11_heater | subject_id=User02 | on_windows_full | ,d}} heater-on windows its heater-on state is essentially unobserved.
- **Direction:** windows after a heater-on code were colder than the other windows: their mean temperature minus that
  of the other windows was {{p13_summary_values | key=User01_temperature_on_minus_other_mean_full | value | +.2f}} °C for User01 and
  {{p13_summary_values | key=User07_temperature_on_minus_other_mean_full | value | +.2f}} °C for User07 (all nights; Table S42). This is the
  direction expected from a controller that switches the heater on after the temperature has fallen (Section 5.3).
- **Heater-conditioned source constant:** on the common endpoints it had a lower temperature MAE than the source mean
  for User01 ({{p13_table11_heater | subject_id=User01 | mae_source_mean_common | .2f}} → {{p13_table11_heater | subject_id=User01 | mae_heater_conditioned_common | .2f}} °C; ΔMAE
  {{p13_table11_heater | subject_id=User01 | delta_mae | +.2f}} °C [{{p13_table11_heater | subject_id=User01 | ci_lower | +.2f}}, {{p13_table11_heater | subject_id=User01 | ci_upper | +.2f}}]) and User07 ({{p13_table11_heater | subject_id=User07 | mae_source_mean_common | .2f}} →
  {{p13_table11_heater | subject_id=User07 | mae_heater_conditioned_common | .2f}} °C; ΔMAE {{p13_table11_heater | subject_id=User07 | delta_mae | +.2f}} °C [{{p13_table11_heater | subject_id=User07 | ci_lower | +.2f}}, {{p13_table11_heater | subject_id=User07 | ci_upper | +.2f}}]), close to boosting at 900 s
  ({{p13_table11_heater | subject_id=User01 | mae_hgb_900_common | .2f}} and {{p13_table11_heater | subject_id=User07 | mae_hgb_900_common | .2f}} °C); for User07 the source median
  ({{p13_table11_heater | subject_id=User07 | mae_source_median_common | .2f}} °C) was lower still. For User02 it was slightly worse
  ({{p13_table11_heater | subject_id=User02 | mae_source_mean_common | .2f}} → {{p13_table11_heater | subject_id=User02 | mae_heater_conditioned_common | .2f}} °C; ΔMAE
  {{p13_table11_heater | subject_id=User02 | delta_mae | +.2f}} °C [{{p13_table11_heater | subject_id=User02 | ci_lower | +.2f}}, {{p13_table11_heater | subject_id=User02 | ci_upper | +.2f}}]).
- **Not a heater effect:** the source pools differed in heater-context coverage between subjects. In the fold holding
  out User01, almost all source heater-on windows came from User07, and in the fold holding out User07 almost all came
  from User01 (Tables S41 and S44). The conditioned constant therefore also transfers the level of one source subject,
  and heater context and subject identity cannot be separated. For User01 humidity, η² was small
  ({{p12_heater_eta_squared | span=full, subject_id=User01, target=humidity, variant=A2_night_centred, scope=three_states | eta_squared | .3f}}
  within night), yet the conditioned constant lowered the MAE by {{p12_heater_bootstrap_common | subject_id=User01, target=humidity, first=source_mean, second=heater_conditioned_source_mean | point_estimate | +.2f}} %RH
  [{{p12_heater_bootstrap_common | subject_id=User01, target=humidity, first=source_mean, second=heater_conditioned_source_mean | ci_lower | +.2f}}, {{p12_heater_bootstrap_common | subject_id=User01, target=humidity, first=source_mean, second=heater_conditioned_source_mean | ci_upper | +.2f}}], an example of this
  composition effect (Table S44).
- **Humidity:** η² was at most {{p13_summary_values | key=eta_humidity_full_three_states_max | value | .3f}} for every subject and centring (Table S43).

## 5. Discussion

### 5.1. What Did Personalization Correct?

The post-hoc comparators (Section 4.7) change how the personalization results should be read.
- **Level correction, matched by a constant.** Under strict evaluation, most of the error was a level offset
  (Section 4.1). Chronological personalization reduced this offset when the adaptation nights were representative.
  A constant computed from the same adaptation labels, with no pressure input, often did nearly as well or better
  (Section 4.7), including the study's largest correction (User02 temperature) with the mean at every budget.
- **Compressed dynamics, no demonstrable tracking.** The unadapted network's errors varied more than the targets
  themselves. After fine-tuning, the variation of the predictions was strongly compressed: at b = 14 the prediction
  standard deviation was `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=E, budget_nights=14 | Q | .2f}}` times the target standard deviation for User02 temperature and
  `{{p8_dynamic_summary | subject_id=User07, target=temperature, condition=E, budget_nights=14 | Q | .2f}}` times for User07 temperature (Table 8), and the error spread was about that of a constant
  (Table 6). A network trained from scratch on the same adaptation nights was not worse than the pretrained model in
  {{COUNT:p8_interpretation_cases | case_I_S_approx_or_better_than_E=True}} of six subject–target cells at b = 14, and a constant computed from the adaptation labels explained much
  of the gain (Section 4.7). Prediction dynamics were therefore strongly compressed toward level-dominated behaviour,
  and cross-subject pretraining did not provide consistent additional predictive value over target-only training
  under the tested fixed adaptation protocol.
  - A direct correlation diagnostic (Section 4.8) found no consistent within-night co-variation.
  - After adaptation, User02's night-centred correlations mostly reflected the level difference between its two mats;
    within night and mat only a small positive temperature correlation remained, and pooled associations for User01
    reflected level alignment between nights.
  - Even a retrospective affine recalibration on the test labels would have left the residual variation close to the
    target variation.
  - Where the adapted networks beat the constant, they did so through a different level on the later span. Whether
    that level difference reflects a relation between pressure and microclimate or an incidental association cannot
    be decided with three subjects.
- **Consequence.** Under the tested 40-s RAW-pressure representation, TCN architecture and fixed training and
  adaptation schedules, we found no consistent evidence of superiority over simple level baselines, also when the
  network was retrained on the endpoints used by the summary models (Section 4.10).
  - In this cohort, the evidence supports chronological personalization as a level correction, which simpler
    predictors achieve as well.
  - It does not support within-subject microclimate tracking by this formulation.
  This is the main negative result of the study. It is a result about the tested formulation, not a statement that
  pressure cannot carry microclimate information.
- **Scope of the negative result.** It concerns the tested 40-s formulation. Summary models with longer pressure
  histories had a lower temperature error than the training mean for two subjects; what this does and does not show
  is discussed in Section 5.3.
- **One additional external subject (Section 4.9)** showed the same pattern: a simple level baseline beat all three
  source-only network configurations, with no demonstrable within-night co-variation. It is one post-hoc subject, not
  a replication.

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
{{COUNT:p6_level_mismatch_consistency | consistent=True}} of 24 cells (Section 4.5). It was formulated after the
results were known and uses the later span's labels, which a deployment does not have. It is descriptive evidence
after the fact, not a confirmatory test and not a deployable safeguard. These observations are consistent with
temporal representativeness being an important condition for successful personalization.

The role of such offsets resembles that of calibration in deployed environmental sensing, where field calibration
corrects systematic sensor errors [@maag2018calibration; @delaine2019insitu]. The pattern also parallels two ideas
from the literature:
- concept drift, a change over time in the relation between inputs and target [@gama2014survey];
- negative transfer from a less related source [@wang2019negative]. Here, the less related data would be the user's
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
  None of them was a model input; the heater codes were excluded from the inputs by design (Section 3.1) and used
  only descriptively (Section 4.11).
- **Consistency with the results:** within a subject, the pressure-based models did not follow the target variation
  (Table 6), and their within-night correlations with the targets were not consistently positive (Table 8).
- **Longer histories and heater context.**
  - In the exploratory analysis on endpoints with 15 min of continuous history, gradient-boosted models on 300-s and
    900-s pressure summaries had a lower temperature error than the source-training mean for User01 and User07
    (Section 4.10).
  - Retraining the 40-s network on the same endpoints showed that this pattern was not caused solely by the original
    network having been trained on a larger pool: the retrained network still did not consistently exceed the level
    baselines for temperature, and its error was close to that of the 40-s boosted model.
  - However, heater and controller context remained associated with temperature for User01 and User07 after centring
    within night (Section 4.11).
  - For User01, a source constant conditioned on heater context reached a temperature MAE of
    {{p13_table11_heater | subject_id=User01 | mae_heater_conditioned_common | .2f}} °C, close to the {{p13_table11_heater | subject_id=User01 | mae_hgb_900_common | .2f}} °C of
    boosting at 900 s.
  - This does not show that heater context produced the longer-history gain: the controller state is related to the
    target itself, the composition of the source subjects differs between heater contexts, occupancy and the room
    environment were not measured, and there was no intervention on the heater.
  - The longer-history gain therefore cannot be attributed uniquely to pressure-specific thermal memory. The
    longer-history pattern is consistent with several non-exclusive mechanisms, including sustained contact history,
    slower thermal or moisture dynamics, and pressure patterns that co-vary with controller or environmental context.
    These mechanisms cannot be separated with the present observational data.
- **Heater context is not an exposure.** Observed heater-on windows having a lower temperature does not imply that
  heater activation reduced the temperature. Because heater and control events may be triggered by the measured
  thermal state, the controller signal is potentially endogenous to the target. Heater context is therefore a
  diagnostic marker of the recording and control state rather than an independent causal environmental exposure,
  which is why it is excluded from the model inputs and used here only descriptively.
- **Consequence:** in this cohort, a pressure-only input under the tested formulation did not suffice for
  within-subject microclimate estimation.
  - Longer history windows were tested only with simple summary models; the retrained network kept the 40-s input
    (Section 4.10). State-space or long-context
    temporal models, contextual variables that are not derived from the target, and explicitly designed calibration
    mechanisms were not tested.
  - Contextual measurements would also reduce the sensor savings that motivate the approach.

### 5.4. Feature Engineering and Personalization Address Different Problems

- **Features:** movement and contact features lowered a single subject's error by at most
  `{{p4_incremental_effects | effect=A, target=temperature, metric=mae | delta_User01 | +.2f}}` °C (movement added to
  RAW, User01) and
  `{{p4_incremental_effects | effect=B, target=humidity, metric=mae | delta_User01 | +.2f}}` %RH (contact added to
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
  - a personalized constant was a strong competitor to full fine-tuning, and no pressure-based model showed
    demonstrable within-subject tracking (Section 4.7 and Section 4.10);
  - the RAW-TCN retrained on the endpoints of the summary models still did not consistently outperform the level
    baselines for temperature (Section 4.10);
  - cross-subject pretraining did not provide consistent additional predictive value over the scratch initialization
    control (Section 4.7).
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
devices are a known source of error in mobile sensing [@stisen2015smart]; here, the mat cannot be separated from its
microclimate and its heater history, and User02 had almost no heater-on context (Section 4.11). We do not attribute
the residual to a device defect, to the heater or to a property of the user.

### 5.8. Practical Implications (Not Tested)

- **Baselines:** an adaptive smart-mat estimator should be compared with a personalized constant computed from the
  same adaptation labels, and its within-night co-variation with the target should be reported. In this cohort, that
  constant was a strong competitor.
- **Commissioning:** in the commissioning scenario of Section 1, the reference labels of the first nights already
  yield the personalized constant. A pressure model adds value only if it improves on that constant in the later
  period, which was not shown here.
- **Safeguards:** the level-mismatch rule of Section 4.5 needs future labels and cannot be applied at deployment.
  Candidates that use only information available at the time exist in neighbouring fields:
  - monitoring drift after adaptation [@gama2014survey], or using adaptive estimators, as for data-driven soft
    sensors [@kadlec2011adaptation];
  - periodic recalibration against reference measurements, as for deployed environmental sensors
    [@delaine2019insitu];
  - selecting or weighting adaptation data.
None of these safeguards was evaluated here; they are future work.

## 6. Limitations

- **Cohort and inference:** the study has three independent primary subjects. Their recording periods do not
  overlap, so subject, recording period, season, mat and microclimate are confounded in every fold. The results
  therefore describe three combined domain shifts; they support no population-level inference and no statistical
  significance across subjects.
- **Post-hoc comparators:**
  - They were designed after the primary results were known. Their design was fixed
    before they were computed, but the decision to run them was motivated by the results.
  - The initialization control used the short, fixed fine-tuning schedule, one architecture and only b = 14; it is
    not an upper bound on what a within-subject model could learn.
  - R is a descriptive ratio of population standard deviations over spans with drifting levels. R ≈ 1 does not
    exclude a small tracking component masked by noise.
  - The dynamic-signal diagnostic is second-order post hoc: it was added after the comparator results were known,
    although its rules were fixed before it was computed. Its correlations and the oracle ratio are linear
    diagnostics. They do not exclude a nonlinear relation or one at a longer time scale than the 40-s window, and
    night-centring removes between-night trends by design.
- **Additional external subject:** it was evaluated post hoc with seven nights, too few for night-level intervals,
  and its rows are reconstructed from two exports of the same nights, with the values taken from the subject's valid
  export and the second-level timestamps from a complementary export that the data provider confirmed to be
  unaffected by the setting problem for which that source is otherwise excluded (Section 3.5.7). It is not part of
  the primary cohort.
- **Inputs and scope:** only pressure was used, in one representation (40-s RAW windows), one model family (TCN)
  and fixed training and adaptation schedules. The negative result is scoped to this formulation. Room climate,
  bedding and occupancy context were not measured; the heater codes were excluded from the inputs under the leakage
  policy and used only descriptively.
- **Adaptation design:**
  - One frozen full fine-tuning recipe was evaluated (learning rate, epochs and scope fixed in advance).
  - Adaptation always used the earliest recorded nights, as a deployment would, so its effect is tied to how
    representative those nights are; other samplings of adaptation data were not studied.
  - The commissioning scenario was emulated with the mats' own sensors and not evaluated operationally.
- **Confounded labels:** User01's pressure-sensor replacement falls inside the primary test span and coincides with a
  change in time and season, so their effects cannot be separated; a large humidity-level change occurred earlier,
  inside the adaptation nights, and has no identified cause. The differences between the two User02 mats have no
  causal interpretation.
- **Sensor documentation:** the temperature–humidity sensor model, accuracy, response time and placement were not
  documented; no statement about measurement validity or physical mechanisms is made.
- **Statistics:** the night-level bootstrap resamples nights independently. Consecutive nights are correlated
  through drift, so the intervals may be too narrow for trending series, and the serial dependence between nights is
  not fully captured. Windows, nights and seeds are not independent replicates of the three subjects, and counts over
  the 24 cells are not independent tests. The level-mismatch rule was formulated post hoc and uses the later span's
  labels; its agreement with {{COUNT:p6_level_mismatch_consistency | consistent=True}} of 24 cells is an association, not a causal test.
- **Adaptation schedule:** with a fixed number of epochs, larger budgets also received more optimizer updates, so the
  effect of more nights cannot be separated from that of more updates.
- **Exploratory analyses (Sections 3.5.8–3.5.9):** designed with all other results known; one tree family with small
  grids; evaluated on the roughly half of the endpoints with 15 min of continuous history, which may favour long,
  stable recordings. The retrained network kept the configuration selected on the full pool, and its re-derived epoch
  count changed with the pool, so the effect of the pool includes that of the epoch count.
- **Heater diagnostic:** observational and post hoc. Only heater on/off codes define the context; the meaning of
  several other heater-related codes (for example the code FOF) is known only from their names, so windows without
  a context can still follow heater actions. The controller state is potentially endogenous to the target. The source
  pools differ in heater-context composition between subjects, so the heater-conditioned constant mixes heater
  context with subject identity, and User02 has almost no heater-on windows. Ambient climate was not measured
  independently, and the heater was never manipulated. The mechanisms behind the longer-history gain therefore cannot
  be separated.
- **Analyses not run:** the declared 20-s and 30-s window sensitivity analyses and a sensitivity analysis for the
  4095 saturation value were not run; the procedures they would need were not fixed in advance.
- **Reproduction scope:** the hyperparameter searches were not rerun; the reproduction reuses their committed
  selections (Section 3.7). The post-hoc analyses were reproduced from the frozen models, not from the release
  package, and the heater-context diagnostic cannot be reproduced from the release package (Section 3.7).
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
  - The mean target of the adaptation nights, which needs no pressure input, was a strong competitor to full
    fine-tuning, and the adapted networks' prediction dynamics were strongly compressed toward level-dominated
    behaviour.
  - No pressure-based model showed demonstrable within-subject tracking of temperature or humidity, and the neural
    predictions showed no consistent within-night co-variation with the targets. User02's night-centred correlations
    after adaptation mostly reflected the level difference between its two mats.
  - Cross-subject pretraining did not provide consistent additional predictive value over target-only training under
    the tested fixed adaptation protocol.
- **Additional external subject (post hoc):** a training-mean predictor again had a lower error than every
  source-only network configuration, with no demonstrable within-night co-variation.
- **Longer histories (exploratory):** gradient-boosted models on 5–15-min pressure summaries reduced the temperature
  error in {{COUNT:p10_history_interpretation | family=hgb, history_s=900, target=temperature, H_a_beats_training_mean_common=True}} of 3 cases, through smaller level offsets and without demonstrated within-night co-variation.
  Retraining the 40-s network on the same endpoints did not overturn the primary finding. The longer-history gains
  cannot be uniquely attributed to pressure-specific thermal dynamics, because controller, heater and environmental
  mechanisms remain entangled with them in these observational data. The results do not demonstrate an absence of
  useful pressure information.
- **Consequence:** under the tested 40-s RAW-pressure representation, TCN architecture and fixed training and
  adaptation schedules, pressure-dependent neural prediction did not show a consistent advantage over simple level
  baselines in these three cases; simpler models with longer histories reduced the offset in some cases but did not
  show tracking. Future work should evaluate other formulations against the same baselines:
  - longer history windows with models and evaluation designed for them;
  - long-context temporal models;
  - contextual measurements that do not derive from the target, such as independently logged heater operation and
    ambient climate, with a documented sensor placement;
  - explicitly designed calibration;
  - larger multi-user and multi-device cohorts.
  This should happen before pressure-based microclimate estimation is deployed.

## Supplementary Materials

<!-- Template wording; the editorial office completes the link. -->
The following supporting information can be downloaded at: https://www.mdpi.com/article/doi/s1, Figure S1: Absolute bias versus the adaptation budget b: (a) temperature, (b) humidity; Figure S2: Start-span
sensitivity of the adaptation gain, post hoc: (a) temperature, (b) humidity, for b = 1, 3, 7 and 14 (for b = 14 only
start nights ≥ 16 are defined); Figure S3: Target-level trajectories over night ordinals for User07 temperature,
User01 humidity and User02 temperature, post hoc and descriptive; Figure S4: User02 MAE by mat (22480, 22482) versus
the adaptation budget b: (a) temperature, (b) humidity; Figure S5: One example night per held-out subject, selected by
a fixed rule, with total pressure, temperature, humidity and heater on/off codes over relative time; Table S1: Strict leave-one-subject-out results per seed and
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
S30: Retrospective oracle affine ratio and calibration trigger; Table S31: Dynamic-signal cases J1–J8; Table S32:
Additional external validation, reconciliation coverage and windows, post hoc; Table S33: Additional external
validation per configuration and seed; Table S34: Additional external validation per night and pre-registered
interpretation; Table S35: Median constants, strict leave-one-subject-out and primary span, exploratory; Table S36:
Point-estimate counts of constants versus networks, exploratory; Table S37: Endpoint availability by history,
exploratory; Table S38: Pressure-summary models: errors, co-variation, night-level intervals and pre-specified reading,
with the RAW-TCN trained on all 40-s windows as a training-pool sensitivity reference, exploratory; Table S39: RAW-TCN
retrained on the common endpoints: per seed, epoch selection and pool counts, exploratory; Table S40: RAW-TCN retrained
on the common endpoints: night-level intervals and pre-specified reading, exploratory; Table S41: Heater-control code
audit and heater-context coverage, post hoc; Table S42: Target level by heater context, post hoc; Table S43: Eta squared
of heater context for both targets and all centrings, post hoc; Table S44: Heater-conditioned source constant, its
night-level intervals and source composition, and errors by heater context, post hoc.

## Author Contributions

[CRediT ROLES — CONFIRM] (skeleton in AUTHOR_CONTRIBUTIONS_DRAFT.md; no role is assigned before PI confirmation.)
All authors have read and agreed to the published version of the manuscript. [CONFIRM]

## Funding

[FUNDING TO BE CONFIRMED BY PI] (the conference paper's funding statement is not carried over automatically)

## Institutional Review Board Statement

[ETHICS / IRB INFORMATION REQUIRED FROM PI]

## Informed Consent Statement

[INFORMED CONSENT WORDING REQUIRED FROM PI]

<!-- Note for the PI: the data provider's confirmation that participant consent was obtained and that the data may be
used and released for research (D-002) is documented. It is not an institutional ethics approval and does not by
itself supply the consent statement. -->

## Data Availability Statement

<!-- Current-state text. Must not say "publicly available" until OPEN-22/23/24 are resolved. Code availability and
the reproduction statement are part of this section because the template has no separate sections for them. -->
The raw sensor recordings analysed in this study are not publicly released, and restricted participant metadata is
never released. A de-identified, model-ready derived dataset (`public_release_v1`) has been prepared as a release
candidate. It contains the model-ready windows of the three anonymous participants (four mat streams), the
evaluation splits and the reference digests needed to reproduce the reported results. Time is given only relative to
each participant's first recorded night. External availability of this dataset is pending the choice of a data
license, a repository with a persistent identifier and final approval. [PI DECISION: interim availability on
reasonable request, and from whom.] Data repository: [DATA REPOSITORY]. DOI: [DOI]. License: [LICENSE].

The code for data preparation, model training, evaluation and the reproduction of the reported results is maintained
in a version-controlled GitHub repository, which is currently publicly accessible; the data themselves are not part of
it. [PI DECISION: confirm the public code release scope (the committed history contains session-level recording dates
outside the de-identified release package) and the license.] Code repository: [CODE REPOSITORY URL — CONFIRM]. Archive
DOI: [DOI]. License: [LICENSE].

From the derived release package and the frozen model selections, a clean
checkout reproduced the selected leave-one-subject-out models (with their weight digests), the predictions of the
feature-family and personalization runs, the night-level analyses and every reproduced result table, bitwise. The
hyperparameter searches were not rerun (Section 3.7). The reconstructed rows of the additional external subject
(Section 3.5.7) are not part of the release candidate. The exploratory analyses of Sections 3.5.8–3.5.9 use the
canonical dataset; the heater-context diagnostic needs heater codes that the release candidate contains for one
subject only.

## Acknowledgments

[OTHER ACKNOWLEDGMENTS — CONFIRM]

<!-- OPEN-28 / D-052: tool inventory in docs/P8_FINAL_BLOCKERS.md; PI approval required before submission. The
ChatGPT entry and its model information are the authors' statement; historical ChatGPT model versions were not
logged and are not inferred. -->
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

[Rendered from references.bib by scripts/build_submission_candidate.py: numbered in order of first citation.]
