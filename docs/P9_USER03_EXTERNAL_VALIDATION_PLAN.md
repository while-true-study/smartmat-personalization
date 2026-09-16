# P9 — User03 external sensitivity validation: plan (protocol v1.3 addendum, D-061)

> **Status: written before any User03 reconciliation, window, label or model output was computed.**
> - The SHA-256 of this file and of `configs/experiments/v1.3/p9_user03_external_validation.yaml` is recorded in
>   every P9 output.
> - **Post hoc.** P9 was conceived after the P3–P8 results were known.
> - **Role of User03:** an additional external sensitivity subject only. User03 is **not** added to the primary
>   cohort (User01, User02, User07). Its results are never pooled with the primary three-subject results.
> - **Scope:** RQ1-like external evaluation only; no RQ2 personalization.
> - Every result is reported, whichever way it points.

## 1. Question

> Trained on all three primary subjects, does the RAW-TCN estimate User03's microclimate better than a training-mean
> predictor, and do its predictions co-vary with User03's temperature and humidity within nights?

The answer is used only to state whether the N = 3 conclusions are strengthened, weakened or mixed for one further
held-out subject. It is not a replication study, it gives no population inference, and it does not make a
four-subject cohort.

## 2. Sources and their governance

- **The valid User03 export:** `user03_legacy`, seven CSV files, one per night.
  - Minute-resolution timestamps; P1–P6, temperature, humidity and event.
  - It is valid User03 data (D-021).
- **The complementary second-resolution export (seven TXT files, one per night):** the same nights, stored in the
  raw folder `user06_auxiliary`.
  - P0 (A1, D-013, D-017) found every User03 CSV row, row for row, inside these recordings.
  - D-017 excluded the `user06_auxiliary` source as a whole (provider-confirmed setting problem).
  - D-061 narrows that exclusion **for this addendum only**. A TXT row may be used, only as the timestamp source
    (and, for night 7, as a second copy of P1), for a minute whose sensor values are verified identical to the
    valid User03 CSV.
  - Every other use of that folder stays excluded: files outside the seven nights, unmatched minutes, and any use
    of TXT values that are not verified against the CSV.
- **Open item (OPEN-29):** the PI/provider should confirm that the setting problem behind D-017 does not affect the
  TXT timestamps. P9 results are conditional on it.
- **File pairs** (by manifest file id and SHA-256, verified before use): see the config. The nights are labelled 1–7
  in time order; no calendar date enters a committed output.
- **Out of scope:** the TXT files of the earlier nights and of the later partial night, which have no CSV
  counterpart.
- **Raw files** are only read, never modified.

## 3. Parsing

The existing parser (`src/data/raw_parser.py`) is used unchanged.
- **Nights 1–6, TXT:** lines have the form `YYYY-MM-DD HH:MM:SS.<v>,<5 values>,T,H,event`.
  - The five comma-separated pressure values are P2–P6.
  - The value fused to the seconds by `.` is **not** used. Its equality with the CSV P1 is recorded as an audit
    column only.
- **Night 7, TXT:** a regular comma layout with P1–P6.
- **CSV:** rows `YYYY-MM-DD H:MM,P1..P6,T,H,event`.
- **Non-data lines** (controller `[NVS]` lines, crash dumps, device logs) are counted and ignored in both sources.

## 4. Minute reconciliation rule (deterministic)

- **Grouping:** rows are grouped by their minute (TXT timestamp truncated to the minute; CSV minute timestamp).
- **Inclusion:** a minute is included only if **all** of the following hold:
  1. it occurs in exactly one CSV file and exactly one TXT file, and they are the paired night files;
  2. both sources have the same number of data rows (≥ 1) in it;
  3. row i of the CSV and row i of the TXT (file order within the minute) have identical compared fields, for
     every i:
     - nights 1–6: P2–P6, temperature and humidity;
     - night 7: P1–P6, temperature and humidity;
  4. the TXT seconds do not decrease within the minute;
  5. the events agree:
     - identical after removing surrounding whitespace, or
     - identical after keeping only letters, digits and Hangul (**punctuation-only difference**: included and
       flagged).
     - Any other event-text difference excludes the minute. Events are never model inputs.
- **Provider annotation:** the minute containing the provider-annotated error interval of the night-3 TXT file
  (07:20:11–07:20:51) is excluded whatever the checks show.
- **Exclusion categories** (the whole minute is excluded):
  - `csv_only`, `txt_only`, `ambiguous_source`;
  - `count_mismatch`, `value_mismatch`;
  - `txt_time_order_violation`, `event_text_mismatch`;
  - `provider_annotated_error`.
  - They are counted per night in minutes and rows.
- **Reconstructed row:**
  - timestamp = the TXT second-level timestamp, unchanged;
  - P1 = the CSV P1 (nights 1–6), or the CSV P1 verified equal to the TXT P1 (night 7);
  - P2–P6, temperature and humidity = the verified common values;
  - event = the CSV event string (provenance only).
- **Forbidden:**
  - timestamp interpolation;
  - pressure imputation;
  - invented seconds;
  - nearest-neighbour joining.
- **Provenance per row:**
  - the minute and within-minute index;
  - the CSV and TXT file ids and line numbers;
  - the source file SHA-256;
  - `timestamp_source = txt_second`;
  - `fsr1_source` (`csv` or `csv_equals_txt`);
  - the verified field list;
  - the dot-value audit;
  - the event flag.

## 5. Canonical processing and artifact

- **Canonical stream builder:** the reconstructed rows pass through the canonical stream builder
  (`src/data/canonical.py`, `configs/canonical_v1.yaml`), exactly as a second-resolution source would. That applies:
  - exact-copy de-duplication (D-014);
  - sessions (gap > 30 min, D-024);
  - target validity (D-025);
  - pressure validity with 4095 kept (D-018);
  - event redaction.
  - Subject User03, device `unknown`, role `external_validation`.
- **Artifact:** the output is a separate external-validation artifact, never part of canonical_v1:
  - `data/external/p9_user03_v1/`, git-ignored, because it holds timestamps and values;
  - a committed manifest with hashes and counts only.

## 6. Windows (protocol v1.0 rule, unchanged)

- **Window spec:** actual second-level timestamps, 40-s windows, 20-s stride, 8 × 5-s bins, a continuity break for
  inter-row gaps > 5 s, and no invented bins (`src/evaluation/windowing.py`, `protocol.window_spec()`).
- **Grouping:** windows are grouped by subject, device, session, sensor phase, channel-quality phase and partition,
  as in the strict LOSO folds.
- **Nights:** noon to noon.
- **Labels:** a window is labelled if both target validity flags are true at its last step.
- **QA report first:** usable nights and windows, and all exclusions, are written to a QA report
  (`docs/P9_USER03_QA_REPORT.md`) before any model output on User03 is computed.

## 7. Model rule (fixed before any User03 label is evaluated)

- **The selections differ:** the three frozen P3 folds selected different RAW-TCN configurations (fold 1: index 12;
  fold 2: index 7; fold 3: index 8). No User03-free rule picks one of them, so none is chosen.
- **All three are trained,** as source-only sensitivity models:
  - on all labelled windows of User01, User02 and User07 (the union of the P3 outer test windows, the strict LOSO
    window rule);
  - each with its frozen final epoch count and the protocol's training recipe;
  - with a target scaler fitted on those source windows;
  - with seeds 0, 1 and 2, giving nine models.
- **User03's role:** it is used for no fitting, scaling, early stopping, validation or selection.
- **Comparator:** the training-mean predictor (the mean of the labelled source windows).
- **Reporting:** each configuration is reported separately, per seed and as the seed mean. The unweighted mean over
  the three configurations is a descriptive summary, not a selection.

## 8. Metrics (reused definitions)

- **Per target** (`src/evaluation/p8_dynamic.py`, population SDs):
  - MAE, RMSE and signed bias (predicted − observed);
  - R = error SD / target SD and Q = prediction SD / target SD;
  - the pooled Pearson r and the night-centred within-night r;
  - per-night MAE, bias and r (eligibility as in v1.2).
- **Constants:** constant predictors have Q = 0, R = 1 and r = NA.
- **Uncertainty:** if User03 has fewer than 10 usable nights (the P6 minimum), no night-bootstrap interval is
  computed; seed ranges and per-night results are reported instead. With ≥ 10 nights, the P6 night bootstrap
  (2,000 resamples, seed 0) is added.

## 9. Interpretation rules (fixed before the results)

Per target:
- **RAW-TCN better than the training mean:** for **every** configuration, the seed-mean MAE is lower **and** the
  seed-mean per-night MAE is lower on ≥ 2/3 of the usable nights.
- **Training mean better:** the symmetric condition.
- **Otherwise:** mixed.
- **Within-night co-variation supported:** for every configuration, the seed-mean r_within is ≥ 0.10 and the
  seed-mean per-night r is > 0 on ≥ 2/3 of the eligible nights.
- **Within-night co-variation absent:** for every configuration, |seed-mean r_within| < 0.10.
- **Otherwise:** inconclusive.

Relation to the N = 3 findings (a training-mean advantage in strict LOSO for temperature; no consistent within-night
co-variation):
- **strengthened** if, for both targets, the RAW-TCN is not better and within-night co-variation is not supported;
- **weakened** if, for both targets, the RAW-TCN is better or co-variation is supported;
- **mixed** otherwise.

If the RAW-TCN is better or co-variation is supported for a target, every manuscript sentence that states no
pressure-dependent advantage or no within-night co-variation is revised for that target.

## 10. Leakage guards

- User03 rows never enter a training, scaler, selection or early-stopping set; this is checked programmatically.
- The source windows are verified against canonical_v1 (hash) and the v1.0 splits.
- The inputs are RAW only: no control code, calendar field or identifier.
- The User03 windows never cross a session, night or partition boundary.

## 11. Outputs and language

- **Paths:**
  - runs `outputs/runs/p9_user03/`;
  - metrics `outputs/metrics/p9_user03/`;
  - paper tables `paper/tables/p9_user03_*.csv` (no dates, anonymous ids);
  - reports `docs/P9_USER03_QA_REPORT.md` and `docs/P9_USER03_EXTERNAL_VALIDATION_REPORT.md`.
- **Wording:** "additional external validation (post hoc)" or "external sensitivity subject".
- **Never:**
  - "N = 4";
  - "four-subject cohort";
  - "independent replication";
  - population generalization.
