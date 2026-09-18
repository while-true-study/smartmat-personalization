# P11 audit: common-pool RAW-TCN (before any P11 code or result)

Status: read-only audit of `experiment/p10-level-baseline-history` at `fa00b09`. Nothing was run or changed to write it.
Purpose of P11: remove the training-pool confound that P10 Part H disclosed. P10 compared summary models trained on the
common endpoints with a RAW-TCN that was trained on the full 40-s pool and only re-evaluated on the common test endpoints.
P11 is post hoc and exploratory (D-066, protocol v1.5). It searches nothing and changes no v1.0–v1.4 result.

File name: the lowercase name was requested by the research lead; `docs/CONVENTIONS.md` §1 names phase documents
`P<n>_*_PLAN.md` / `_REPORT.md`, which the plan and the report follow.

## 1. Existing full-pool RAW-TCN pipeline (P3, protocol v1.0)

| Item | Implementation |
| --- | --- |
| Model | `src/models/tcn.py`: causal residual TCN, 3 blocks, dilations (1, 2, 4), two causal convolutions per block with ReLU and dropout, 1×1 residual projection, linear head on the last step, 2 outputs. No normalisation layers. |
| Input | 40-s window = 8 steps of 5 s, last observed row per bin, stride 20 s, max gap 5 s (`src/evaluation/windowing.py`, `configs/experiments/v1.0/protocol.yaml` L27-36). RAW family: six channels, `p / 4095`. **No fitted input scaler** (`src/features/pressure_features.py`, `PRESSURE_DIVISOR`). |
| Folds | `data/splits/v1.0_loso/outer_folds.csv`: fold 1 holds out User01 (train User02 + User07), fold 2 User02 (User01 + User07), fold 3 User07 (User01 + User02). User02's two mats share a partition. |
| Inner splits | `data/splits/v1.0_loso/inner_folds.csv`, built by `src/evaluation/splits.py::loso_inner`: A = first source subject trains, second validates; B = swapped. The held-out subject is in neither. |
| Frozen configuration | `configs/experiments/v1.0/p3_selected_configs.yaml`: fold 1 (64 ch, k 3, dropout 0.1, lr 1e-3), fold 2 (32, 3, 0.3, 3e-4), fold 3 (64, 2, 0.1, 1e-3); AdamW, weight decay 1e-4, batch 256, max 50 epochs, patience 5. |
| Seeds | selection seed 0 for every inner run; final seeds 0, 1, 2 (`protocol.yaml` L133-136). `trainer.set_determinism` seeds Python, NumPy, PyTorch CPU and CUDA, enables deterministic algorithms; the per-epoch shuffle uses a seeded CPU generator. |
| Target scaler | `TargetScaler.fit` (z-score per target, population sd, fit provenance recorded). Inner run: labelled windows of the inner-train subject (`p3_loso.run_inner` L385). Final run: labelled windows of the outer training pool (`run_final` L568), checked against the frozen yaml values to 1e-9. |
| Inner selection | `trainer.train_tcn` with validation data: criterion `(MAE_T/sd_T + MAE_H/sd_H)/2` with sd from the inner-train scaler (`metrics.selection_criterion`); best epoch = first epoch with the strictly lowest criterion; stop after 5 epochs without improvement; at most 50. |
| Final epoch rule | `p3_loso.final_epochs(best_A, best_B) = round_half_up((best_A + best_B) / 2)` with `round_half_up(x) = floor(x + 0.5)` (`metrics.py` L51-53). Frozen values: inner best epochs (4, 5) → 5; (1, 8) → 5; (2, 3) → 3. |
| Outer refit | `run_final`: every labelled window of both source subjects, exactly `final_epochs` epochs, no validation data, constant learning rate, no clipping, no scheduler; the outer test is predicted once and logged. |
| Outputs | `outputs/runs/p3/{inner,selection,final}/…`, `outputs/metrics/p3/*.csv`. Predictions: long parquet, key columns `device_id`, `window_start` (+ session, night, target timestamp). |

## 2. P10 common-pool summary pipeline (protocol v1.4)

- Code: `src/evaluation/p10_history.py`; entry point `scripts/run_p10_history.py`.
- **Availability** (`endpoint_availability` L159-170): an endpoint has history H iff `t_end − H >= first timestamp of its
  continuity segment`. A continuity segment is a run of canonical rows of one subject, mat, session, sensor phase and
  channel-quality phase with inter-row gaps ≤ 5 s (`windowing.continuity_segments`).
- **Common set** (`build_subject` L212-214): `common = labelled & available[40] & available[300] & available[900]`. It is
  computed per subject from that subject's own timestamps and label validity, so it is identical in every fold. In effect
  it is the 900-s availability.
- **Key**: `P8.window_keys(device_id, window_start)` = `"<device>|<epoch seconds>"`. Partition is not part of the key
  because a subject has one role per fold. There is **no persisted manifest** of common endpoints; the set lives in
  `SubjectHistory.common`, and the test keys are recoverable from every P10 `predictions.parquet`.
- **Pools** (`pool` L388-391, `run` L553-589): test, inner-train, inner-validation and outer-train rows are all the
  common endpoints of the respective subjects. Because `features[h]` is built on the common set for every h, Ridge and
  HGB at H = 40, 300 and 900 s use the **same** training endpoints (gate check `common_set_identical_across_histories`;
  `n_train` equal in every `selection.json` of a fold).
- **Counts** (`outputs/metrics/p10/p10_history_availability.csv`): User01 139,735 / 289,437 (48.3 %), User02 74,802 /
  143,999 (51.9 %), User07 61,782 / 140,971 (43.8 %). Common training pools: fold 1 136,584 (full 284,970), fold 2
  201,517 (430,408), fold 3 214,537 (433,436).
- **Bootstrap** (`bootstrap_rows` L433-451 on the frozen P6 functions): night-cluster, 2,000 resamples,
  `default_rng(0)`, 95 % percentile interval, paired (same night draws on both sides), statistic
  ΔMAE = MAE(first) − MAE(second), window-weighted.
- **Metrics**: `metric_row` → `p8_dynamic.signal_stats` (MAE, RMSE, bias, R, Q, r_pooled, r_within, r_within_mat for
  User02).
- Outputs: `outputs/runs/p10/history/fold{k}/{ridge,hgb}_h{40,300,900}/predictions.parquet`,
  `outputs/metrics/p10/p10_history_{metrics,bootstrap,selection,availability}.csv`, copies in `paper/tables/p10_*`.

## 3. How the frozen RAW-TCN is evaluated on the common subset (P10, L607-624)

The P3 final predictions (`outputs/runs/p3/final/fold{k}_seed{s}/predictions.parquet`, status `complete`) are paired with
`LB.strict_pairs`, keyed with `P8.window_keys`, indexed at the common test keys and checked with
`np.array_equal(y_true[ii], y_te)`. The rows carry `train_pool = "full_40s_labelled"`, and the bootstrap pairs that
involve the TCN carry the role `descriptive_different_training_pool`.

## 4. The exact difference between the two pipelines

| Aspect | Summary models (P10) | RAW-TCN in P10 |
| --- | --- | --- |
| Outer training endpoints | common endpoints of the source subjects | all labelled 40-s windows of the source subjects |
| Inner selection endpoints | common (train and validation) | all labelled windows |
| Target scaler | fitted on the common training pool | fitted on the full training pool |
| Epoch count | not applicable | 5 / 5 / 3, derived on the full pool |
| Test endpoints | common | common (key join) |

So a TCN-versus-summary-model difference mixes representation and model family with the training pool. P11 changes only
the first four rows for the TCN.

## 5. Code reused unchanged

`P5.P5Session` (rows, folds, frozen gate), `loso_data.fold_data`, `p10_history.build_subject`,
`p10_history.frozen_fold_windows_equal`, `p10_history.subject_roles`, `p3_loso.inner_subjects`,
`p3_loso.frozen_selection`, `trainer.TCNConfig`, `trainer.train_tcn`, `trainer.predict_z`, `trainer.to_tensor`,
`TargetScaler.fit`, `p3_loso.final_epochs`, `p3_loso.write_predictions`, `p10_history.metric_row`,
`p10_history.bootstrap_rows`, `p10_history.seed_mean`, `LB.constants`, `LB.strict_pairs`, `P8.window_keys`, the
`io_guard` writers and the P3 run bookkeeping (`begin_run`, `complete_run`, `fail_run`, `RunLog`).

## 6. Minimal new code

`p3_loso.run_inner` and `run_final` cannot be called as they are: their masks are hard-coded to every labelled window,
they write under `outputs/runs/p3/`, they skip because the P3 runs are complete, and `run_final` refuses a scaler that
differs from the frozen yaml. P11 therefore adds one thin orchestrator that

1. scatters each subject's `common` mask into the fold index space (order-exact alignment is first asserted with
   `frozen_fold_windows_equal`);
2. runs inner A and B for the **frozen** configuration of the fold (seed 0) with train and validation restricted to the
   common endpoints, and takes `final_epochs(best_A, best_B)`;
3. refits on the common outer training pool for that epoch count with seeds 0, 1, 2, target scaler refitted on that pool;
4. predicts the common test endpoints once per seed and evaluates with the P10 metric and bootstrap functions;
5. reads the committed P10 tables and predictions for HGB and the full-pool TCN without recomputing them.

The 16-configuration grid is **not** re-run: the architecture and hyperparameters stay those of
`p3_selected_configs.yaml`. Runs: 3 folds × (2 inner + 3 final) = 15.

## 7. Epoch rule: reproducible

The rule is a pure function of the two inner best epochs of the selected configuration, and the best-epoch logic lives
inside `train_tcn`. Nothing prevents exact reuse. With about half of the windows an epoch is about half as many updates,
so the re-derived epoch counts may differ from 5 / 5 / 3; that is the intended consequence, not a new rule.

## 8. Leakage risks and how they are closed

| Risk | Status |
| --- | --- |
| Held-out subject influences the common-pool definition | No: `common` is computed per subject from its own timestamps and label validity; no target value, no cross-subject statistic, no fold dependence. |
| Held-out subject in epoch selection | Closed by `inner_subjects` (raises if the held-out subject appears) and by the frozen gate with `selection_subjects=[inner validation subject]`. |
| Target scaler sees validation or test rows | Scaler is fitted on the training mask only; `fit_provenance` is compared with the gated plan; a P11 test asserts the fitted subjects. |
| 900-s eligibility uses future samples | No: the history is `[t_end − 900, t_end)`; P10 checks `has_future_step` per subject and history, and eligibility depends only on gaps before the endpoint. |
| Test labels in selection | The common test endpoints are predicted once per seed after the epoch count is frozen; the access is logged. |
| Common set differs from P10 | P11 asserts key-wise equality of its test keys with the keys of the committed P10 prediction files, equality of `y_true`, and equality of the common training counts with `p10_history_provenance.json`. |
| Existing results overwritten | P11 writes only under `outputs/p11_common_pool_tcn/`; SHA-256 of every file under `outputs/runs/p3`, `outputs/runs/p10`, `outputs/metrics/p3`, `outputs/metrics/p10` and `paper/tables` is recorded before and after the run and compared. |

## 9. Governance

- D-059, D-060 and D-065 stop further experiments unless a new phase is explicitly authorized. The research lead
  requested P11 on 2026-09-18; this is recorded as D-066 with protocol version v1.5
  (`configs/experiments/v1.5/p11_common_pool_tcn.yaml`, `docs/P11_COMMON_POOL_TCN_PLAN.md`), written before any P11 metric.
- Results already seen when P11 was designed: every P3–P10 result, including the full-pool TCN on the common test
  endpoints.
- Output root: `outputs/p11_common_pool_tcn/` as requested (the phase precedent is `outputs/runs/p<N>/`). Outputs are
  git-ignored either way.
- No commit, push, merge or tag is part of this work unless the research lead asks for it.

## 10. Verdict

No obstacle: the common endpoint set, the inner structure and the final-epoch rule are all reproducible from existing
functions. Implementation proceeds under D-066.
