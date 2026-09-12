# P2 — Evaluation Protocol & Split Freeze

| | |
|---|---|
| Phase | P2 (`docs/RESEARCH_PROTOCOL.md` §5), branch `research/p2-split-freeze` (from `main` at `61edfaf`, P1 merged) |
| Result | Protocol **v1.0** frozen: `docs/EXPERIMENT_PROTOCOL.md`, `configs/experiments/v1.0/protocol.yaml`, decisions D-029 … D-042 |
| Splits | `data/splits/v1.0_loso/{outer_folds,inner_folds}.csv`, `data/splits/v1.0_personalization/chronological.csv`, manifest `data/splits/v1.0_manifest.json` (committed) |
| Code | `src/evaluation/{protocol,splits,windowing,leakage,p2_protocol}.py`, `src/features/pressure_features.py` |
| Commands | `scripts/audit_p2_window_feasibility.py`, `scripts/build_p2_splits.py [--check]`, `scripts/validate_p2_protocol.py` |
| Tests | `tests/test_{windowing,splits,leakage,pressure_features}.py` (synthetic data) |

**No model was trained and no prediction, loss, MAE, RMSE or R² was produced in P2.** Every P2 statistic is
structural: timestamps, coverage, window and night counts, and validity flags. **Decide first, then train.**

## 1. Purpose

Fix everything that could be tuned against test results before any model result exists:
- cohort use, preprocessing, scaling and windowing;
- the RQ1 LOSO and nested-validation splits;
- the RQ2 chronological split;
- feature admissibility, model selection and metrics;
- the leakage gate that stops any training run that violates them.

After P2, every change needs a new decision and a new protocol version.

## 2. P0/P1 inputs

- **P0** (tag `p0-data-freeze`):
  - canonical_v1 primary rows (4,136,059) of User01, User02 (22480, 22482) and User07;
  - sessions (D-024), target flags (D-025), timestamps (D-026);
  - `sensor_phase` (D-019), `channel_quality_phase` (D-022), separate User02 streams (D-027).
- **P1** (`docs/P1_DOMAIN_SHIFT_EDA_REPORT.md`), the evidence P2 had to respect:
  - User01 s1 ↔ s2 pressure shift ≈ a between-subject shift;
  - s1's pressure scale is 1.5–2.9× the others, with 4095 in 22.1 % of s1 rows;
  - the two User02 mats differ by 3 °C / 14 %RH;
  - the 22482 response shift changes pressure, not T/H;
  - subjects, seasons, periods and devices are confounded;
  - time of night is secondary;
  - control events derive from temperature;
  - pressure–T/H links are weak and domain-specific.

P1 was used to set boundaries, strata and claims, not to make any model look better.

## 3. Decisions frozen in P2

| # | Protocol question | Decision | Entry |
|---|---|---|---|
| 1 | window continuity | no gap > 5 s inside a window; never across subject/device/session/phase/partition (+ night for RQ2) | D-032 |
| 2 | window duration / stride | 40 s, 8 × 5 s steps, stride 20 s; 20/30 s only as P6 sensitivity | D-032 |
| 3 | timestamp irregularity | last observed row per 5-s bin; ties = last row in canonical order; no resampling to invented values | D-032 |
| 4 | pressure scaling | P / 4095, no fitted input scaler | D-033 |
| 5 | target normalisation | z-score from training-partition labelled windows; metrics in °C / %RH | D-034 |
| 6 | invalid targets | label only if both targets valid at the target row; nothing repaired | D-034 |
| 7 | 4095 | kept as observed; sensitivity only in P6 | D-033 |
| 8 | User01 sensor phase | boundary and stratum; not an input; not excluded | D-035 |
| 9 | User02 dual device | two streams of one subject; no fusion; device strata secondary | D-036 |
| 10 | 22482 response shift | boundary and stratum; P1 used as recorded; not excluded | D-035 |
| 11 | RQ1 LOSO | 3 folds, whole subject held out | D-031 |
| 12 | nested validation | subject-level two-way inner splits | D-031 |
| 13 | RQ2 unit | subject-night (noon to noon) | D-030, D-037 |
| 14 | adaptation budgets | 0, 1, 3, 7, 14 earliest nights | D-037 |
| 15 | buffer | one recorded subject-night; common primary test span from night 16 | D-037 |
| 16 | LOSO aggregation | per subject, then unweighted mean over 3 | D-041 |
| 17 | heater/control | not an input; targets kept; stratification only | D-038 |
| 18 | firmware movement labels | not inputs | D-038 |
| 19 | contact-structure features | geometry-free only | D-039 |
| 20 | calendar/time inputs | none | D-038 |
| 21 | hyperparameter selection | 16-configuration grid, inner validation only, seeds 0/1/2 | D-040 |
| 22 | leakage gate | `src/evaluation/leakage.py`, fail-closed, mandatory before training | D-042 |
| 23 | split artifacts | session / session×night assignments + SHA-256 manifest, committed | D-042 |
| 24 | statistical unit | subject, then night; night-level bootstrap in P6; no window-level tests | D-041 |

Cohort use, data source and change policy: D-029. Night definition: D-030.

## 4. Cohort and device policy

- **Primary subjects:** User01, User02, User07.
- **Not used:**
  - auxiliary (User02 legacy, User03 legacy): not read by v1.0;
  - User06 source and quarantined files: not in canonical_v1, absent from every split (checked by the gate).
- **User02** (D-036):
  - 22480 and 22482 are two window streams of one subject: no 12-channel merge, fusion, alignment, averaged targets,
    cross-device labels or device preference;
  - in LOSO both mats are on the same side of every fold; in RQ2 both mats of a night share its partition (L8);
  - User02 counts once in every subject metric. Device-stratified metrics are secondary and never add subjects.
- **Phases** (D-035):
  - User01 `s1`/`s2` and 22482 `normal`/`p1_transition`/`p1_response_shift` are window boundaries and reporting
    strata, never inputs;
  - no phase is excluded, masked or given its own scaler;
  - the boundaries are fixed and cannot be moved after results.

## 5. Windowing protocol

A structural audit (`scripts/audit_p2_window_feasibility.py`) compared three representations. It looked only at
timestamps and flags, never at a model.

| Slice | Gap > 5 s | Gap-free / session time | Windowable / gap-free | A: empty 1-s cells | B: 14-row span p05–p95 | C: first→last step p05–p95 | C labelled |
|---|---|---|---|---|---|---|---|
| User01/s1 | 13,975 | 89.9 % | 97.7 % | 64.0 % | 26–41 s | 33–37 s | 99.85 % |
| User01/s2 | 3,591 | 98.8 % | 99.7 % | 66.6 % | 37–41 s | 33–37 s | 100.00 % |
| User02/22480 | 1,436 | 99.2 % | 99.9 % | 66.6 % | 37–41 s | 33–37 s | 100.00 % |
| User02/22482/normal | 1,074 | 96.5 % | 99.8 % | 66.6 % | 37–41 s | 33–37 s | 99.60 % |
| User02/22482/p1_shift | 524 | 98.1 % | 99.9 % | 66.6 % | 37–41 s | 33–37 s | 99.99 % |
| User07 | 4,864 | 97.3 % | 99.6 % | 66.6 % | 37–41 s | 33–37 s | 100.00 % |

- **A (1-s grid)** leaves two-thirds of the cells empty, so it needs fill or mask values. Rejected.
- **B (fixed row count)** changes its time scale by domain: User01/s1 has a 2-s sampling episode (OPEN-21). Rejected.
- **C (time bins, last observation)** has the same time scale everywhere, uses only observed rows and keeps
  ≥ 97.7 % of the gap-free time. **Chosen.**
- Most of User01/s1's coverage loss is missing time: its ≈ 2-min pauses and other gaps > 5 s. Only 2.3 % of its
  gap-free time lies in segments too short for a window (≤ 0.4 % elsewhere).

Frozen rule (EXPERIMENT_PROTOCOL §7):
- [t0, t0 + 40 s) cut into 8 bins of 5 s, stride 20 s;
- t0 = segment start + k · 20 s, and the window exists only if t0 + 35 s ≤ the segment end, so every bin has a row;
- step = the last observed row in the bin;
- target = T/H of the last step row;
- 4095 is kept.
- Every window is validated against its bins, boundaries and gaps (`validate_windows`).

The 40 s choice is the prior-study comparison anchor. It was not chosen by any model result. 20 s and 30 s windows
are feasible (User01/s1 windowable 89.3 % and 88.6 % of session time) and are declared for P6.

Structural window counts at 40 s: User01 289,672, User02 144,205 (22480 57,492; 22482 86,713), User07 140,972.

## 6. RQ1 LOSO and nested validation

| Fold | Test | Train pool | Test windows (labelled) | Train windows (labelled) | Inner A (train → val) | Inner B |
|---|---|---|---|---|---|---|
| 1 | User01 | User02, User07 | 289,672 (289,437) | 285,177 (284,970) | User02 → User07 | User07 → User02 |
| 2 | User02 | User01, User07 | 144,205 (143,999) | 430,644 (430,408) | User01 → User07 | User07 → User01 |
| 3 | User07 | User01, User02 | 140,972 (140,971) | 433,877 (433,436) | User01 → User02 | User02 → User01 |

- The held-out subject is in no inner record.
- Selection uses only the two inner splits (D-040).
- The outer test is evaluated once per protocol version.
- Each fold holds out a subject and also its period, season mix and device/sensor configuration. The RQ1 claim is
  therefore "an unseen subject under the observed combined domain shift".

## 7. RQ2 chronological personalization

| Subject | Nights | Primary test nights (≥ 16) | Adaptation windows at b = 1 / 3 / 7 / 14 | Primary test windows |
|---|---|---|---|---|
| User01 | 151 | 136 | 1,087 / 3,050 / 7,675 / 21,419 | 266,084 |
| User02 | 51 | 36 | 3,506 / 10,354 / 23,060 / 44,807 | 96,037 |
| User07 | 100 | 85 | 2,075 / 5,775 / 12,405 / 23,932 | 114,839 |

- The partition order is adaptation (earliest b nights) → one buffer night → test.
- **The primary test span is the same for every budget.** Otherwise budget effects would be confounded with drift
  over the extra, earlier test nights. The per-budget later span is kept as secondary.
- The deployment timeline is preserved:
  - User01 adapts on `s1` in 2025-08…11 and is tested across `s1` and `s2`;
  - User02's test span contains the 22482 shift phase and six 22482-only days.
  Gains are therefore reported with phase strata, and not called pure user adaptation.
- The fine-tuning recipe is fixed (D-037). Nothing is tuned on target data.

## 8. Preprocessing / scaling

- Pressure P / 4095; 4095 kept; no fitted input transform.
- Targets z-scored with training-partition statistics (recorded fit provenance), inverted for metrics.
- Labels require both targets valid at the target row. Invalid targets are never repaired.
- **Why a fixed scale rather than train-only statistics:**
  - the pressure-scale shift (User01/s1) is part of the deployment shift RQ1 measures;
  - statistics fitted on two training subjects would not remove that shift for the held-out subject, and would make
    the input representation fold-dependent;
  - test-subject statistics are forbidden (L11).
  This rationale is methodological; no performance was consulted.

## 9. Feature admissibility

- **Inputs:** only P1–P6 of the window rows, through the fixed feature formulas (allowlist enforced by the gate).
- **Families (D-039), per step:**
  - RAW (6);
  - MOVEMENT (10): per-channel and summary differences between steps, and dominant-channel switches;
  - CONTACT (11): sum, active count, channel shares, entropy, max share, spread;
  - combinations: RAW+MOVEMENT, RAW+CONTACT, RAW+MOVEMENT+CONTACT.
  The formulas are in EXPERIMENT_PROTOCOL §8 and `src/features/pressure_features.py`.
- **Not admissible:**
  - temperature/humidity and target flags;
  - control events, heater state (OPEN-10) and firmware movement labels (OPEN-15);
  - calendar/time fields;
  - subject/device/source/session/phase identifiers;
  - geometry-dependent features (OPEN-20 is not invented).

## 10. Metrics / statistics

- **Primary:** MAE and RMSE per target, in °C and %RH:
  - per held-out subject (User02 pools both mats);
  - the unweighted mean over the three subjects.
- There is no unit-mixing endpoint, and no window-weighted primary metric.
- **Secondary** (declared now): bias, micro-pooled, device strata, phase strata, per-night distribution, seed spread,
  heater-event strata.
- **Statistics:**
  - n = 3, so there is no population-level significance claim;
  - within-subject uncertainty from a night-level cluster bootstrap (P6);
  - model comparisons: per-subject paired differences and the number of subjects improved;
  - no window-level tests.

## 11. Leakage gate

`src/evaluation/leakage.py` implements L1–L12 as fail-closed checks (list in EXPERIMENT_PROTOCOL §12). The protocol
file hash and the canonical data hashes are checked against the split manifest. P3+ runners must call
`gate_for_training(RunContext(...))`, which raises `LeakageGateError` on any failure.

`scripts/validate_p2_protocol.py` on the frozen splits:
- runs the split-level checks;
- runs the run-level checks for 3 folds × 6 feature families and 3 personalization subjects;
- validates every window built inside every partition;
- confirms that 4095 rows are retained.

**Result: 118/118 checks pass** (§14).

Synthetic tests prove that each violation is caught:
- a held-out subject in training or in inner validation;
- a device split across partitions;
- adaptation after test, or a missing buffer;
- User06 in a split;
- an edited split, protocol file or canonical file;
- forbidden inputs (targets, control events, firmware labels, IDs, calendar);
- scalers fitted on test or target data;
- selection on the held-out subject;
- a window crossing a partition.

## 12. Split files and hashes

| File | Rows | SHA-256 (LF-normalised) |
|---|---|---|
| `v1.0_loso/outer_folds.csv` | 1,092 | `59e53c903f8c5a70f8e8bcb8cd2917d314c8e2114b408b7806fada89eb76da86` |
| `v1.0_loso/inner_folds.csv` | 1,456 | `567fadee4b731639593e4d1cc8610024a0d07ef3cb2f2dc3457ef753a96230df` |
| `v1.0_personalization/chronological.csv` | 1,835 | `8007cfcd4e057cbb7771ea8327ceabc615c5c3ca5a4a08f47ecc73a8393eff59` |

- Each record is a group assignment (session, or session × night piece) with partition, phases, time span and row
  count. There are no sensor or target values and no row IDs.
- The manifest records:
  - protocol and canonical hashes (primary content `26b970a4edce2bd5…`);
  - the raw manifest hash (`f5a27acc59cc7429…`);
  - file hashes, scheme metadata and generator hashes;
  - build time and commit.
- `build_p2_splits.py --check` reproduces byte-identical files.

## 13. Open non-blocking limitations

- **n = 3 subjects** with confounded subject, period, season and device (A11, P1). No isolated user effect and no
  population claim.
- **Inner validation** transfers between only two subjects, so model selection is noisy (accepted; D-031).
- **The prior study's exact configuration** is not in the repository. The TCN is configured only by the declared
  search space (D-040).
- **Provider questions the protocol does not depend on:**
  - OPEN-02: attribution of the quarantined files;
  - OPEN-04: device IDs of other sources;
  - OPEN-14: metadata dates;
  - OPEN-18: release date format (P7);
  - OPEN-20: channel layout;
  - OPEN-21: acquisition changes inside User01 `s1`.
- **The heater-controlled microclimate** stays part of the target. Control context is a P6 stratum, not an input.

## 14. Reproducibility checks

| Check | Result |
|---|---|
| canonical_v1 parquet SHA-256 (3 files) and manifests vs P2 start | unchanged |
| raw integrity | 377 / 377 files, no hash mismatch |
| split rebuild (`build_p2_splits.py --check`) | byte-identical files, identical manifest content |
| leakage gate (`validate_p2_protocol.py`) | 118/118 checks pass (fail-closed) |
| pytest (full suite) | all pass |
| model outputs | none produced in P2 |

## 15. P2 closure assessment

**P2 closure conditions:**
- `EXPERIMENT_PROTOCOL.md` v1.0 is complete, with no TBD.
- Decisions D-029–D-042 are appended.
- The outer LOSO, nested and personalization splits are frozen and committed with their SHA-256 manifest.
- The windowing, preprocessing/scaling, feature admissibility, metrics and model-selection rules are frozen.
- The leakage gate is implemented and passing.
- The tests pass, and canonical_v1 and raw are unchanged.
- The README shows P1 completed and P2 current.

**P2 can be closed.**

**Frozen for P3:**
- protocol v1.0;
- the split files and manifest;
- the window rule;
- scaling, labels, inputs and feature families;
- the TCN search space, selection rule and seeds;
- the metrics and statistical unit;
- the leakage gate requirement.

After the P2 PR is merged, the freeze tag `p2-protocol-freeze` is created on `main`.
