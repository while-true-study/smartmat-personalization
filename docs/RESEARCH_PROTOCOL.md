# Research Protocol

Research questions, evaluation principles and leakage-prevention rules.
Concrete split/preprocessing/model settings belong in `docs/EXPERIMENT_PROTOCOL.md`; data rules in
`docs/DATA_POLICY.md`. Any deviation from this document must be recorded in `docs/DECISIONS.md`
**before** the affected experiment is run.

---

## 1. Background

A prior study regressed temperature and relative humidity from multi-channel smart-mat pressure
time series. This study tests whether that result holds under stricter, deployment-like evaluation
and whether short user-specific adaptation helps.

Measured quantities (per raw row): six pressure channels (`P1`–`P6`, 12-bit ADC, 0–4095),
temperature (`temp`, integer °C), relative humidity (`humid`, integer %RH), and a firmware event field
(movement label and heater-control events). The mat is a **heated mat** whose firmware controls a
heater from temperature readings; this matters for leakage (L9) and target definition (OPEN-10).

## 2. Research questions

- **RQ1 — Cross-subject generalization.** How accurately does a model trained on other subjects
  estimate temperature/humidity for an unseen subject (leave-one-subject-out over the frozen
  primary cohort)?
- **RQ2 — Chronological user-adaptive fine-tuning.** Given a subject-independent model, does
  fine-tuning on the target subject's *earliest* data improve accuracy on that subject's *later* data,
  and how does the gain depend on the amount of adaptation data?
- **RQ3 — Feature contribution.** What do movement-derived features and contact-structure features
  each contribute (ablation under the RQ1 and RQ2 protocols)?

Feature-family definitions are pending (EXPERIMENT_PROTOCOL §6). Working meaning:
*movement-derived* = features describing change of pressure over time (shifts, turnovers, activity);
*contact-structure* = features describing the spatial distribution of pressure across channels at a time.

## 3. Evaluation principles

1. **Unit of independence.** Subject first, then recording session. Rows and windows are not
   independent samples. Statistics, confidence intervals and significance tests are computed over
   subjects (and sessions within subject), never over windows.
2. **Pre-specified primary metrics.** MAE and RMSE for each target, reported per subject and as the
   unweighted mean over subjects. Secondary metrics are declared in `EXPERIMENT_PROTOCOL.md` before
   results are seen.
3. **Baselines are mandatory** and evaluated under the identical split: at minimum a training-mean
   predictor and the prior study's approach re-implemented under this protocol.
4. **One look at the test data.** Test folds are evaluated once per frozen protocol version. Iterating
   on test results turns the test set into a validation set; any re-run after a protocol change gets a
   new protocol version in `DECISIONS.md`.
5. **Report everything.** All subjects, all folds, failed and negative results. No subject, night or
   fold is dropped after results are seen.
6. **No outcome-driven adjustment.** Preprocessing, splits, filtering or feature choices are never
   tuned to reproduce or beat the prior study's numbers. Exploratory analyses are labelled as such.
7. **Reproducibility.** Every reported number traces to a run directory holding config, git commit,
   manifest SHA-256, split-file SHA-256, seed and environment (`CONVENTIONS.md` §5).

## 4. Leakage-prevention rules

| ID | Rule |
|---|---|
| L1 | **Split before windowing.** Splits are defined on subjects/sessions/time spans and saved to `data/splits/` *before* any window is generated. Windows are generated inside each partition and never cross a partition boundary. |
| L2 | **No shared recording across partitions.** Data from the same subject, session or log must not appear in both train and test. Because raw files overlap (identical rows in adjacent files) and do not correspond to sessions, grouping is by de-duplicated time span, never by file. |
| L3 | **Fit on training data only.** Scalers, normalisers, imputers, outlier thresholds, feature selectors, PCA, etc. are fitted on the training partition of each fold and only applied to validation/test. |
| L4 | **Held-out subject is untouchable.** It is never used for validation, early stopping, hyperparameter tuning, model/feature selection, threshold choice or normalisation statistics. Validation data come from training subjects only (nested scheme). |
| L5 | **Personalization is chronological.** Adaptation data for a subject strictly precede that subject's test data in time, with a buffer gap between them (length set in EXPERIMENT_PROTOCOL). No shuffling across time. Hyperparameters of adaptation are not tuned on the subject's test span. |
| L6 | **Subject-level exclusion covers all sources.** When a subject is held out, all of its sources, including auxiliary legacy data (e.g. User02 `legacy_csv` when User02 is tested), are excluded from training and validation. |
| L7 | **Duplicated recordings are resolved first.** Data that exist under two subject IDs (OPEN-01: User03 ⊂ User06) or in two files (adjacent-file overlap) are de-duplicated before splitting; the same physical recording never appears twice. |
| L8 | **Concurrent devices are one group.** Simultaneous recordings of one subject on several devices (User02: 22480 and 22482) belong to the same split group and never straddle train/test. |
| L9 | **No target leakage through inputs.** Inputs must not contain the targets or quantities computed from them: temperature/humidity of any device, heater-control events or set-points (AHON/AHOF, BHSDOWN, BCSUP, FOH, STEMP, SLIMIT, …, which the firmware derives from temperature). Firmware movement labels (UM/DM/LM/RM/NM) are derived from pressure only according to the provider's legend and are admissible candidates, pending OPEN-15. |
| L10 | **Calendar leakage is declared.** Date, season or time-of-day inputs can proxy for temperature. They are excluded by default and, if used, are declared and ablated. |
| L11 | **No normalisation using the test subject's statistics** (e.g. per-subject z-scoring with test-span statistics) unless it is part of the declared personalization protocol and uses adaptation-span data only. |
| L12 | **Leakage validation gate.** Before any training run, automated checks verify L1–L11 against the saved split files (disjoint groups, chronological order, scaler-fit provenance, excluded sources). If any check fails, training does not start. The check report is stored with the run. |

## 5. What counts as a protocol change

Any change to cohort, inclusion/exclusion, de-duplication, session definition, split, windowing,
preprocessing, feature set, model family, hyperparameter search space, metric or adaptation budget.
Record it in `DECISIONS.md` (with rationale that does not reference test results) and bump the
protocol version in `EXPERIMENT_PROTOCOL.md`.
