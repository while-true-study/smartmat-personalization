# Experiment Protocol

> **Status: PLACEHOLDER — NOT FROZEN (protocol version v0.0).**
> Nothing in this file may be used to generate splits, windows, processed data or models yet.
> Each section is filled in by a dated `DECISIONS.md` entry; the protocol is frozen as `v1.0`
> only when every section is decided and the open items listed under "Blocked by" are closed.
> Freezing happens at the end of phase P2 (tag `p2-protocol-freeze`), before any model result is seen
> (`RESEARCH_PROTOCOL.md` §5).

Governing rules: `docs/RESEARCH_PROTOCOL.md` (L1–L12) and `docs/DATA_POLICY.md`.

---

## 0. Prerequisites

- [ ] P0 dataset audit completed and reviewed (`docs/initial_dataset_inventory.md`, `outputs/qa/`)
- [ ] Identity issues resolved: OPEN-01, OPEN-02, OPEN-03, OPEN-04
- [ ] Leakage validation checks implemented (`src/evaluation/`) and tested

## 1. Cohort and inclusion — TBD
Primary cohort, auxiliary usage, exclusion criteria (defined without looking at model results).
Blocked by: OPEN-01, OPEN-03, OPEN-13, OPEN-16.

## 2. Interim data construction — TBD
Parsing rules per format family, timestamp/year policy, de-duplication, handling of non-data lines,
sentinel/glitch values. Output: `data/interim/` with full provenance.
Blocked by: OPEN-07, OPEN-08, OPEN-09, OPEN-12.

## 3. Session definition — TBD
How continuous recordings are delimited (gap threshold, night boundary), how concurrent devices of a
subject are grouped. Blocked by: OPEN-03, OPEN-06.

## 4. Splits (defined before windowing) — TBD
- RQ1: leave-one-subject-out over the primary cohort; nested validation from training subjects only.
- RQ2: per target subject, chronological adaptation span → buffer gap → test span.
- Split files saved under `data/splits/<split_id>/` with SHA-256 recorded.

## 5. Preprocessing — TBD
Resampling, interpolation, filtering, normalisation (fit on training partition only), handling of
pressure-scale differences and the User01 sensor replacement. Blocked by: OPEN-11, OPEN-17.
P0 input: User01 rows carry the provenance label `sensor_phase` s1/s2 (D-019). Phase-aware handling is decided here.

## 6. Windowing and features — TBD
Window length/stride; movement-derived feature set; contact-structure feature set; admissible event
inputs (L9, L10). Blocked by: OPEN-10, OPEN-15.

## 7. Models and training — TBD
Baselines (training-mean, prior-study method), candidate models, hyperparameter search space and budget.

## 8. Personalization protocol — TBD
Adaptation data budgets, buffer length, fine-tuning scope, no tuning on the test span.
For User01, whether adaptation and test spans may cross the `sensor_phase` boundary (D-019) is decided here (OPEN-11, OPEN-21).

## 9. Metrics and statistics — TBD
Primary: MAE, RMSE per target, per subject and subject-averaged. Uncertainty over subjects/sessions.

## 10. Leakage validation gate — TBD
Automated checks run before every training job; training refuses to start on failure (L12).
