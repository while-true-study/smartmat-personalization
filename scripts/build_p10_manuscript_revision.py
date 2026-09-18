"""Build paper/manuscript/manuscript_p10_revision.md from manuscript.md by exact, checked replacements (D-064).

  python scripts/build_p10_manuscript_revision.py && python scripts/render_p10_revision.py

manuscript.md is read only. Every replacement target must occur exactly once, so the revision is auditable and fails if
the source changes. New numbers are source tokens resolved from paper/tables/p10_*.csv.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_text  # noqa: E402

SRC = paths.PROJECT_ROOT / "paper" / "manuscript" / "manuscript.md"
DST = paths.PROJECT_ROOT / "paper" / "manuscript" / "manuscript_p10_revision.md"
t = SRC.read_text(encoding="utf-8").replace("\r\n", "\n")

N12 = "{{COUNT:p8_interpretation_cases | case_A_B_le_E=True}}"
N7 = "{{p10_point_counts | setting=rq2_primary_span, comparison=B_med MAE <= E (fine-tuning) seed-mean MAE | count | d}}"
GB_T = "{{COUNT:p10_history_interpretation | family=hgb, history_s=900, target=temperature, H_a_beats_training_mean_common=True}}"


def v(table, filters, col, spec):
    return "{{" + f"{table} | {filters} | {col} | {spec}" + "}}"


def hm(subject, target, predictor, history, seed, col, spec):
    return v("p10_history_metrics", f"subject_id={subject}, target={target}, predictor={predictor}, "
                                    f"history_s={history}, seed={seed}", col, spec)


R = []

# ---------------------------------------------------------------- header comment and Featured Application
R.append(("""<!--
P8 formatting pass: manuscript source of the submission candidate (formatting-complete candidate for PI review).""",
"""<!--
P10 REVISION (D-064): a revised copy of paper/manuscript/manuscript.md, which is kept unchanged. Changes are listed in
paper/manuscript/REVISION_P10_NOTES.md. New numbers are tokens resolved from paper/tables/p10_*.csv.
P8 formatting pass: manuscript source of the submission candidate (formatting-complete candidate for PI review)."""))

R.append(("""**Featured Application:** This study provides a deployment-oriented evaluation framework for smart-mat temperature
and humidity estimation. In three held-out cases, limited chronological user adaptation mainly corrected
unseen-domain prediction offsets, which a personalized constant corrected as well, and the neural predictions showed
no consistent within-night co-variation with the measured microclimate; simple level baselines are therefore needed to
judge such systems.""",
"""**Featured Application:** Smart-mat temperature and humidity estimators should be reported against simple level
baselines under subject-wise and chronological evaluation. In three held-out cases, limited chronological user
adaptation mainly corrected unseen-domain prediction offsets, which a personalized constant often corrected as well,
and no pressure-based model showed within-night co-variation with the measured microclimate beyond a level
difference."""))

# ---------------------------------------------------------------- Abstract
R.append(("""Smart-mat pressure could yield bed-microclimate temperature and humidity estimates without extra sensors, but
deployed models face unseen users, periods and mats. We evaluated temporal convolutional networks on 40-s pressure
windows from three subjects (four mat streams) under strict leave-one-subject-out evaluation; each held-out fold was an
unseen domain of subject, period and mat. Models were fine-tuned on each subject's earliest 1–14 nights and tested
on a fixed later span. Strict-evaluation errors were dominated by level offsets; for temperature, the network did not beat a
training-mean predictor. Fine-tuning moved one subject's temperature bias from
{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_0 | +.2f}} to
{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_b | +.2f}} °C after 14 nights,
whereas another subject's seed-mean temperature error exceeded its base model's at every budget. Post-hoc comparators
showed mainly level corrections: the mean target of the adaptation nights, which uses no pressure input, was not worse
than full fine-tuning in {{COUNT:p8_interpretation_cases | case_A_B_le_E=True}} of 24 subject–target–budget cells.
Night-centred correlations showed no consistent within-night co-variation between predictions and targets, and a
retrospective affine recalibration on the test labels could not have lowered the residual standard deviation
below {{p8_dynamic_summary | subject_id=User02, target=temperature, condition=S, budget_nights=14 | oracle_affine | .2f}} times the target's. Under the tested representation, architecture and schedules,
pressure-based neural estimation showed no consistent advantage over simple level baselines, also for one
post-hoc external subject. With three subjects, these
findings are case-level.""",
f"""Smart-mat pressure could yield bed-microclimate temperature and humidity estimates without extra sensors, but
deployed models face unseen users, periods and mats. We evaluated temporal convolutional networks on 40-s pressure
windows from three subjects (four mat streams) under strict leave-one-subject-out evaluation, each held-out subject being
an unseen domain of subject, period and mat, and fine-tuned them on each subject's earliest 1–14 nights with a fixed
later test span. Errors were dominated by level offsets; for temperature, the network did not beat a training-mean
predictor. Fine-tuning moved one subject's temperature bias from
{{{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_0 | +.2f}}}} to
{{{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_b | +.2f}}}} °C after 14 nights,
whereas another subject's error rose at every budget. In post-hoc comparisons, the adaptation-night target mean, which
uses no pressure input, had a point-estimate error no higher than fine-tuning in {N12} of 24 subject–target–budget
cells ({N7} with the median). No consistent within-night co-variation was found; one subject's positive night-centred
correlations after adaptation largely disappeared when centred within night and mat. In an exploratory analysis,
gradient-boosted models on 5–15-min pressure summaries beat the training mean for temperature in {GB_T} of 3
subjects, through smaller offsets rather than within-night tracking. The findings are limited to three retrospective
cases."""))

# ---------------------------------------------------------------- Introduction
R.append(("""post-hoc diagnostic measured the prediction scale and the pooled and within-night correlations between predictions and
targets (Section 3.5.6).""",
"""post-hoc diagnostic measured the prediction scale and the pooled and within-night correlations between predictions and
targets (Section 3.5.6). After an internal review of a draft, an exploratory addendum checked whether these readings
depend on the choice of constant (mean or median) and whether simple pressure-summary models with histories of up to
15 min beat the level baseline under strict leave-one-subject-out evaluation (Section 3.5.8). The question that these
post-hoc analyses address, how much of the personalization gain is level correction and whether pressure adds
tracking beyond it, became explicit only after the primary results were known."""))

R.append((f"""3. A post-hoc comparator analysis showing that the personalization gains were mainly level corrections: a
   personalized constant had an error no higher than full fine-tuning in
   {N12} of 24 cells, the pressure-based models showed no
   demonstrable within-subject tracking of the targets, and cross-subject pretraining added little over training on
   the adaptation nights alone. A final diagnostic found no consistent within-night co-variation between the neural
   predictions and the targets and little retrospective linear-calibration headroom.
4. A night-level robustness analysis: a paired cluster bootstrap, seed and start-span sensitivity, and post-hoc
   temporal level-mismatch and device-residual diagnostics.
5. A secondary comparison of six pressure feature families under the same protocol. It shows target-dependent,
   non-additive contributions of movement and contact features and a level offset that no representation removes
   (RQ3).
6. A de-identified, model-ready release candidate""",
f"""3. A post-hoc comparator analysis showing that the personalization gains were mainly level corrections: a
   personalized constant (the adaptation-night target mean) had a point-estimate error no higher than full
   fine-tuning in {N12} of 24 cells ({N7} with the adaptation-night median), the pressure-based models showed no
   demonstrable within-subject tracking of the targets, and cross-subject pretraining added little over training on
   the adaptation nights alone. A final diagnostic found no consistent within-night co-variation between the neural
   predictions and the targets once the level difference between one subject's two mats was removed, and little
   retrospective linear-calibration headroom.
4. An exploratory scope check with median constants and with ridge and gradient-boosted models on 40-s, 5-min and
   15-min pressure summaries. It narrows the negative result: a gradient-boosted model beat the training mean for
   temperature in {GB_T} of 3 held-out subjects, on endpoints with 15 min of continuous history, through a smaller
   offset and without within-night co-variation.
5. A night-level robustness analysis: a paired cluster bootstrap, seed and start-span sensitivity, and post-hoc
   temporal level-mismatch and device-residual diagnostics.
6. A secondary comparison of six pressure feature families under the same protocol. It shows target-dependent,
   non-additive contributions of movement and contact features and a level offset that no representation removes
   (RQ3).
7. A de-identified, model-ready release candidate"""))

# ---------------------------------------------------------------- Methods
R.append(("""microclimate for every model in this study.

**Cohort:**""",
"""microclimate for every model in this study. The temperature–humidity sensor model, its accuracy and response time,
and its position relative to the body and the heater are not documented in the delivered data and are not assumed here
[TEMPERATURE–HUMIDITY SENSOR MODEL, ACCURACY AND PLACEMENT — CONFIRM WITH DATA PROVIDER].

**Cohort:**"""))

R.append(("""  - User01's sensor phases s1 and s2, before and after a sensor replacement;""",
"""  - User01's sensor phases s1 and s2, before and after a documented replacement of the **pressure** sensor (a
    study-log note of the data provider; no replacement of the temperature–humidity sensor is documented). The
    adaptation nights of every budget lie in s1, whereas the primary test span (nights ≥ 16) contains both s1 and s2
    nights. A large change in User01's humidity level, seen in the data audit across a recording gap inside the
    seven-night adaptation span, precedes this replacement; its cause (season, heating, bedding or acquisition) is not
    identified;"""))

R.append(("""  The recipe and the per-subject plan (nights, windows, base checkpoints) were committed before any adaptation run.""",
"""  The recipe and the per-subject plan (nights, windows, base checkpoints) were committed before any adaptation run.
  Because the number of epochs is fixed, the number of optimizer updates grows with the number of adaptation windows
  (Table S13): budgets differ in both data and update count."""))

R.append(("""  - Night-cluster intervals require at least 10 nights (Section 3.6).

### 3.6. Metrics and Statistical Analysis""",
"""  - Night-cluster intervals require at least 10 nights (Section 3.6).

#### 3.5.8. Exploratory Addendum: Median Constants and Pressure-Summary Histories (Post Hoc)

After an internal review of a draft, a fourth protocol addendum was written, with all results above known and before
any of its metrics was computed. It is exploratory and replaces no result above.
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
  RAW-TCN (trained on all 40-s windows) and the constants were re-evaluated on the same endpoints.
- **Reading, fixed in advance:** a model beats the level baseline if the night-level paired bootstrap interval of
  MAE(training mean) − MAE(model) lies above zero; variation beyond level requires R < 1 and a night-centred
  correlation of at least 0.10 (for User02 also within night and mat). Longer history is associated with lower error
  if the interval of MAE(40 s) − MAE(longer history) lies above zero. None of these readings implies a thermal time
  constant.

### 3.6. Metrics and Statistical Analysis"""))

R.append(("""  - Windows are never treated as independent samples, and with three subjects no population-level significance is
    claimed.""",
"""  - Windows are never treated as independent samples, and with three subjects no population-level significance is
    claimed.
- **Units of independence:** the three subjects are the independent units. Nights, windows and model seeds are nested
  within them and are not independent replicates. The 24 subject–target–budget cells share subjects, targets and base
  models, so counts over cells are descriptive summaries, not 24 independent tests."""))

R.append(("""  - the additional external validation of Section 3.5.7, which follows a third addendum.""",
"""  - the additional external validation of Section 3.5.7, which follows a third addendum;
  - the exploratory addendum of Section 3.5.8."""))

R.append(("""- **Software:** Python 3.12.1, PyTorch 2.12.0 with CUDA 12.6, NumPy 2.4.4, PyArrow 24.0.0 and Matplotlib 3.10.9, with
  deterministic settings; bitwise equality of reruns was verified on the recorded GPU stack.""",
"""- **Exploratory addendum (Section 3.5.8):** rerun into a separate output directory; every table and every prediction
  file was identical. It used scikit-learn 1.8.0 in addition.
- **Software:** Python 3.12.1, PyTorch 2.12.0 with CUDA 12.6, NumPy 2.4.4, PyArrow 24.0.0 and Matplotlib 3.10.9, with
  deterministic settings; bitwise equality of reruns was verified on the recorded GPU stack. Reproducibility shows
  that the reported numbers follow from the data and code; it does not establish the validity of the measurements or
  any physical explanation."""))

# ---------------------------------------------------------------- Results
lm = lambda s, t, p, c, spec: v("p10_loso_metrics", f"subject_id={s}, target={t}, predictor={p}, seed=", c, spec)  # noqa: E731
R.append(("""- **Seeds:** the spread across the three seeds was much smaller than the differences between subjects (Table S1).""",
f"""- **Seeds:** the spread across the three seeds was much smaller than the differences between subjects (Table S1).
- **Choice of constant (exploratory, Section 3.5.8):** with the training median instead of the mean, the constant still
  had a lower temperature MAE than the RAW-TCN for User02 and User07, but not for User01
  (`{lm('User01', 'temperature', 'training_median', 'mae', '.2f')}` °C). The statement for temperature above is
  specific to the mean."""))

R.append(("""- **User07 temperature (negative transfer):** the seed-mean MAE was higher than that of the base model at every
  adaptation budget.""",
"""- **User07 temperature (negative transfer, i.e. adaptation-induced degradation relative to its own base model):** the
  seed-mean MAE was higher than that of the base model at every adaptation budget."""))

R.append(("""error). Seed 0: point estimate and 95 % interval from 2,000 resamples; then the side of zero for seeds 0 / 1 / 2.""",
"""error). MAE of B: a single deterministic value; MAE of E and S: mean ± standard deviation over model seeds 0, 1 and 2.
The Δ point estimates and 95 % intervals refer to model seed 0 only (2,000 resamples); then the side of zero for seeds
0 / 1 / 2."""))

R.append(("""- **A personalized constant often matched full fine-tuning.**
  - The adaptation-target mean (B) had a seed-mean MAE no higher than full fine-tuning (E) in
    `{{COUNT:p8_interpretation_cases | case_A_B_le_E=True}}` of 24 subject–target–budget cells
    (`{{COUNT:p8_interpretation_cases | case_A_B_le_E=True, budget_nights=14}}` of six at b = 14).""",
f"""- **A personalized constant often came close to or below full fine-tuning.**
  - The MAE of the adaptation-target mean (B) was no higher than the seed-mean MAE of full fine-tuning (E) in
    `{N12}` of 24 subject–target–budget cells
    (`{{{{COUNT:p8_interpretation_cases | case_A_B_le_E=True, budget_nights=14}}}}` of six at b = 14). This compares
    point estimates; it is not a test of equivalence or non-inferiority.
  - With the adaptation-night median instead of the mean (exploratory, Section 3.5.8), the count was `{N7}` of 24.
    Many of these cells are close, so the count depends on the choice of constant."""))

R.append(("""- **After adaptation: level alignment between nights or mats.** At b = 14:
  - for User01 temperature, the pooled correlation of full fine-tuning was
    `{{p8_dynamic_summary | subject_id=User01, target=temperature, condition=E, budget_nights=14 | r_pooled | +.2f}}`, and its within-night correlation
    `{{p8_dynamic_summary | subject_id=User01, target=temperature, condition=E, budget_nights=14 | r_within | +.2f}}`;
  - for User02 temperature, the night-centred correlation `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=E, budget_nights=14 | r_within | +.2f}}` fell to
    `{{p8_dynamic_summary | subject_id=User02, target=temperature, condition=E, budget_nights=14 | r_within_mat | +.2f}}` when centred within night and mat.
  These are level alignments between nights or between mats, not within-night tracking. For User07 temperature and
  User01 humidity, the pooled correlations were negative.""",
"""- **After adaptation, User02: mostly the two mats' level difference.** User02 is the only subject recorded on two
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
  temperature and User01 humidity, the pooled correlations were negative."""))


def row(s, t):
    cells = [s, t, f"{hm(s, t, 'training_mean_common', '', '', 'n_windows', ',d')} / "
                   f"{hm(s, t, 'training_mean_common', '', '', 'n_nights', 'd')}",
             hm(s, t, "training_mean_common", "", "", "mae", ".2f"),
             hm(s, t, "training_median_common", "", "", "mae", ".2f"),
             hm(s, t, "raw_tcn", "40", "mean", "mae", ".2f"),
             hm(s, t, "ridge", "40", "", "mae", ".2f"), hm(s, t, "ridge", "900", "", "mae", ".2f"),
             hm(s, t, "hgb", "40", "", "mae", ".2f"), hm(s, t, "hgb", "300", "", "mae", ".2f"),
             hm(s, t, "hgb", "900", "", "mae", ".2f"),
             f"{hm(s, t, 'hgb', '900', '', 'bias', '+.2f')} / {hm(s, t, 'hgb', '900', '', 'R', '.2f')} / "
             f"{hm(s, t, 'hgb', '900', '', 'r_within', '+.2f')}"]
    return "| " + " | ".join(cells) + " |"


table10 = "\n".join(
    ["| Subject | Target | Common endpoints (windows / nights) | Training mean | Training median | RAW-TCN 40 s | "
     "Ridge 40 s | Ridge 900 s | Boosting 40 s | Boosting 300 s | Boosting 900 s | Boosting 900 s: bias / R / r within night |",
     "|" + "---|" * 12] + [row(s, t) for t in ("temperature", "humidity") for s in ("User01", "User02", "User07")])

hi = lambda f, h, s, t, c: v("p10_history_interpretation", f"family={f}, history_s={h}, subject_id={s}, target={t}", c, "s")  # noqa: E731
R.append(("""## 5. Discussion""",
f"""### 4.10. Exploratory Addendum: Median Constants and Pressure-Summary Histories (Post Hoc)

**Table 10.** Exploratory addendum (Section 3.5.8), strict leave-one-subject-out evaluation on the endpoints with 40-s,
300-s and 900-s histories available. MAE in °C (temperature) or %RH (humidity) of the training mean and median of the
common training endpoints, the frozen RAW-TCN (mean over seeds 0–2; trained on all 40-s windows), ridge regression and
histogram gradient boosting on pressure summaries; for boosting at 900 s also the bias, R and the night-centred
correlation. Night-level intervals, all histories and the per-cell reading: Tables S37–S38.

{table10}

- **Reproduction:** every frozen metric used here was reproduced from the frozen predictions within the tolerance, and
  the whole addendum reproduced exactly in a separate rerun.
- **Endpoints:** a 900-s history needs 15 min without a recording gap longer than 5 s, so about half of the labelled
  endpoints qualified (Table S37); the comparisons below are on that subset.
- **Temperature:** gradient boosting with 300-s or 900-s histories beat the training mean in
  {GB_T} of 3 subjects (User01 and User07; night-level intervals above zero) and not for User02, where every pressure
  model was worse than the constant; ridge regression beat it in none. The gains came with a smaller offset, R stayed
  above 1, and the night-centred correlations were near zero or negative. For User07 the training median had a lower
  MAE than the boosted models.
- **Humidity:** both model families beat the training mean for User01 and User02 at every history and were worse for
  User07, the same pattern as the 40-s RAW-TCN in Table 2.
- **History length:** for temperature, the 300-s and 900-s histories had a lower error than the 40-s history in all three
  subjects for gradient boosting, mostly through a smaller offset. This is an association on the common endpoints, not
  evidence of a thermal lag.
- **Variation beyond level:** no model met the pre-specified rule (R < 1 with a night-centred correlation of at least
  0.10) for any subject and target.
- The RAW-TCN and the summary models differ in representation, model family and training pool, so their difference is
  not attributed to history length or read as overfitting.

## 5. Discussion"""))

# ---------------------------------------------------------------- Discussion
R.append((f"""  A constant computed from the same adaptation labels, with no pressure input, did the same: it was not worse than
  full fine-tuning in {N12} of 24 cells, including the study's largest correction (User02 temperature).""",
f"""  A constant computed from the same adaptation labels, with no pressure input, often did nearly as well or better: its
  point-estimate error was no higher than that of full fine-tuning in {N12} of 24 cells with the mean and {N7} with the
  median, including the study's largest correction (User02 temperature) with the mean at every budget."""))

R.append(("""  - Pooled associations after adaptation reflected level alignment between nights or between mats.""",
"""  - After adaptation, User02's night-centred correlations mostly reflected the level difference between its two mats;
    within night and mat only a small positive temperature correlation remained, and pooled associations for User01
    reflected level alignment between nights."""))

R.append(("""  This is the main negative result of the study. It is a result about the tested formulation, not a statement that
  pressure cannot carry microclimate information.""",
f"""  This is the main negative result of the study. It is a result about the tested formulation, not a statement that
  pressure cannot carry microclimate information.
- **Scope of the negative result (exploratory addendum, Section 4.10).** It does not extend to every pressure model: a
  gradient-boosted model on 5–15-min pressure summaries had a lower temperature error than the training mean in
  {GB_T} of 3 subjects. That advantage was a smaller level offset on the held-out subject, without within-night
  co-variation, on endpoints with 15 min of continuous history, and it depended on the mean being the reference
  constant for one subject. It narrows, but does not reverse, the reading that simple level information explains most
  of what the pressure models achieved."""))

R.append(("""  - This study does not test the explanation.""",
"""  - This study does not test the explanation. In the exploratory addendum, longer pressure histories were associated
    with a lower temperature error of simple summary models, mostly through smaller offsets. This is consistent with,
    but does not demonstrate, a role of longer context, and it is not evidence of a thermal time constant."""))

R.append(("""  - Other formulations were not tested: longer occupancy or history windows, state-space or long-context temporal
    models, contextual variables that are not derived from the target, and explicitly designed calibration
    mechanisms.""",
"""  - Longer history windows were tested only with simple summary models (Section 4.10). State-space or long-context
    temporal models, contextual variables that are not derived from the target, and explicitly designed calibration
    mechanisms were not tested."""))

R.append((f"""  - a personalized constant was not worse than full fine-tuning in {N12} of 24 cells, and no
    pressure-based model showed demonstrable within-subject tracking (Section 4.7);""",
f"""  - a personalized constant had a point-estimate error no higher than full fine-tuning in {N12} of 24 cells ({N7}
    with the median), and no pressure-based model showed demonstrable within-subject tracking (Sections 4.7 and 4.10);"""))

# ---------------------------------------------------------------- Limitations
R.append(("""- **Confounded labels:** User01's sensor phases coincide with a change in time and season, so their effects cannot
  be separated. The differences between the two User02 mats have no causal interpretation.""",
"""- **Confounded labels:** User01's pressure-sensor replacement falls inside the primary test span and coincides with a
  change in time and season, so their effects cannot be separated; a large humidity-level change occurred earlier,
  inside the adaptation nights, and has no identified cause. The differences between the two User02 mats have no
  causal interpretation.
- **Sensor documentation:** the temperature–humidity sensor model, accuracy, response time and placement were not
  documented; no statement about measurement validity or physical mechanisms is made."""))

R.append(("""- **Statistics:** the night-level bootstrap resamples nights independently. Consecutive nights are correlated
  through drift, so the intervals may be too narrow for trending series, and the serial dependence between nights is
  not fully captured. The level-mismatch rule was formulated post hoc and uses the later span's labels.""",
"""- **Statistics:** the night-level bootstrap resamples nights independently. Consecutive nights are correlated
  through drift, so the intervals may be too narrow for trending series, and the serial dependence between nights is
  not fully captured. Windows, nights and seeds are not independent replicates of the three subjects, and counts over
  the 24 cells are not independent tests. The level-mismatch rule was formulated post hoc and uses the later span's
  labels; its agreement with {{COUNT:p6_level_mismatch_consistency | consistent=True}} of 24 cells is an association, not a causal test.
- **Adaptation schedule:** with a fixed number of epochs, larger budgets also received more optimizer updates, so the
  effect of more nights cannot be separated from that of more updates.
- **Exploratory addendum:** designed with all other results known; one tree family with small grids; evaluated on the
  roughly half of the endpoints with 15 min of continuous history."""))

# ---------------------------------------------------------------- Conclusions
R.append((f"""  - The mean target of the adaptation nights, which needs no pressure input, was not worse than full fine-tuning in
    {N12} of 24 cells.
  - No pressure-based model showed demonstrable within-subject tracking of temperature or humidity, and the neural
    predictions showed no consistent within-night co-variation with the targets. Where pooled associations appeared,
    they were level alignments between nights or mats.""",
f"""  - The mean target of the adaptation nights, which needs no pressure input, had a point-estimate error no higher than
    full fine-tuning in {N12} of 24 cells ({N7} with the median).
  - No pressure-based model showed demonstrable within-subject tracking of temperature or humidity, and the neural
    predictions showed no consistent within-night co-variation with the targets. User02's night-centred correlations
    after adaptation mostly reflected the level difference between its two mats."""))

R.append(("""- **Consequence:** under the tested 40-s RAW-pressure representation, TCN architecture and fixed training and
  adaptation schedules, pressure-dependent neural prediction did not show a consistent advantage over simple level
  baselines in these three cases. Future work should evaluate other formulations against the same baselines:
  - longer history windows;""",
f"""- **Exploratory addendum:** gradient-boosted models on 5–15-min pressure summaries beat the training mean for
  temperature in {GB_T} of 3 cases, through smaller level offsets and without demonstrated within-night co-variation.
- **Consequence:** under the tested 40-s RAW-pressure representation, TCN architecture and fixed training and
  adaptation schedules, pressure-dependent neural prediction did not show a consistent advantage over simple level
  baselines in these three cases; simpler models with longer histories reduced the offset in some cases but did not
  show tracking. Future work should evaluate other formulations against the same baselines:
  - longer history windows with models and evaluation designed for them;"""))

# ---------------------------------------------------------------- Supplementary, Data availability
R.append(("""Table S34: Additional external validation per night and pre-registered
interpretation.""",
"""Table S34: Additional external validation per night and pre-registered
interpretation; Table S35: Median constants, strict leave-one-subject-out and primary span, exploratory; Table S36:
Point-estimate counts of constants versus networks, exploratory; Table S37: Endpoint availability by history,
exploratory; Table S38: Pressure-summary models: errors, co-variation, night-level intervals and pre-specified reading,
exploratory."""))

R.append(("""The code for data preparation, model training, evaluation and the reproduction of the reported results is maintained
in a version-controlled research repository. The repository is not released publicly at this stage: its committed
history contains recording-date information outside the de-identified release package, and the scope of a public
code release (for example, a de-identified copy) and its license have not yet been decided. [PI DECISION: public code
release scope and license.] Code repository: [CODE REPOSITORY]. Archive DOI: [DOI]. License: [LICENSE].""",
"""The code for data preparation, model training, evaluation and the reproduction of the reported results is maintained
in a version-controlled GitHub repository, which is currently publicly accessible; the data themselves are not part of
it. [PI DECISION: confirm the public code release scope (the committed history contains session-level recording dates
outside the de-identified release package) and the license.] Code repository: [CODE REPOSITORY URL — CONFIRM]. Archive
DOI: [DOI]. License: [LICENSE]."""))

text = t
for old, new in R:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"replacement target found {n} times: {old[:90]!r}")
    text = text.replace(old, new)
write_text(DST, text)
print(f"wrote {DST.relative_to(paths.PROJECT_ROOT)} with {len(R)} replacements")
