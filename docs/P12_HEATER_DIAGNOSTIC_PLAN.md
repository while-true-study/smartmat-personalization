# P12 — Heater-context confound diagnostic: plan (protocol v1.6 addendum, D-067)

> **Status: post-hoc descriptive confound diagnostic. Written before any P12 statistic was computed.**
> - Requested by the research lead on 2026-09-18 as a new phase outside the D-059/D-060/D-065/D-066 stop rules.
> - **Results already seen:** every P3–P11 result, the P6 User02 heater-context strata and the P1 event-conditioned
>   trajectories. P12 is not confirmatory and is never described as originally planned.
> - Machine-readable parameters: `configs/experiments/v1.6/p12_heater_diagnostic.yaml`. The SHA-256 of this plan and of
>   that config is written to `outputs/p12_heater_diagnostic/pre_result_design_hashes.json` before the first statistic
>   and must equal the values in the final `provenance.json`. Neither file is edited after the first P12 computation.
> - Nothing in v1.0–v1.5 is edited. P12 writes only under `outputs/p12_heater_diagnostic/` and its own documents.
>   Audit: `docs/P12_HEATER_DIAGNOSTIC_AUDIT.md`. **Local only: no push before a PI / public-release decision.**

## 1. Purpose and non-purpose

P12 is **not** a predictive-model phase. It asks two descriptive questions:

1. How strongly is heater/controller context associated with the recorded temperature and humidity **level**?
2. Is heater/controller context a plausible competing explanation for the lower error of the 300-s and 900-s
   pressure-summary models in P10?

No heater or control field is added to the RAW-TCN, histogram boosting, Ridge or any other pressure model. No neural
model and no new model family is fitted. RQ1, RQ2 and RQ3 are unchanged.

## 2. Heater context (frozen; D-047 A.2, reused unchanged)

The most recent `AHON` or `AHOF` code on the **same mat** with event time ≤ the window's target time and within
**3,600 s**; otherwise no context. Implementation: `p6_robustness.heater_events` and `heater_context`. Event tables
are built per subject (User01 and User07 share `device_id = "unknown"`). Labels: `ON` (last code AHON), `OFF` (last
code AHOF), `UNKNOWN`. `ON`/`OFF` describe the last code, not a reconstructed heater state. The look-back is not cut
at session boundaries (as in D-047); affected windows are counted. No other control code is added or reinterpreted,
and the definition is not changed after results are seen.

New relative to D-047: the same definition is applied to User01 and User07 and to the strict-LOSO test span.

## 3. Diagnostic-only exception

D-038 forbids heater/control fields as model inputs and keeps them for stratification. Analysis A is stratification.
Analysis B predicts held-out windows from their heater context and is therefore **outside** D-038; it runs only under
the D-067 *post-hoc diagnostic-only exception*. Because the control codes are derived from temperature (L9; P1 §9), the
heater-conditioned constant uses target-derived information: it is a diagnostic comparator, never an estimator, and its
error is never reported as achievable performance.

## 4. Analysis A — association of heater context with the target

Windows: the frozen labelled 40-s windows of each subject. Spans, reported separately: **full** (all labelled windows of
the subject = its strict-LOSO test span) and **common** (the P10/P11 common endpoints).

Per subject × target × state: windows, nights, mean, median, population SD, IQR. User02: coverage per mat.

η² = SS_between / SS_total of the one-way layout over the states present, described only as "the proportion of observed
target variance associated with heater context":

- **A1** raw target;
- **A2** target minus its mean within (subject, night);
- **A3** User02 only: target minus its mean within (subject, night, mat).

Sensitivity: η² over the `ON`/`OFF` windows only. Each η² gets a night-cluster percentile interval with the frozen
bootstrap settings (2,000 resamples, `default_rng(0)`, 95 %), resampling whole nights.

## 5. Analysis B — heater-conditioned source constant (diagnostic comparator)

Per outer fold the held-out subject is excluded from every fit. From the source training windows only: mean of each
target over `ON` windows, over `OFF` windows and over all windows, and the overall median. Prediction rule for a
held-out window: `ON → source ON mean`, `OFF → source OFF mean`, `UNKNOWN → source overall mean`; a state with no source
window also falls back to the overall mean. The rule is not changed after results are seen.

Comparators: source training mean, source training median, heater-conditioned source mean. Metrics: MAE, RMSE, bias.
Spans: **full** (constants from the full source pool, evaluated on all labelled test windows) and **common** (constants
from the common source pool, evaluated on the P11 common test endpoints). The two spans are never averaged together.

Paired night bootstrap (the P10/P11 function, unchanged): ΔMAE = MAE(source mean) − MAE(heater-conditioned mean) per
subject × target, with the 95 % interval and its side; (source median, heater-conditioned) is secondary.

## 6. Analysis C — supplementary, descriptive

On the common span, MAE of the training mean, HGB 40/300/900 s and the common-pool RAW-TCN (seed mean) **within each
heater state**, from the committed P10/P11 predictions. Nothing is refitted. It shows where the longer-history gain
sits relative to heater context.

## 7. Interpretation map (fixed now)

η² labels: < 0.06 "small", 0.06–0.14 "medium", ≥ 0.14 "large".

- **CASE A** — raw η² < 0.06 and night-centred η² < 0.06: weak evidence that heater context is a main level proxy.
- **CASE B** — raw η² ≥ 0.06 and night-centred η² < 0.06: heater context is entangled with night- or domain-level
  conditions; an independent heater contribution is not isolated.
- **CASE C** — night-centred η² ≥ 0.06: an association with short-timescale target variation remains; occupancy,
  ambient and controller-policy confounding still rule out a causal heater claim.

For User02 the night × mat-centred value (A3) is the primary sensitivity diagnostic. Cases are assigned per subject and
target on the full span; the common span is reported beside it.

**Competing explanation (question 6).** For each subject–target pair whose P10 interval of
MAE(training mean) − MAE(HGB-900) was above zero: *plausible* if the common-span interval of
MAE(source mean) − MAE(heater-conditioned) is above zero and its point estimate is at least half of the HGB-900 gain;
*not supported* if that interval includes or is below zero and the night-centred η² < 0.06; otherwise *unresolved*.

**Mechanisms (question 7).** P12 is observational. It cannot separate (A) sustained contact/load history acting as a
proxy for slower thermal and moisture dynamics from (B) pressure/contact history co-varying with heater, controller and
environment context. The report states this explicitly whatever the numbers are.

Wording: no causal heater effect; "associated with", never "explained by"; N = 3 retrospective cases; no population
inference.

## 8. Validation

- Heater look-up: no future event, > 60 min → `UNKNOWN`, other mat ignored, other subject ignored (tests).
- Held-out subject never in a fit (fails closed; test). `UNKNOWN` fallback = source overall mean (test).
- Common endpoints: keys and targets equal to the committed P11 predictions.
- Source mean/median metrics equal to the committed P3 (full span) and P10/P11 (common span) tables to 1e-9.
- Deterministic re-run: byte-identical tables in a second output root.
- SHA-256 of every file under `outputs/runs/p3`, `outputs/runs/p10`, `outputs/metrics/p3`, `outputs/metrics/p10`,
  `outputs/p11_common_pool_tcn` and `paper/tables` before and after.
- Plan/config hashes written before the first statistic and re-checked at the end.

## 9. Outputs

`outputs/p12_heater_diagnostic/`: `heater_code_audit.csv`, `heater_context_counts.csv`, `heater_target_summary.csv`,
`heater_eta_squared.csv`, `heater_constant_metrics_full.csv`, `heater_constant_metrics_common.csv`,
`heater_bootstrap_full.csv`, `heater_bootstrap_common.csv`, `heater_predictions_metadata.csv`,
`heater_history_gain_by_context.csv`, `heater_interpretation.csv`, `pre_result_design_hashes.json`, `validation.json`,
`provenance.json`. Report: `docs/P12_HEATER_DIAGNOSTIC_REPORT.md`.

## 10. Limits stated in advance

- Only AHON/AHOF define the context; FOF/FON and other ambiguous codes are not used, so `UNKNOWN` and `OFF` may hide
  heater actions the definition does not see.
- Context is event-conditioned within 60 min; most windows may be `UNKNOWN`.
- Control codes are temperature-derived, so an association with temperature is partly built in.
- No new model family is explored after P12.
