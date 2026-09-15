# Experiment Protocol

> **Status: FROZEN — protocol version v1.0.**
> - Frozen in P2, before any model was trained on the study data. The tag `p2-protocol-freeze` is set on `main`
>   after the P2 merge.
> - Machine-readable parameters: `configs/experiments/v1.0/protocol.yaml`.
> - Split files and hashes: `data/splits/v1.0_manifest.json`.
> - Rationale: `docs/DECISIONS.md` D-029 … D-042.
> - Changing any item below requires a new decision entry and a new protocol version (§14).

Governing rules: `docs/RESEARCH_PROTOCOL.md` (L1–L12) and `docs/DATA_POLICY.md`. Where this file names an
implementation, the implementation is the exact definition, and its tests pin it.

---

## 0. Prerequisites

- [x] P0 dataset audit completed and merged (`docs/P0_DATASET_AUDIT_REPORT.md`, tag `p0-data-freeze`).
- [x] Identity issues resolved or made non-blocking:
  - OPEN-01: closed by D-017;
  - OPEN-02: quarantined, not in canonical_v1 (D-023);
  - OPEN-03: closed by D-027 and D-036;
  - OPEN-04: non-blocking, D-029.
- [x] P1 domain-shift EDA completed and merged (`docs/P1_DOMAIN_SHIFT_EDA_REPORT.md`).
- [x] Leakage validation checks implemented and tested (`src/evaluation/leakage.py`, `tests/test_leakage.py`; §12).

## 1. Cohort and inclusion (D-020, D-023, D-029)

- **Primary cohort:** User01, User02, User07. There are three subjects and three LOSO folds.
  - User02 is one subject with two concurrent mats, 22480 and 22482 (§4, D-036).
- **Auxiliary sources** (User02 legacy, User03 legacy) are not used by protocol v1.0 in any partition.
- **Not in canonical_v1:**
  - the User06 source (`excluded_invalid`, D-017);
  - the two quarantined files (D-006, D-023).
- No subject, device, session, night or phase is excluded from any partition, and nothing is removed after results
  are seen.
- **Claim scope:** "an unseen subject under the observed combined subject–period–season–device shift". No two
  primary subjects were recorded at the same time (A11 §5, P1 §6–§7). It is not a pure biological subject effect or
  population-level generalisation.

## 2. Canonical data source (D-028, D-029)

- **Input:** `data/interim/canonical_v1/primary.parquet`, the only input of protocol v1.0. It is read through
  `src/evaluation/canonical_input.py`, which:
  - verifies every canonical file against `canonical_v1_build.json`;
  - refuses raw and non-canonical paths;
  - asserts that only `primary_candidate` rows and no excluded source are present.
- **Frozen P0 policies used as they are:**
  - de-duplication (D-014);
  - timestamps: naive local, `local_unspecified` (D-026);
  - sessions (D-024);
  - target flags (D-025);
  - pressure validity (D-018): all primary rows are valid;
  - `sensor_phase` (D-019);
  - `channel_quality_phase` (D-022);
  - separate User02 streams (D-027).
- Hashes the splits were built from (recorded in the split manifest):
  - primary content `26b970a4edce2bd5…`;
  - primary file `1b34342b9906d288…`;
  - raw manifest `f5a27acc59cc7429…`.

## 3. Session and night grouping (D-024, D-030)

- **Session:** `session_id` = `<subject>|<device>|S<nnnn>` from canonical_v1 (a gap > 1,800 s starts a new session).
  - Every session lies in exactly one `sensor_phase` and one `channel_quality_phase`.
  - Counts: User01 157, User02 105 (47 on 22480, 58 on 22482), User07 102.
- **Night:** `night_id` = date(timestamp − 12 h) on naive local time (noon to noon; no timezone conversion).
- **Subject-night:** all rows of one subject on all its devices with one `night_id`.
  - Counts: User01 151, User02 51, User07 100. The shortest has 2.0 h and 2,400 rows.
  - Every recorded subject-night counts.
- A session that crosses noon is cut into session × night pieces for RQ2 (3 sessions; 367 pieces).

## 4. RQ1 — strict LOSO splits (D-031, D-036)

| Fold | Test (held out) | Training pool |
|---|---|---|
| 1 | User01 (all sessions, s1 + s2) | User02 (22480 + 22482), User07 |
| 2 | User02 (22480 + 22482, all phases) | User01, User07 |
| 3 | User07 | User01, User02 (22480 + 22482) |

- Every source, device, session and phase of the held-out subject is test.
- User02's two mats are always in the same partition.
- No device-level LOSO, no auxiliary data.
- File: `data/splits/v1.0_loso/outer_folds.csv`, one row per fold × session with the partition (`train` / `test`),
  phases, time span and row count.

## 5. Nested validation (D-031, D-040)

- Validation uses training subjects only. The held-out subject appears in no inner record.
- For each fold, the two training subjects give two subject-level inner splits:

| Fold | Inner A: train → validate | Inner B: train → validate |
|---|---|---|
| 1 (test User01) | User02 → User07 | User07 → User02 |
| 2 (test User02) | User01 → User07 | User07 → User01 |
| 3 (test User07) | User01 → User02 | User02 → User01 |

- File: `data/splits/v1.0_loso/inner_folds.csv` (`inner_train` / `inner_val`).
- Hyperparameter and model selection, early stopping and epoch choice use inner validation only (§9). The outer test
  is evaluated once per protocol version.

## 6. Preprocessing and scaling (D-033, D-034, D-035)

- **Pressure:** P_scaled = P / 4095 for every channel (fixed 12-bit physical range).
  - No fitted input scaler: none per subject, device, phase or full dataset, and no test statistics.
  - **4095 is kept as observed** (→ 1.0). It is never deleted, clipped, interpolated or masked, and no partition
    drops it.
- **Targets:** z-score per target, with mean and standard deviation from the labelled windows of the training
  partition of the fit.
  - Outer training pool for final models; `inner_train` for inner models.
  - Personalization keeps the base model's statistics (no refit).
  - Metrics are computed after the inverse transform, in °C and %RH.
  - Fit provenance is recorded (`TargetScaler.fit_provenance`) and checked by the gate (L3, L11).
- **Invalid targets:** a window is labelled only if `target_temp_valid` and `target_humidity_valid` are both true at
  its target row.
  - Unlabelled windows are not used for training, validation, adaptation or metrics.
  - Targets are never interpolated, clipped, corrected or replaced.
  - There is no episode or outlier exclusion beyond D-025.
- **No** resampling, interpolation, smoothing, filtering, clipping, channel deletion or imputation of pressure or
  targets.
- **Phases:** `sensor_phase` and `channel_quality_phase` are not inputs and not scaler groups.
  - No phase is excluded or masked.
  - 22482 P1 in `p1_transition` / `p1_response_shift` is used as recorded.
  - Phases act as window boundaries and reporting strata.
- Any fitted transform added in a later protocol version must be fitted on a training partition only.

## 7. Windowing (D-032)

| Item | v1.0 rule |
|---|---|
| Window duration | 40 s (prior-study comparison anchor) |
| Input steps | 8 bins of 5 s |
| Stride | 20 s (50 % overlap) |
| Step value | the last observed row in the bin (no interpolation, no averaging, no fill) |
| Same-second ties | the last row in canonical order (`within_timestamp_order`) |
| Max allowed gap | 5 s between consecutive rows inside a window; a gap > 5 s ends a continuity segment |
| Window starts | t0 = segment start + k · 20 s; the window exists only if t0 + 35 s ≤ the segment's last timestamp |
| Incomplete windows | cannot occur: every bin holds a row by construction (bin width = max gap); otherwise no window is generated |
| Target timestamp | the row used at the last step (window end): past/current pressure → current T/H; no later row |
| Boundaries never crossed | subject, device, session, `sensor_phase`, `channel_quality_phase`, split partition; for RQ2 also `night_id` |
| Missing-upload gaps (22482, D-024) | never bridged by a window |
| Sensitivity windows (P6 only) | 20 s (4 steps, stride 10 s), 30 s (6 steps, stride 15 s), same rule |

- **Order:** splits first (§4, §5, §10). Windows are then generated inside each partition, from the split files (L1).
- **Implementation:** `src/evaluation/windowing.py` (`build_windows` validates every window).
- **Structural counts at 40 s:**
  - windows: User01 289,672, User02 144,205, User07 140,972;
  - labelled: ≥ 99.6 % in every slice.

## 8. Inputs and features (D-038, D-039)

**Admissible inputs** are functions of P1–P6 of the window's step rows only. A fixed allowlist is enforced by the
gate.

**Never inputs:**
- temperature and humidity of any device, and target flags;
- heater/control events, set-points, limits and modes (AHON, AHOF, BHSDOWN, BCSUP, STEMP, SLIMIT, …);
- heater state;
- firmware movement labels;
- calendar and time fields (timestamp, date, month, season, day index, hour, night);
- identity and provenance fields (subject, device, source, file, session, sensor or quality phase).

Feature families (per step k; `src/features/pressure_features.py`):

| Family | Features per step |
|---|---|
| RAW (6) | p_c / 4095 |
| MOVEMENT (10) | Δp_c / 4095 (6); mean \|Δp_c\| / 4095; Δ(sum / (6·4095)); Δ(active / 6); dominant-channel switch. Step 0 = 0 (no predecessor inside the window). |
| CONTACT (11) | sum / (6·4095); active channels (p_c > 0) / 6; shares p_c / Σp (6); normalised share entropy; max share; across-channel std / 4095. All-zero frame: shares, entropy and max share = 0. |

- **Dominant channel:** argmax_c p_c, taking the lowest index on ties; none for an all-zero frame.
- **Compared families:** RAW, MOVEMENT, CONTACT, RAW+MOVEMENT, RAW+CONTACT, RAW+MOVEMENT+CONTACT. The primary
  RQ1/RQ2 family is RAW.
- **Geometry-dependent features are forbidden** while the channel layout is unknown (OPEN-20): coordinates, centre
  of pressure, left/right or head/foot interpretation, spatial moments. Adding one needs a protocol version bump.
- **No feature selection.**

## 9. Baselines and models (D-040)

**Baselines** (P3, identical splits):
1. **Training-mean predictor:** the mean of each target over the labelled windows of the outer training pool
   (deterministic).
2. **TCN on RAW inputs:** the prior study's model family, re-implemented under this protocol.
   - No prior-study configuration value is assumed; it is not in the repository.
   - The configuration comes only from the search below.

**TCN architecture:**
- causal residual TCN, 3 blocks with dilations 1, 2, 4;
- two causal convolutions per block, with ReLU and dropout;
- a 1×1 residual projection when the channel count changes;
- a linear head on the last step with 2 outputs (temperature, humidity);
- loss: MSE on training-standardised targets.

**Search space** (16 configurations):
- channels {32, 64} × kernel size {2, 3} × dropout {0.1, 0.3} × learning rate {1e-3, 3e-4};
- fixed: AdamW, weight decay 1e-4, batch 256, at most 50 epochs, early stopping patience 5.

**Selection** (per outer fold and feature family):
- train on `inner_train` and score on `inner_val` for inner splits A and B, with seed 0;
- criterion: the mean over A and B of (MAE_T / sd_T + MAE_H / sd_H) / 2, with sd from the inner training partition.
  It is for selection only, never an endpoint;
- ties go to the first configuration in grid order.

**Final model:**
- retrained on the full outer training pool for the rounded mean of the two inner best-epoch counts;
- no held-out data.

**Seeds:** 0, 1, 2 for every final model.
- Results are reported per seed and as the mean.
- Seeds are never added or dropped after results are seen.

The prior study's movement-fusion idea is examined through the P4 family comparison (§8).

## 10. Personalization protocol (D-037)

- **Unit:** subject-night, numbered 1…N in time order per target subject.
- **Budgets** b ∈ {0, 1, 3, 7, 14} nights:
  - adaptation = the earliest b nights;
  - buffer = the next recorded night (never used);
  - per-budget test = all later nights;
  - b = 0: no adaptation (baseline).
- **Primary test span:** nights ≥ 16, identical for all budgets. The per-budget later span is secondary.
  - Primary test nights: User01 136, User02 36, User07 85.
- Both User02 mats of an adaptation night are adapted on. Every device of a night shares its partition.
- The deployment timeline is kept: spans may cross sensor/quality phases and seasons (e.g. User01 adapts on `s1`, is
  tested on `s1` + `s2`). No split is rebuilt to avoid a boundary.
- **Base model:** the RQ1 model of the fold holding out the target subject.
- **Fine-tuning** (fixed, never tuned on target data):
  - all parameters, AdamW;
  - learning rate 0.1 × the selected base rate, same weight decay;
  - 10 epochs, batch 256;
  - no early stopping, no scaler refit;
  - seeds 0, 1, 2.
- File: `data/splits/v1.0_personalization/chronological.csv`, one row per subject × budget × session-night piece,
  with `partition` (`adaptation` / `buffer` / `test`) and `primary_test`.

## 11. Metrics and statistics (D-041)

- **Primary endpoints**, per target and never combined across units:
  - MAE and RMSE in °C (temperature) and %RH (humidity), for each held-out subject (User02 = both mats pooled);
  - the unweighted mean over the three subjects.
- **Secondary:**
  - bias (mean signed error);
  - window-weighted pooled metric;
  - device-stratified (22480 / 22482);
  - phase-stratified (User01 s1 / s2; 22482 normal / p1_transition / p1_response_shift);
  - per-night error distribution;
  - seed spread;
  - event-conditioned heater-context strata (P6).
- **RQ2:** per subject, budget and target, MAE/RMSE on the primary test span, and gain_b = MAE(0) − MAE(b). Also the
  unweighted mean over subjects.
- **Statistical unit:** subject first, then night.
  - n = 3: no population-level significance claim; every fold is reported.
  - Within-subject uncertainty (P6): night-level cluster bootstrap, with 2,000 resamples, seed 0 and a 95 %
    percentile interval.
  - Model comparisons: per-subject paired differences, a night-level paired bootstrap, and the number of subjects
    improved (x/3).
  - No window-level significance test.

## 12. Leakage validation gate (D-042)

`src/evaluation/leakage.py`. Every P3+ training entry point calls `gate_for_training(RunContext(...))` before loading
training data and stores the report as `leakage_check.json`. Any failure raises `LeakageGateError` and the run does
not start (L12). A check that raises counts as failed (fail closed).

| Check | Rule |
|---|---|
| split files match their SHA-256 manifest (corruption / hand edits) | L1, L12 |
| canonical data equal the data the splits were built from | L7 |
| exactly three outer folds; held-out subject only in test; each session once per fold | L2, L4 |
| inner validation subject-level, held-out subject absent | L4 |
| adaptation = earliest b nights < one buffer night < test; primary test span identical across budgets | L5 |
| devices of a subject (LOSO) or subject-night (RQ2) in one partition | L8 |
| only canonical primary sessions; no User03 / User06 / auxiliary / quarantined | L6 |
| every canonical session and session × night piece assigned with its exact span | L2, L7 |
| run inputs ⊆ admissible allowlist; no target / control / firmware-label field | L9 |
| no calendar or identity field | L10 |
| fitted transforms: provenance present, training partition only, no held-out/target subject | L3, L11 |
| selection / early stopping subjects ⊆ training pool | L4 |
| every window inside one partition, session, phase (and night) | L1 |

`python scripts/validate_p2_protocol.py` runs the gate for every declared v1.0 run context (3 folds × 6 families,
plus personalization). It also builds and validates every window inside its partition. Result at freeze: 118/118
checks pass.

## 13. Split manifests and hashes (D-042)

| File | Rows | SHA-256 (LF-normalised) |
|---|---|---|
| `data/splits/v1.0_loso/outer_folds.csv` | 1,092 | `59e53c903f8c5a70f8e8bcb8cd2917d314c8e2114b408b7806fada89eb76da86` |
| `data/splits/v1.0_loso/inner_folds.csv` | 1,456 | `567fadee4b731639593e4d1cc8610024a0d07ef3cb2f2dc3457ef753a96230df` |
| `data/splits/v1.0_personalization/chronological.csv` | 1,835 | `8007cfcd4e057cbb7771ea8327ceabc615c5c3ca5a4a08f47ecc73a8393eff59` |

- **Manifest:** `data/splits/v1.0_manifest.json`. It holds:
  - the protocol file hash;
  - canonical and raw-manifest hashes;
  - file hashes and row counts;
  - scheme metadata and generator hashes;
  - build time and git commit.
- **Build and check:**
  - `python scripts/build_p2_splits.py` builds the files deterministically from canonical_v1;
  - `--check` rebuilds them in memory and requires byte-identical files and a semantically identical manifest.
- `.gitattributes` keeps LF for `data/splits/**`.

## 14. Versioning and change policy

- v1.0 is frozen. Any change to the cohort, data version, grouping, splits, windowing, preprocessing, inputs, feature
  families, model family, search space, selection rule, seeds, adaptation budgets or recipe, or metrics:
  - needs a new `DECISIONS.md` entry (rationale without test results; if results were seen, name them);
  - needs a new protocol version (`configs/experiments/v1.1/`, new split files and manifest);
  - reports results under both versions (RESEARCH_PROTOCOL §6).
- Editing a v1.0 split file or `protocol.yaml` breaks the manifest hash, and the gate then refuses training.
- **Known non-blocking limitations,** which the protocol does not depend on:
  - OPEN-02: quarantined attribution;
  - OPEN-04: device IDs of other sources;
  - OPEN-14: metadata dates;
  - OPEN-18: release dates (P7);
  - OPEN-20: channel layout;
  - OPEN-21: acquisition changes inside User01 `s1`.

**Version history:**
- v1.0: frozen in P2. It governs every primary result.
- v1.1 (D-057): a post-hoc validation addendum (`configs/experiments/v1.1/posthoc_validation.yaml`,
  `docs/P8_POSTHOC_VALIDATION_PLAN.md`).
  - It reuses the v1.0 data, splits and windows unchanged.
  - It adds calibration comparators, a residual-variation ratio and an initialization control.
  - Its results are supplementary and do not replace v1.0.

