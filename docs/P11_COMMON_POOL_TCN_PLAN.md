# P11 — Common-pool RAW-TCN: plan (protocol v1.5 addendum, D-066)

> **Status: post-hoc exploratory addendum. Written before any P11 metric was computed.**
> - Requested by the research lead on 2026-09-18 as a new phase outside the D-059/D-060/D-065 stop rules. The stop
>   rules stay recorded as history.
> - **Results already seen when this plan was written:** every P3–P10 result, including the full-pool RAW-TCN
>   re-evaluated on the P10 common test endpoints. P11 is **not** confirmatory and is never described as originally
>   planned.
> - Machine-readable parameters: `configs/experiments/v1.5/p11_common_pool_tcn.yaml`. The SHA-256 of this plan and of
>   that config is recorded in the P11 outputs. Neither file is edited after the first P11 computation.
> - Nothing in v1.0–v1.4 is edited. P11 writes only under `outputs/p11_common_pool_tcn/` (root requested by the
>   research lead) and its own documents. Audit: `docs/p11_common_pool_tcn_audit.md`.

## 1. Question

P10 Part H trained Ridge and histogram-boosting models on the endpoints with 900 s of gap-free history ("common
endpoints") but compared them with a RAW-TCN trained on every labelled 40-s window. A difference between the two
therefore mixes representation and model family with the training pool. P11 asks one thing:

> Does restricting the RAW-TCN's training pool to the same common endpoints change its error on the common test
> endpoints, and does it change how the 40-s RAW-TCN compares with the simple level baselines?

P11 is not a model search. It does not look for a better model and has no result it is meant to reach.

## 2. What is fixed

| Item | Value |
| --- | --- |
| Input | RAW 40-s window, 8 steps of 5 s, six channels, `p / 4095`. **No 900-s sequence enters the TCN.** |
| Architecture and hyperparameters | per fold from `configs/experiments/v1.0/p3_selected_configs.yaml`; no grid search, no new value |
| Optimizer, learning rate, batch, weight decay, patience, max epochs | as frozen in v1.0 |
| Folds | User01, User02, User07 held out in turn (`data/splits/v1.0_loso/`) |
| Seeds | inner seed 0; final seeds 0, 1, 2 |
| Endpoint rule | the P10 common set: labelled and available at 40, 300 and 900 s; computed per subject |
| Metrics, bootstrap | the P10 functions, unchanged (night-cluster, 2,000 resamples, seed 0, 95 % percentile) |

## 3. What changes, and only this

1. **Inner runs.** For each outer fold, inner A and inner B are run once with the fold's frozen configuration, with the
   inner-training and the inner-validation windows restricted to the common endpoints. The target scaler is fitted on
   the inner-training common windows.
2. **Epoch count.** `final_epochs = round_half_up(mean(best epoch A, best epoch B))` — the v1.0 rule
   (`p3_loso.final_epochs`). The count may differ from the frozen 5 / 5 / 3 because an epoch over about half of the
   windows is about half as many updates. No other epoch rule is introduced.
3. **Final runs.** Seeds 0, 1, 2: the outer training pool is the common endpoints of the two source subjects; the
   target scaler is refitted on that pool; exactly `final_epochs` epochs; no validation data.
4. **Test.** The common endpoints of the held-out subject, predicted once per seed after the epoch count is fixed.

Runs: 3 folds × (2 inner + 3 final) = 15.

## 4. Comparison (same common test endpoints)

Training mean (common pool), training median (common pool), RAW-TCN common pool (new), RAW-TCN full pool (frozen P3
predictions), HGB 40 s, 300 s, 900 s. HGB and the full-pool TCN are **read** from the committed P10 / P3 prediction
files; they are not refitted, retuned or reselected. P11 recomputes their metrics with the same functions only to assert
equality with the committed P10 tables.

Paired night bootstrap, ΔMAE = MAE(first) − MAE(second): (mean, TCN-common), (median, TCN-common), (TCN-common, HGB-40),
(HGB-40, HGB-300), (HGB-40, HGB-900), and (TCN-full, TCN-common) for the pool-restriction effect. Seed 0 is primary;
seeds 1 and 2 are reported separately.

## 5. Interpretation map (fixed now)

A subject "exceeds the level baselines" for a target iff the seed-0 intervals of MAE(mean) − MAE(TCN-common) **and** of
MAE(median) − MAE(TCN-common) are both above zero.

- **Case A** — no subject: the 40-s RAW-TCN still does not exceed the level baselines once the training pool is matched.
- **Case B** — exactly one subject: a subject-specific advantage; the "no consistent advantage" statement stays but is
  qualified.
- **Case C** — at least two of three subjects: the statement "the 40-s RAW-TCN did not consistently exceed simple level
  baselines" does not hold on the common endpoints and the manuscript must say so.

Whatever the case, the TCN-versus-HGB comparison at 40 s is reported as a difference between two pipelines on three
retrospective cases, never as architecture superiority, and the pool-restriction effect (TCN-common minus TCN-full) is
reported for every subject and target with its seed range. All folds and seeds are reported.

## 6. Leakage and validation

- The v1.0 gate runs before every inner and final run (`P3Session.gate`), with the fit plan and selection subjects of
  the run; it fails closed.
- The common masks are aligned with the frozen fold windows by `p10_history.frozen_fold_windows_equal` before use.
- Key-wise equality of the P11 test keys and targets with every committed P10 prediction file of the fold; equality of
  the common training counts with `p10_history_provenance.json`.
- The held-out subject never appears in a scaler fit, an inner run or the epoch rule.
- SHA-256 of every file under `outputs/runs/p3`, `outputs/runs/p10`, `outputs/metrics/p3`, `outputs/metrics/p10` and
  `paper/tables` before and after the run.
- Tests: `tests/test_p11_common_pool_tcn.py`.

## 7. Outputs

`outputs/p11_common_pool_tcn/`: `common_pool_counts.csv`, `common_pool_epoch_selection.csv`,
`common_pool_tcn_per_seed.csv`, `common_pool_tcn_seed_mean.csv`, `common_pool_model_comparison.csv`,
`common_pool_bootstrap.csv`, `validation.json`, `provenance.json`, and `runs/{inner,final}/…`.
Report: `docs/P11_COMMON_POOL_TCN_REPORT.md`.

## 8. Limits stated in advance

- N = 3 retrospective cases; no population inference.
- The common subset (44–52 % of the labelled endpoints) may favour long, stable recordings (P10 report §6).
- The per-fold configuration was selected on the full pool; P11 keeps it on purpose so that only the pool changes.
- A different result with a re-run grid would be a different experiment and is not authorized.
