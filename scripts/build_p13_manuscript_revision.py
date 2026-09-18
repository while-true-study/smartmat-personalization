"""Build paper/manuscript/manuscript_p13_revision.md from manuscript_p10_revision.md by exact, checked replacements.

  python scripts/export_p13_tables.py && python scripts/build_p13_manuscript_revision.py \
      && python scripts/render_p13_revision.py && python scripts/validate_p13_revision.py

manuscript.md and manuscript_p10_revision.md are read only. Every replacement target must occur exactly once, so the
revision is auditable and fails if the base changes. Specification: docs/P13_MANUSCRIPT_REVISION_PLAN.md,
docs/P13_MAIN_TEXT_CHANGE_MAP.md and docs/P13_TABLE_FIGURE_PLAN.md. New numbers are source tokens resolved from
paper/tables/p11_*.csv, p12_*.csv and p13_*.csv (scripts/export_p13_tables.py); none is typed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_text  # noqa: E402

SRC = paths.PROJECT_ROOT / "paper" / "manuscript" / "manuscript_p10_revision.md"
DST = paths.PROJECT_ROOT / "paper" / "manuscript" / "manuscript_p13_revision.md"
t = SRC.read_text(encoding="utf-8").replace("\r\n", "\n")

SUBJ = ("User01", "User02", "User07")
GB_T = "{{COUNT:p10_history_interpretation | family=hgb, history_s=900, target=temperature, H_a_beats_training_mean_common=True}}"
TCN_EXCEEDS = "{{COUNT:p11_common_pool_interpretation | target=temperature, exceeds_level_baselines=True}}"
ETA = ".3f"        # eta squared: three decimals (User02 values are below 0.01); MAE and other metrics keep two
S_APPROX_E = "{{COUNT:p8_interpretation_cases | case_I_S_approx_or_better_than_E=True}}"


def v(table, filters, col, spec):
    return "{{" + f"{table} | {filters} | {col} | {spec}" + "}}"


def t10(s, tg, col, spec=".2f"):
    return v("p13_table10_common_endpoints", f"subject_id={s}, target={tg}", col, spec)


def t11(s, col, spec=".2f"):
    return v("p13_table11_heater", f"subject_id={s}", col, spec)


def sv(key, spec=".2f"):
    return v("p13_summary_values", f"key={key}", "value", spec)


def q14(s, tg="temperature"):
    return v("p8_dynamic_summary", f"subject_id={s}, target={tg}, condition=E, budget_nights=14", "Q", ".2f")


def ci(s):
    return f"{t11(s, 'delta_mae', '+.2f')} °C [{t11(s, 'ci_lower', '+.2f')}, {t11(s, 'ci_upper', '+.2f')}]"


def boot12(s, tg, col):
    return v("p12_heater_bootstrap_common", f"subject_id={s}, target={tg}, first=source_mean, "
                                             f"second=heater_conditioned_source_mean", col, "+.2f")


R = []

# ---------------------------------------------------------------- header comment
R.append(("""<!--
P10 REVISION (D-064): a revised copy of paper/manuscript/manuscript.md, which is kept unchanged. Changes are listed in
paper/manuscript/REVISION_P10_NOTES.md. New numbers are tokens resolved from paper/tables/p10_*.csv.""",
"""<!--
P13 REVISION: a revised copy of paper/manuscript/manuscript_p10_revision.md, built by
scripts/build_p13_manuscript_revision.py; manuscript.md and manuscript_p10_revision.md are kept unchanged. Changes are
listed in paper/manuscript/REVISION_P13_NOTES.md. New numbers are tokens resolved from paper/tables/p11_*.csv,
p12_*.csv and p13_*.csv (scripts/export_p13_tables.py). Figure 6 and Figure S5 are drawn by
scripts/render_p13_figures.py into paper/manuscript/revision_p13/figures/; Tables S35-S44 are in
paper/manuscript/revision_p13/supplementary/. Render: scripts/render_p13_revision.py; checks:
scripts/validate_p13_revision.py.
P10 REVISION (D-064): a revised copy of paper/manuscript/manuscript.md, which is kept unchanged. Changes are listed in
paper/manuscript/REVISION_P10_NOTES.md. New numbers are tokens resolved from paper/tables/p10_*.csv."""))

# ---------------------------------------------------------------- Abstract
R.append(("""Smart-mat pressure could yield bed-microclimate temperature and humidity estimates without extra sensors, but
deployed models face unseen users, periods and mats. We evaluated temporal convolutional networks on 40-s pressure
windows from three subjects (four mat streams) under strict leave-one-subject-out evaluation, each held-out subject being
an unseen domain of subject, period and mat, and fine-tuned them on each subject's earliest 1–14 nights with a fixed
later test span. Errors were dominated by level offsets; for temperature, the network did not beat a training-mean
predictor. Fine-tuning moved one subject's temperature bias from
{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_0 | +.2f}} to
{{p5_adaptation_gain | subject_id=User02, target=temperature, budget_nights=14 | bias_b | +.2f}} °C after 14 nights,
whereas another subject's error rose at every budget. In post-hoc comparisons, the adaptation-night target mean, which
uses no pressure input, had a point-estimate error no higher than fine-tuning in {{COUNT:p8_interpretation_cases | case_A_B_le_E=True}} of 24 subject–target–budget
cells ({{p10_point_counts | setting=rq2_primary_span, comparison=B_med MAE <= E (fine-tuning) seed-mean MAE | count | d}} with the median). No consistent within-night co-variation was found; one subject's positive night-centred
correlations after adaptation largely disappeared when centred within night and mat. In an exploratory analysis,
gradient-boosted models on 5–15-min pressure summaries beat the training mean for temperature in {{COUNT:p10_history_interpretation | family=hgb, history_s=900, target=temperature, H_a_beats_training_mean_common=True}} of 3
subjects, through smaller offsets rather than within-night tracking. The findings are limited to three retrospective
cases.""",
f"""Smart-mat pressure could yield bed-microclimate temperature and humidity estimates without extra sensors, but
deployed models face unseen users, periods and mats. We evaluated temporal convolutional networks on 40-s pressure
windows from three subjects (four mat streams) under strict leave-one-subject-out evaluation, each held-out subject being
an unseen domain of subject, period and mat, and fine-tuned them on each subject's earliest 1–14 nights with a fixed
later test span. Errors were dominated by level offsets; for temperature, the network did not beat a training-mean
predictor for any held-out subject. Personalization gave mixed results: a large offset correction in one subject and
degradation in another. A personalized constant was a strong competitor, the adapted predictions were strongly
compressed toward level-dominated behaviour, and no consistent within-night co-variation was found. In exploratory
analyses on endpoints with 15 min of continuous history, gradient-boosted models on 5–15-min pressure summaries
reduced temperature error in {GB_T} of 3 subjects, and a network retrained on the same endpoints did not change the
primary conclusion. Heater-control context was associated with temperature in the same two subjects, so the
longer-history gain cannot be attributed specifically to pressure. The findings are limited to three retrospective
cases."""))

R.append(("""<!-- One paragraph, about 200 words at most once the tokens are rendered (requirements item 3): problem, strict
design, adaptation design, primary evidence, post-hoc comparators, dynamic-signal diagnostic, scoped interpretation and
limit. Every number is a source token.""",
"""<!-- One paragraph, 190-200 words once the tokens are rendered (checked by scripts/validate_p13_revision.py): problem,
strict design, adaptation design, primary evidence, mixed personalization, the exploratory longer-history result with
the retrained network, the heater competing explanation, and limit. Counts over cells, seeds and audit detail are left
to the body. Every number is a source token."""))

# ---------------------------------------------------------------- Introduction
R.append(("""targets (Section 3.5.6). After an internal review of a draft, an exploratory addendum checked whether these readings
depend on the choice of constant (mean or median) and whether simple pressure-summary models with histories of up to
15 min beat the level baseline under strict leave-one-subject-out evaluation (Section 3.5.8). The question that these""",
"""targets (Section 3.5.6). Exploratory analyses then checked whether these readings depend on the choice of constant
(mean or median) and whether simple pressure-summary models with histories of up to 15 min beat the level baseline
under strict leave-one-subject-out evaluation; the network was retrained on the same endpoints, and heater-control
context was examined as a competing explanation (Sections 3.5.8–3.5.9). The question that these"""))

R.append(("""3. A post-hoc comparator analysis showing that the personalization gains were mainly level corrections: a
   personalized constant (the adaptation-night target mean) had a point-estimate error no higher than full
   fine-tuning in {{COUNT:p8_interpretation_cases | case_A_B_le_E=True}} of 24 cells ({{p10_point_counts | setting=rq2_primary_span, comparison=B_med MAE <= E (fine-tuning) seed-mean MAE | count | d}} with the adaptation-night median), the pressure-based models showed no
   demonstrable within-subject tracking of the targets, and cross-subject pretraining added little over training on
   the adaptation nights alone. A final diagnostic""",
"""3. A post-hoc comparator analysis showing that the personalization gains were mainly level corrections: a
   personalized constant (the adaptation-night target mean) was a strong competitor to full fine-tuning, the adapted
   predictions were strongly compressed toward level-dominated behaviour, the pressure-based models showed no
   demonstrable within-subject tracking of the targets, and cross-subject pretraining did not provide consistent
   additional predictive value over target-only training under the tested fixed adaptation protocol. A final
   diagnostic"""))

R.append(("""4. An exploratory scope check with median constants and with ridge and gradient-boosted models on 40-s, 5-min and
   15-min pressure summaries. It narrows the negative result: a gradient-boosted model beat the training mean for
   temperature in {{COUNT:p10_history_interpretation | family=hgb, history_s=900, target=temperature, H_a_beats_training_mean_common=True}} of 3 held-out subjects, on endpoints with 15 min of continuous history, through a smaller
   offset and without within-night co-variation.""",
f"""4. An exploratory scope check with median constants and with ridge and gradient-boosted models on 40-s, 5-min and
   15-min pressure summaries, on endpoints with 15 min of continuous history. It narrows the negative result: a
   gradient-boosted model reduced the temperature error relative to the training mean in {GB_T} of 3 held-out
   subjects, through a smaller offset and without within-night co-variation; the network retrained on the same
   endpoints left the primary conclusion unchanged; and heater-control context, which was associated with
   temperature in the same two subjects, remains a competing explanation that cannot be separated from pressure
   history."""))

# ---------------------------------------------------------------- Methods
R.append(("""firmware control, which writes control codes into the logs. These codes are excluded from the model inputs under the
leakage policy (Section 3.5.4), so the heater and controller state remains an unobserved determinant of the
microclimate for every model in this study. The temperature–humidity""",
"""firmware control, which writes control codes into the logs. These codes are excluded from the model inputs under the
leakage policy (Section 3.5.4), so no model in this study observes the heater and controller state. The heater on/off
codes were used only after the fact, as a descriptive stratifier (Section 3.5.9 and Section 3.6). The
temperature–humidity"""))

R.append(("""These analyses were added after the primary results and a draft of this article were known, to test simpler""",
"""These analyses were added after the primary results were known, to test simpler"""))

R.append(("""#### 3.5.8. Exploratory Addendum: Median Constants and Pressure-Summary Histories (Post Hoc)

After an internal review of a draft, a fourth protocol addendum was written, with all results above known and before
any of its metrics was computed. It is exploratory and replaces no result above.""",
"""#### 3.5.8. Exploratory Analysis: Median Constants and Pressure-Summary Histories (Post Hoc)

A fourth protocol addendum was written with all results above known and before any of its metrics was computed. It is
exploratory and replaces no result above."""))

R.append(("""- **Common endpoints:** training, selection and evaluation used only endpoints with all three histories available; the
  RAW-TCN (trained on all 40-s windows) and the constants were re-evaluated on the same endpoints.""",
"""- **Common endpoints:** training, selection and evaluation used only endpoints with all three histories available; the
  constants were recomputed on the common training endpoints.
- **RAW-TCN on the common endpoints (training-pool control):** so that every learned model shares one training pool,
  the RAW-TCN was retrained on the common training endpoints. Its input remained the original 40-s window; it is not
  a 900-s network, and only the source training endpoints were restricted to the set with 900 s of continuous history.
  The architecture and hyperparameters selected in Section 3.5.1 were kept; only the number of epochs was re-derived,
  with the unchanged inner rule of Section 3.5.1 on the common inner splits, and the target scaler was fitted on the
  common training endpoints of the two source subjects. Seeds 0, 1 and 2 were trained. The held-out subject was used
  neither for the epoch selection nor for any scaler. The network trained on all 40-s windows is reported as a
  training-pool sensitivity reference (Table S38)."""))

R.append(("""  if the interval of MAE(40 s) − MAE(longer history) lies above zero. None of these readings implies a thermal time
  constant.

### 3.6. Metrics and Statistical Analysis""",
"""  if the interval of MAE(40 s) − MAE(longer history) lies above zero. The retraining of the network and the same
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

### 3.6. Metrics and Statistical Analysis"""))

R.append(("""  - User02 strata by mat, quality phase and heater context. Heater context is the most recent heater on/off code on
    the same mat within 60 min before the target time, used for stratification only;""",
"""  - User02 strata by mat, quality phase and heater context. Heater context is the most recent heater on/off code on
    the same mat within 60 min before the target time, used for stratification only; the heater-context diagnostic of
    Section 3.5.9 applies the same definition to all three subjects;"""))

R.append(("""  - the exploratory addendum of Section 3.5.8.""",
"""  - the exploratory analysis of Section 3.5.8 and the heater-context diagnostic of Section 3.5.9."""))

R.append(("""  - the heater codes used for stratification;""",
"""  - User02's heater codes, used for stratification;"""))

R.append(("""- **Exploratory addendum (Section 3.5.8):** rerun into a separate output directory; every table and every prediction
  file was identical. It used scikit-learn 1.8.0 in addition.""",
"""- **Exploratory analyses (Sections 3.5.8–3.5.9):** they use the canonical dataset, not the release package.
  - The pressure-summary analysis was rerun into a separate output directory, and every table and every prediction
    file was identical; it used scikit-learn 1.8.0 in addition.
  - The network retrained on the common endpoints was trained in one recorded execution, with fixed seeds 0, 1 and 2,
    the frozen configuration and the pre-specified epoch rule; this execution was not repeated.
  - The heater-context diagnostic was run twice into separate output directories, with identical tables. It needs the
    heater codes of all three subjects, which the release candidate does not contain, so it cannot be reproduced from
    the release package alone."""))

# ---------------------------------------------------------------- Results: feature families
R.append(("""- **Movement → temperature:** movement information helped temperature.
  - MOVEMENT changed the unweighted temperature MAE by
    `{{p4_vs_raw | family=MOVEMENT, target=temperature, metric=mae | delta_unweighted_mean | +.2f}}` °C relative to
    RAW, improving `{{p4_vs_raw | family=MOVEMENT, target=temperature, metric=mae | improved_subjects | d}}` of three
    subjects.""",
"""- **MOVEMENT, temperature:** movement-derived features reduced the temperature MAE relative to RAW in
  `{{p4_vs_raw | family=MOVEMENT, target=temperature, metric=mae | improved_subjects | d}}` of three held-out subjects,
  although the unweighted mean remained close to the training-mean baseline (see below).
  - MOVEMENT changed the unweighted temperature MAE by
    `{{p4_vs_raw | family=MOVEMENT, target=temperature, metric=mae | delta_unweighted_mean | +.2f}}` °C relative to
    RAW."""))

R.append(("""- **Contact → humidity:** RAW+CONTACT changed the unweighted humidity MAE by""",
"""- **RAW+CONTACT, humidity:** RAW+CONTACT changed the unweighted humidity MAE by"""))

# ---------------------------------------------------------------- Results: device residual
R.append(("""  evidence of a sensor defect or a heater effect. Heater and controller state, excluded from the inputs, is an
  unobserved contextual factor that may contribute to the microclimate variation the pressure input does not carry.""",
"""  evidence of a sensor defect or a heater effect. Heater context across the three subjects is described in
  Section 4.11."""))

# ---------------------------------------------------------------- Results: post-hoc comparators (pretraining)
R.append(("""- **Pretraining added little (b = 14; Table 7).**""",
"""- **Pretraining added no consistent value (b = 14; Table 7).**"""))

R.append(("""  - S was better than the adaptation-target mean in
    `{{COUNT:p8_interpretation_cases | case_F_S_better_than_B=True}}` of six cells, the same cells in which E was.""",
"""  - S was better than the adaptation-target mean in
    `{{COUNT:p8_interpretation_cases | case_F_S_better_than_B=True}}` of six cells, the same cells in which E was.
  - Cross-subject pretraining therefore did not provide consistent additional predictive value over target-only
    training under the tested fixed adaptation protocol."""))

# ---------------------------------------------------------------- Results: dynamic-signal diagnostic (compression)
R.append(("""- **After adaptation, User02: mostly the two mats' level difference.**""",
f"""- **After adaptation: compressed prediction dynamics.** At b = 14 the prediction standard deviation of full
  fine-tuning was `{q14('User02')}` times the target standard deviation for User02 temperature and `{q14('User07')}`
  times for User07 temperature (Q in Table 8). Prediction dynamics were strongly compressed toward level-dominated
  behaviour.
- **After adaptation, User02: mostly the two mats' level difference.**"""))

# ---------------------------------------------------------------- Results: 4.10 (Table 10) and new 4.11 (Table 11)
old_410_start = "### 4.10. Exploratory Addendum: Median Constants and Pressure-Summary Histories (Post Hoc)"
old_410_end = """- The RAW-TCN and the summary models differ in representation, model family and training pool, so their difference is
  not attributed to history length or read as overfitting."""
i0, i1 = t.index(old_410_start), t.index(old_410_end) + len(old_410_end)
if t.count(old_410_start) != 1 or t.count(old_410_end) != 1:
    raise SystemExit("Section 4.10 boundaries are not unique")
old_410 = t[i0:i1]


def row10(s, tg):
    tcn = (f"{t10(s, tg, 'mae_tcn_common')} ({t10(s, tg, 'mae_tcn_common_seed_min')}–"
           f"{t10(s, tg, 'mae_tcn_common_seed_max')}){t10(s, tg, 'mark_tcn_common', 's')}")
    cells = [s, tg, f"{t10(s, tg, 'n_windows', ',d')} / {t10(s, tg, 'n_nights', 'd')}",
             t10(s, tg, "mae_source_mean"), t10(s, tg, "mae_source_median"), tcn,
             *[f"{t10(s, tg, f'mae_hgb_{h}')}{t10(s, tg, f'mark_hgb_{h}', 's')}" for h in ("40", "300", "900")]]
    return "| " + " | ".join(cells) + " |"


table10 = "\n".join(
    ["| Subject | Target | Common endpoints (windows / nights) | Source mean | Source median | "
     "RAW-TCN 40 s, common pool | Boosting 40 s | Boosting 300 s | Boosting 900 s |",
     "|" + "---|" * 9] + [row10(s, tg) for tg in ("temperature", "humidity") for s in SUBJ])


def row11(s, share_spec):
    cells = [s, f"{t11(s, 'on_windows_full', ',d')} ({t11(s, 'on_share_pct_full', share_spec)} %)",
             t11(s, "eta_raw_full", ETA), t11(s, "eta_night_centred_full", ETA), t11(s, "mae_source_mean_common"),
             t11(s, "mae_source_median_common"), t11(s, "mae_heater_conditioned_common"),
             f"{t11(s, 'delta_mae', '+.2f')} [{t11(s, 'ci_lower', '+.2f')}, {t11(s, 'ci_upper', '+.2f')}]",
             t11(s, "mae_hgb_900_common")]
    return "| " + " | ".join(cells) + " |"


table11 = "\n".join(
    ["| Subject | Heater-on windows (share) | η² raw | η² within night | Source mean | Source median | "
     "Heater-conditioned source constant | ΔMAE [95 % interval] | Boosting 900 s |",
     "|" + "---|" * 9, row11("User01", ".1f"), row11("User02", ".2f"), row11("User07", ".1f")])

full = lambda s, tg: t10(s, tg, "mae_tcn_full")  # noqa: E731
new_410 = f"""### 4.10. Exploratory Analysis: Median Constants, Pressure-Summary Histories and a Matched Training Pool (Post Hoc)

The held-out subjects differ strongly in their target levels, and User02's two mats differ from each other (Figure 6).
The comparisons below are made against this domain-level structure.

{{{{FIGURE:figure6_target_distributions}}}}

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

{table10}

Training-pool sensitivity (Table S38): the RAW-TCN trained on all labelled 40-s windows, evaluated on the same
endpoints, had a temperature MAE of {full('User01', 'temperature')}, {full('User02', 'temperature')} and
{full('User07', 'temperature')} °C and a humidity MAE of {full('User01', 'humidity')}, {full('User02', 'humidity')} and
{full('User07', 'humidity')} %RH (User01, User02, User07).

- **Endpoints:** a 900-s history needs 15 min without a recording gap longer than 5 s, so about half of the labelled
  endpoints qualified (Table S37); the comparisons below are on that subset.
- **Temperature, summary models:** gradient boosting with 300-s or 900-s histories had a lower MAE than the
  source-training mean in {GB_T} of 3 subjects (User01 and User07; night-level intervals above zero) and not for
  User02, where every pressure model was worse than the constant; ridge regression did so in none (Table S38). The
  gains came with a smaller offset, R stayed above 1, and the night-centred correlations were near zero or negative.
  For User07 the source-training median had a lower MAE than the boosted models.
- **Temperature, retrained RAW-TCN:** its MAE was {t10('User01', 'temperature', 'mae_tcn_common')},
  {t10('User02', 'temperature', 'mae_tcn_common')} and {t10('User07', 'temperature', 'mae_tcn_common')} °C (User01,
  User02, User07). Under the pre-specified reading it exceeded both constants for {TCN_EXCEEDS} of 3 subjects. For
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
  {sv('tcn_common_vs_hgb_40_temperature_absdiff_min')} to {sv('tcn_common_vs_hgb_40_temperature_absdiff_max')} °C,
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
composition of the source subjects. User02 had heater-on context in only {t11('User02', 'on_windows_full', ',d')}
windows, so inference about its heater-on state is very limited; its η² after centring within night and mat was
{t11('User02', 'eta_night_x_mat_centred_full', ETA)}.

{table11}

- **Association:** for User01 and User07, heater context was associated with temperature, and the association
  remained after centring within night (η² {t11('User01', 'eta_raw_full', ETA)} raw and
  {t11('User01', 'eta_night_centred_full', ETA)} within night for User01; {t11('User07', 'eta_raw_full', ETA)} and
  {t11('User07', 'eta_night_centred_full', ETA)} for User07). For User02 it was negligible
  ({t11('User02', 'eta_raw_full', ETA)}, {t11('User02', 'eta_night_centred_full', ETA)} and
  {t11('User02', 'eta_night_x_mat_centred_full', ETA)} within night and mat), but with
  {t11('User02', 'on_windows_full', ',d')} heater-on windows its heater-on state is essentially unobserved.
- **Direction:** windows after a heater-on code were colder than the other windows: their mean temperature minus that
  of the other windows was {sv('User01_temperature_on_minus_other_mean_full', '+.2f')} °C for User01 and
  {sv('User07_temperature_on_minus_other_mean_full', '+.2f')} °C for User07 (all nights; Table S42). This is the
  direction expected from a controller that switches the heater on after the temperature has fallen (Section 5.3).
- **Heater-conditioned source constant:** on the common endpoints it had a lower temperature MAE than the source mean
  for User01 ({t11('User01', 'mae_source_mean_common')} → {t11('User01', 'mae_heater_conditioned_common')} °C; ΔMAE
  {ci('User01')}) and User07 ({t11('User07', 'mae_source_mean_common')} →
  {t11('User07', 'mae_heater_conditioned_common')} °C; ΔMAE {ci('User07')}), close to boosting at 900 s
  ({t11('User01', 'mae_hgb_900_common')} and {t11('User07', 'mae_hgb_900_common')} °C); for User07 the source median
  ({t11('User07', 'mae_source_median_common')} °C) was lower still. For User02 it was slightly worse
  ({t11('User02', 'mae_source_mean_common')} → {t11('User02', 'mae_heater_conditioned_common')} °C; ΔMAE
  {ci('User02')}).
- **Not a heater effect:** the source pools differed in heater-context coverage between subjects. In the fold holding
  out User01, almost all source heater-on windows came from User07, and in the fold holding out User07 almost all came
  from User01 (Tables S41 and S44). The conditioned constant therefore also transfers the level of one source subject,
  and heater context and subject identity cannot be separated. For User01 humidity, η² was small
  ({v('p12_heater_eta_squared', 'span=full, subject_id=User01, target=humidity, variant=A2_night_centred, scope=three_states', 'eta_squared', ETA)}
  within night), yet the conditioned constant lowered the MAE by {boot12('User01', 'humidity', 'point_estimate')} %RH
  [{boot12('User01', 'humidity', 'ci_lower')}, {boot12('User01', 'humidity', 'ci_upper')}], an example of this
  composition effect (Table S44).
- **Humidity:** η² was at most {sv('eta_humidity_full_three_states_max', ETA)} for every subject and centring (Table S43)."""
R.append((old_410, new_410))

# ---------------------------------------------------------------- Discussion 5.1
R.append(("""  A constant computed from the same adaptation labels, with no pressure input, often did nearly as well or better: its
  point-estimate error was no higher than that of full fine-tuning in {{COUNT:p8_interpretation_cases | case_A_B_le_E=True}} of 24 cells with the mean and {{p10_point_counts | setting=rq2_primary_span, comparison=B_med MAE <= E (fine-tuning) seed-mean MAE | count | d}} with the
  median, including the study's largest correction (User02 temperature) with the mean at every budget.
- **No demonstrable tracking.** The unadapted network's errors varied more than the targets themselves, and after
  fine-tuning the error spread was about that of a constant (Table 6).""",
f"""  A constant computed from the same adaptation labels, with no pressure input, often did nearly as well or better
  (Section 4.7), including the study's largest correction (User02 temperature) with the mean at every budget.
- **Compressed dynamics, no demonstrable tracking.** The unadapted network's errors varied more than the targets
  themselves. After fine-tuning, the variation of the predictions was strongly compressed: at b = 14 the prediction
  standard deviation was `{q14('User02')}` times the target standard deviation for User02 temperature and
  `{q14('User07')}` times for User07 temperature (Table 8), and the error spread was about that of a constant
  (Table 6). A network trained from scratch on the same adaptation nights was not worse than the pretrained model in
  {S_APPROX_E} of six subject–target cells at b = 14, and a constant computed from the adaptation labels explained much
  of the gain (Section 4.7). Prediction dynamics were therefore strongly compressed toward level-dominated behaviour,
  and cross-subject pretraining did not provide consistent additional predictive value over target-only training
  under the tested fixed adaptation protocol."""))

R.append(("""- **Limited value of pretraining.** A randomly initialised network of the same architecture, trained on the
  adaptation nights with the same recipe, reached the error of the pretrained fine-tuning in most cells.
""", ""))

R.append(("""  adaptation schedules, we found no consistent evidence of superiority over simple level baselines.""",
"""  adaptation schedules, we found no consistent evidence of superiority over simple level baselines, also when the
  network was retrained on the endpoints used by the summary models (Section 4.10)."""))

R.append(("""- **Scope of the negative result (exploratory addendum, Section 4.10).** It does not extend to every pressure model: a
  gradient-boosted model on 5–15-min pressure summaries had a lower temperature error than the training mean in
  {{COUNT:p10_history_interpretation | family=hgb, history_s=900, target=temperature, H_a_beats_training_mean_common=True}} of 3 subjects. That advantage was a smaller level offset on the held-out subject, without within-night
  co-variation, on endpoints with 15 min of continuous history, and it depended on the mean being the reference
  constant for one subject. It narrows, but does not reverse, the reading that simple level information explains most
  of what the pressure models achieved.""",
"""- **Scope of the negative result.** It concerns the tested 40-s formulation. Summary models with longer pressure
  histories had a lower temperature error than the training mean for two subjects; what this does and does not show
  is discussed in Section 5.3."""))

# ---------------------------------------------------------------- Discussion 5.3
R.append(("""  These factors were unobserved here, and the heater state was excluded from the inputs by design (Section 3.1).""",
"""  None of them was a model input; the heater codes were excluded from the inputs by design (Section 3.1) and used
  only descriptively (Section 4.11)."""))

R.append(("""- **A plausible limitation (not a demonstrated mechanism): temporal-scale mismatch.**
  - The 40-s pressure window captures short-term contact and movement.
  - The mat microclimate may also depend on longer occupancy history, accumulated thermal conditions, heater and
    controller state, ventilation and other contextual variables unavailable to the model.
  - This study does not test the explanation. In the exploratory addendum, longer pressure histories were associated
    with a lower temperature error of simple summary models, mostly through smaller offsets. This is consistent with,
    but does not demonstrate, a role of longer context, and it is not evidence of a thermal time constant.""",
f"""- **Longer histories and heater context.**
  - In the exploratory analysis on endpoints with 15 min of continuous history, gradient-boosted models on 300-s and
    900-s pressure summaries had a lower temperature error than the source-training mean for User01 and User07
    (Section 4.10).
  - Retraining the 40-s network on the same endpoints showed that this pattern was not caused solely by the original
    network having been trained on a larger pool: the retrained network still did not consistently exceed the level
    baselines for temperature, and its error was close to that of the 40-s boosted model.
  - However, heater and controller context remained associated with temperature for User01 and User07 after centring
    within night (Section 4.11).
  - For User01, a source constant conditioned on heater context reached a temperature MAE of
    {t11('User01', 'mae_heater_conditioned_common')} °C, close to the {t11('User01', 'mae_hgb_900_common')} °C of
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
  which is why it is excluded from the model inputs and used here only descriptively."""))

R.append(("""  - Longer history windows were tested only with simple summary models (Section 4.10). State-space or long-context""",
"""  - Longer history windows were tested only with simple summary models; the retrained network kept the 40-s input
    (Section 4.10). State-space or long-context"""))

# ---------------------------------------------------------------- Discussion 5.5 and 5.7
R.append(("""  - a personalized constant had a point-estimate error no higher than full fine-tuning in {{COUNT:p8_interpretation_cases | case_A_B_le_E=True}} of 24 cells ({{p10_point_counts | setting=rq2_primary_span, comparison=B_med MAE <= E (fine-tuning) seed-mean MAE | count | d}}
    with the median), and no pressure-based model showed demonstrable within-subject tracking (Sections 4.7 and 4.10);
  - cross-subject pretraining gave limited benefit over the scratch initialization control (Section 4.7).""",
"""  - a personalized constant was a strong competitor to full fine-tuning, and no pressure-based model showed
    demonstrable within-subject tracking (Section 4.7 and Section 4.10);
  - the RAW-TCN retrained on the endpoints of the summary models still did not consistently outperform the level
    baselines for temperature (Section 4.10);
  - cross-subject pretraining did not provide consistent additional predictive value over the scratch initialization
    control (Section 4.7)."""))

R.append(("""microclimate and its heater history. The heater and controller state, excluded from the inputs, remains an unobserved
contextual factor. We do not attribute the residual to a device defect, to the heater or to a property of the user.""",
"""microclimate and its heater history, and User02 had almost no heater-on context (Section 4.11). We do not attribute
the residual to a device defect, to the heater or to a property of the user."""))

# ---------------------------------------------------------------- Limitations
R.append(("""  - They were designed after the primary results and a draft of this article were known. Their design was fixed""",
"""  - They were designed after the primary results were known. Their design was fixed"""))

R.append(("""  and fixed training and adaptation schedules. The negative result is scoped to this formulation. Room climate,
  bedding and the heater and controller state were unobserved; the heater codes were excluded from the inputs under
  the leakage policy.""",
"""  and fixed training and adaptation schedules. The negative result is scoped to this formulation. Room climate,
  bedding and occupancy context were not measured; the heater codes were excluded from the inputs under the leakage
  policy and used only descriptively."""))

R.append(("""- **Exploratory addendum:** designed with all other results known; one tree family with small grids; evaluated on the
  roughly half of the endpoints with 15 min of continuous history.""",
"""- **Exploratory analyses (Sections 3.5.8–3.5.9):** designed with all other results known; one tree family with small
  grids; evaluated on the roughly half of the endpoints with 15 min of continuous history, which may favour long,
  stable recordings. The retrained network kept the configuration selected on the full pool, and its re-derived epoch
  count changed with the pool, so the effect of the pool includes that of the epoch count.
- **Heater diagnostic:** observational and post hoc. Only heater on/off codes define the context; the meaning of
  several other heater-related codes (for example the code FOF) is known only from their names, so windows without
  a context can still follow heater actions. The controller state is potentially endogenous to the target. The source
  pools differ in heater-context composition between subjects, so the heater-conditioned constant mixes heater
  context with subject identity, and User02 has almost no heater-on windows. Ambient climate was not measured
  independently, and the heater was never manipulated. The mechanisms behind the longer-history gain therefore cannot
  be separated."""))

R.append(("""  selections (Section 3.7). The post-hoc analyses were reproduced from the frozen models, not from the release
  package.""",
"""  selections (Section 3.7). The post-hoc analyses were reproduced from the frozen models, not from the release
  package, and the heater-context diagnostic cannot be reproduced from the release package (Section 3.7)."""))

# ---------------------------------------------------------------- Conclusions
R.append(("""  - The mean target of the adaptation nights, which needs no pressure input, had a point-estimate error no higher than
    full fine-tuning in {{COUNT:p8_interpretation_cases | case_A_B_le_E=True}} of 24 cells ({{p10_point_counts | setting=rq2_primary_span, comparison=B_med MAE <= E (fine-tuning) seed-mean MAE | count | d}} with the median).""",
"""  - The mean target of the adaptation nights, which needs no pressure input, was a strong competitor to full
    fine-tuning, and the adapted networks' prediction dynamics were strongly compressed toward level-dominated
    behaviour."""))

R.append(("""  - Cross-subject pretraining added little over training on the adaptation nights alone.""",
"""  - Cross-subject pretraining did not provide consistent additional predictive value over target-only training under
    the tested fixed adaptation protocol."""))

R.append(("""- **Exploratory addendum:** gradient-boosted models on 5–15-min pressure summaries beat the training mean for
  temperature in {{COUNT:p10_history_interpretation | family=hgb, history_s=900, target=temperature, H_a_beats_training_mean_common=True}} of 3 cases, through smaller level offsets and without demonstrated within-night co-variation.""",
f"""- **Longer histories (exploratory):** gradient-boosted models on 5–15-min pressure summaries reduced the temperature
  error in {GB_T} of 3 cases, through smaller level offsets and without demonstrated within-night co-variation.
  Retraining the 40-s network on the same endpoints did not overturn the primary finding. The longer-history gains
  cannot be uniquely attributed to pressure-specific thermal dynamics, because controller, heater and environmental
  mechanisms remain entangled with them in these observational data. The results do not demonstrate an absence of
  useful pressure information."""))

R.append(("""  - contextual inputs that do not leak the target;""",
"""  - contextual measurements that do not derive from the target, such as independently logged heater operation and
    ambient climate, with a documented sensor placement;"""))

R.append(("""  - larger cohorts.
  This should happen""",
"""  - larger multi-user and multi-device cohorts.
  This should happen"""))

# ---------------------------------------------------------------- Supplementary list and Data availability
R.append(("""the adaptation budget b: (a) temperature, (b) humidity; Table S1:""",
"""the adaptation budget b: (a) temperature, (b) humidity; Figure S5: One example night per held-out subject, selected by
a fixed rule, with total pressure, temperature, humidity and heater on/off codes over relative time; Table S1:"""))

R.append(("""exploratory; Table S38: Pressure-summary models: errors, co-variation, night-level intervals and pre-specified reading,
exploratory.""",
"""exploratory; Table S38: Pressure-summary models: errors, co-variation, night-level intervals and pre-specified reading,
with the RAW-TCN trained on all 40-s windows as a training-pool sensitivity reference, exploratory; Table S39: RAW-TCN
retrained on the common endpoints: per seed, epoch selection and pool counts, exploratory; Table S40: RAW-TCN retrained
on the common endpoints: night-level intervals and pre-specified reading, exploratory; Table S41: Heater-control code
audit and heater-context coverage, post hoc; Table S42: Target level by heater context, post hoc; Table S43: Eta squared
of heater context for both targets and all centrings, post hoc; Table S44: Heater-conditioned source constant, its
night-level intervals and source composition, and errors by heater context, post hoc."""))

R.append(("""hyperparameter searches were not rerun (Section 3.7). The reconstructed rows of the additional external subject
(Section 3.5.7) are not part of the release candidate.""",
"""hyperparameter searches were not rerun (Section 3.7). The reconstructed rows of the additional external subject
(Section 3.5.7) are not part of the release candidate. The exploratory analyses of Sections 3.5.8–3.5.9 use the
canonical dataset; the heater-context diagnostic needs heater codes that the release candidate contains for one
subject only."""))

text = t
for old, new in R:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"replacement target found {n} times: {old[:90]!r}")
    text = text.replace(old, new)
write_text(DST, text)
print(f"wrote {DST.relative_to(paths.PROJECT_ROOT)} with {len(R)} replacements")
