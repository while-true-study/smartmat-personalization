# P0 — Dataset Audit & Data Freeze: Plan

| | |
|---|---|
| Phase | P0 (`RESEARCH_PROTOCOL.md` §5) |
| Branch | `research/p0-data-freeze` |
| Status | **Closed 2026-09-13 (closure gate passed; merge and tag pending PI review)**. A1, A2, A5 (incl. A3, A4), A7, A8, A9, A9b, A10, A11 done; A6, A12 partly; A13 not needed for the frozen policies. Canonical interim dataset v1 built (D-028). Final report: `docs/P0_DATASET_AUDIT_REPORT.md` |
| Starting point | `docs/initial_dataset_inventory.md` |
| Decisions | Open items in `docs/DECISIONS.md` (OPEN-xx); P0 start: D-012; User06 source excluded: D-017 (supersedes D-013); User01 `sensor_phase`: D-019; primary cohort User01/User02/User07: D-020; User03 legacy valid auxiliary: D-021; 22482 `channel_quality_phase`: D-022; P0 closure: D-014 and D-018 accepted, D-023 … D-028 |

## Goal

raw data → provenance audit → canonical subject/device mapping → data-quality audit → cohort decision →
data freeze.

P0 does not aim at model performance. Every P0 decision must be justified by provenance or data quality,
never by expected model results.

## Not allowed in P0

Model training · window generation · resampling · interpolation · normalisation · LOSO or personalization
split generation · movement/contact feature extraction · hyperparameter search.
Raw data stay read-only (`DATA_POLICY.md` §1).

## Working rules

- All analyses are **descriptive**, read raw data only through `src/`, and write only under
  `outputs/qa/p0/<analysis>/` (regenerable, not committed). Findings that support a decision are
  summarised in `docs/P0_DATASET_AUDIT_REPORT.md` (created during P0).
- Every threshold (gap length, glitch range, co-occupancy rule) is reported as a sensitivity sweep, and
  the value chosen later is justified in a decision entry.
- Analyses are implemented as functions in `src/data/` or `src/qa/` with tests, and are called from
  `scripts/`. Integrity checks (manifest SHA-256) run first; a mismatch stops the script.
- One-off checks from the inventory (User03/User06 containment, User02 co-occupancy) are
  re-implemented as reproducible code (A1, A2).

## Analyses

Order of execution: A1, A2 (identity) → A5, A3, A4 (duplication) → A6, A7 (time) → A8, A9, A10
(quality) → A13 → A11, A12 (coverage and target distributions).

### A1. Cross-subject duplicate / provenance analysis — **done (2026-09-12)**
- **Purpose:** Establish whether any recording appears under more than one subject ID (known case:
  User03 ⊂ User06), and rule it out for all other subject pairs.
- **Input:** All sensor files in the manifest; parsed rows (`src/data/raw_parser.py`).
- **Method:** Row fingerprints at three resolutions: exact timestamp, minute-truncated timestamp, and
  pressure-only fingerprint (timestamp and P1–P6, ignoring T/H/event). For every ordered pair of sources,
  compute containment in both directions, per date. For matching dates, check row-by-row sequence
  alignment and characterise the transformation (truncated seconds, changed separators, dropped rows,
  file-boundary shifts). Negative control: source pairs with no expected relation (e.g. User02 legacy vs User06).
- **As implemented:** the third mode became a timestamp-free 5-row value sequence over all common channels
  (P1–P6, temp, humid) instead of a pressure-only row fingerprint with timestamp, so that re-dated copies are
  also detected. Matches are split into informative (pressure > 0) and empty-mat rows. Comparisons run on
  all 10 subject pairs and all 45 source pairs. Code: `src/data/provenance.py`,
  `scripts/audit_cross_subject_provenance.py`; tests: `tests/test_provenance.py`.
- **Artifacts:** `outputs/qa/p0/provenance/cross_subject_provenance_summary.csv`, `…_by_date.csv`,
  `…_by_source.csv`, `cross_subject_file_correspondence.csv`; report `docs/P0_A1_PROVENANCE_REPORT.md`.
- **Result:** only User03 – User06 overlaps (User03: 100 % in minute and sequence modes); all other pairs share
  nothing. OPEN-01 remains unresolved pending provider confirmation.
- **Decision it may influence:** OPEN-01 (which subject ID and source survive), OPEN-13, OPEN-16,
  leakage rule L7.

### A2. User02 device overlap — **done (2026-09-12)**
- **Purpose:** Characterise the concurrent recording of mats 22480 and 22482 and test the device
  attribution of the two quarantined files.
- **Input:** `user02_mat_22480`, `user02_mat_22482`, `user02_mat_22480_prefix_mismatch`.
- **Method:** Minute-level joint coverage; co-occupancy under two occupancy definitions (firmware
  label ≠ `NM`; pressure-sum threshold sweep); lagged cross-correlation of pressure-sum changes between
  devices (simultaneous movement on both mats suggests one body on both); same-minute T/H differences;
  hour-of-day coverage. Device signature (T/H level, pressure range, recording hours) of the quarantined
  files compared with 22480 and 22482 over neighbouring dates.
- **Expected artifact:** `outputs/qa/p0/user02_devices/joint_coverage.csv`, `co_occupancy.csv`,
  `movement_xcorr.csv`, `quarantine_attribution.csv`.
- **As implemented:**
  - Coverage uses a per-second grid with coverage gap rules of 10/60/300 s.
  - Cross-device comparisons pair existing rows by nearest timestamp (exact / ±1 / ±3 s), with no resampling.
  - Pressure coupling is tested by correlation at lag 0 and over −30…+30 s with ±24 h controls, by
    movement-event coincidence, and by a supplementary ±12 h clock-offset scan (pooled and per date).
  - Occupancy is evaluated under 14 definitions.
  - T/H is compared on paired rows, per date, and with the inventory's per-minute method.
  - Device distributions and a rule-based evidence table for the quarantined files are produced.
  - Code: `src/data/device_overlap.py`, `scripts/audit_user02_devices.py`; tests: `tests/test_device_overlap.py`.
- **Artifacts:** `outputs/qa/p0/user02_devices/` (`device_summary.csv`, `temporal_overlap.csv`,
  `aligned_device_comparison.csv`, `lagged_correlation.csv`, `event_lag_scan*.csv`, `daily_th_difference.csv`,
  `occupancy_sensitivity.csv`, `device_distributions.csv`, `daily_device_profile.csv`,
  `prefix_mismatch_evidence.csv`); report `docs/P0_A2_USER02_DEVICE_REPORT.md`.
- **Result:**
  - 253 h of simultaneous recording, but no pressure or occupancy coupling between the mats.
  - Persistent T/H offset (−2 °C / −19 %RH) and different channel-load patterns: device behaves as a domain
    factor within User02.
  - Quarantined files: strong evidence for 22482, still unresolved.
  - OPEN-02/03 remain open pending the provider.
- **Decision it may influence:** OPEN-02, OPEN-03 (use of two streams), L8 grouping, User02 inclusion
  in the primary cohort.

### A3. Duplicate rows — **done within A5 (2026-09-12)**
- **Purpose:** Quantify exact duplicate rows within files and where they occur.
- **Input:** Parsed rows per file.
- **Method:** Count exact duplicates (all fields), split into consecutive vs non-consecutive, and locate
  them relative to upload-chunk boundaries and file boundaries; by source and firmware period.
- **Expected artifact:** `outputs/qa/p0/duplicates/within_file_duplicates.csv`.
- **Decision it may influence:** OPEN-07 (de-duplication rule).

### A4. Duplicate timestamps — **done within A5 (2026-09-12)**
- **Purpose:** Distinguish harmless repeated rows from conflicting records sharing one timestamp.
- **Input:** Parsed rows per subject-device timeline.
- **Method:** For each repeated timestamp, classify as identical content, same T/H but different pressure,
  or different T/H. Treat minute-resolution legacy sources separately (ties are expected there).
- **Expected artifact:** `outputs/qa/p0/duplicates/timestamp_conflicts.csv`.
- **Decision it may influence:** OPEN-07, OPEN-08.

### A5. Cross-file overlaps — **done (2026-09-12)**
- **Purpose:** Map how adjacent daily files repeat upload chunks, and whether overlapping content is
  always identical.
- **Input:** Parsed rows with JSON chunk keys; `cross_file_time_overlap.csv` from the inventory audit.
- **Method:** Chunk-key index across files (key → files containing it); compare overlapping chunks
  row by row; flag any overlap with conflicting values. Count rows that each candidate de-duplication
  rule would keep or drop (counting only — no interim data are written).
- **Expected artifact:** `outputs/qa/p0/overlaps/chunk_index.csv`, `overlap_conflicts.csv`,
  `dedup_rule_counts.csv`.
- **As implemented (covers A3 and A4):**
  - Relations R1–R5 are kept apart per subject + device group: exact duplicates (all fields),
    metadata-only differences, conflicting timestamps (classified by origin, adjacency, sentinel and control
    event), repeated sequences (between files and within a file) and time overlap without shared rows.
  - Also produced: every time-overlapping file pair, repeated upload-chunk keys, file-boundary gap bins, a
    cross-device diagnostic, and simulated policy impacts A1/A/B/C.
  - Code: `src/data/duplicates.py`, `scripts/audit_cross_file_duplicates.py`; tests: `tests/test_duplicates.py`.
- **Artifacts:** `outputs/qa/p0/duplicates/`; report `docs/P0_A5_DUPLICATE_OVERLAP_REPORT.md`.
- **Result:**
  - Primary-group overlaps are exact duplicate blocks (187,190 cross-file copies + one 600-row within-file
    block); copies never disagree.
  - 10,997 same-second timestamps with different readings originate inside single files.
  - Source file ≠ session is confirmed.
  - De-duplication proposed as D-014 (Proposed); session threshold not chosen.
- **Decision it may influence:** OPEN-07, OPEN-06.

### A6. Sampling interval distribution — **partly done within A7 (2026-09-12)**
- **Status:** step distributions per primary timeline (and reference groups) are in A7 (3 s nominal, p99 5 s,
  0-s double readings, 6–15 s sample losses).
- **User01 change points: done within A10 (2026-09-13).** Regimes:
  - 2 s in phase_a;
  - 3 s from 2025-11-05;
  - a temporary 2 s regime 2026-01-03…07;
  - 3 s with wider jitter from 2026-01-08;
  - no change at the sensor boundary.
- Still pending: other sources and rows-per-minute for the legacy sources.
- **Purpose:** Describe the real sampling process per source, device and firmware period.
- **Input:** De-duplicated (in memory) subject-device timelines.
- **Method:** Δt histograms and quantiles; rows per minute; change points in the nominal interval
  (e.g. 2 s → 3 s between User01 phase_a and later phases); relation to chunk boundaries.
- **Expected artifact:** `outputs/qa/p0/sampling/interval_distribution.csv`, histogram figures.
- **Decision it may influence:** OPEN-08; input to the resampling decision taken in P2 (not in P0).

### A7. Temporal gap distribution — **done (2026-09-12)**
- **As implemented:**
  - Two timelines per primary subject/device: raw, and an audit-only view without A5's repeated-block copies.
  - Descriptive step classes and 13 gap buckets, upload-chunk alignment (n × 1,800 s ± 10 s) against its
    chance rate, and gap context (file boundary, clock time, pressure/NM, T/H, events).
  - Threshold sweep 1–120 min with and without bridging lost chunks; candidate-session night structure; QA figures.
  - Code: `src/data/temporal.py`, `scripts/audit_temporal_gaps.py`; tests: `tests/test_temporal_gaps.py`.
- **Artifacts:** `outputs/qa/p0/temporal/`; report `docs/P0_A7_TEMPORAL_GAP_REPORT.md`.
- **Result:**
  - Bimodal gaps; 5–90 min plateau for User01/22480/User07.
  - 22482 loses 1–3 upload chunks at morning file cuts (13/13 aligned gaps at file boundaries).
  - Recording is quantised in 30-min chunks.
  - A vs B identical in session structure.
  - Candidate policy D-015 (Proposed): > 30 min, with chunk-aligned 1–3-chunk gaps bridged.
- **Purpose:** Provide the evidence base for a session definition.
- **Input:** De-duplicated subject-device timelines.
- **Method:** Gap-length distribution within and across files; number and length of candidate sessions
  as a function of the gap threshold (sweep, e.g. 1–120 min); gaps against provider annotations
  (e.g. "part missing"); night boundary behaviour (recordings crossing midnight or spanning days).
- **Expected artifact:** `outputs/qa/p0/gaps/gap_distribution.csv`, `session_threshold_sweep.csv`.
- **Decision it may influence:** OPEN-06 (session definition).

### A8. T/H missing / sentinel / glitch — **done (2026-09-13)**
- **As implemented:**
  - Per-channel cause-preserving states on the A5/A7 audit timeline; candidate patterns with counts, dates and
    files.
  - Context of every suspicious row: chunk/file/session position, gap before, same second, control event,
    repeated block, neighbouring valid values.
  - Zero runs split into start sentinels and dropout runs.
  - Jumps between valid observations by Δt class, spikes, constant runs with a sensor-freeze check, per-session
    target statistics.
  - Same-second target conflicts (A5 function) classified; policies A/B/C simulated; distributions by
    device/month; User02 device bias reproduced; flag schema proposed.
  - Code: `src/data/target_quality.py`, `scripts/audit_target_quality.py`; tests: `tests/test_target_quality.py`.
- **Artifacts:** `outputs/qa/p0/target_quality/`; report `docs/P0_A8_TARGET_QUALITY_REPORT.md`.
- **Result:**
  - 0.10 % invalid-candidate targets: start sentinels plus two dropout/glitch episodes.
  - No abrupt jumps within 5 s; same-second target conflicts are ±1 steps or zero-vs-reading.
  - Long constant temperature on 22480 and User07 with humidity still varying.
  - D-016 (Proposed): flag known sentinel/glitch patterns, keep values.
- **Purpose:** Characterise invalid target values before any target is defined.
- **Input:** Parsed rows; chunk keys.
- **Method:** Joint zeros (`temp == 0 and humid == 0`) and their position relative to chunk start;
  out-of-range values; sudden steps between consecutive rows; flat-lines; per-source plausible ranges.
  Each rule reported with counts per source; no values are removed.
- **Expected artifact:** `outputs/qa/p0/targets/th_quality_flags.csv`.
- **Decision it may influence:** OPEN-09 (flagging/exclusion rules), OPEN-10.

### A9. Pressure channel consistency — **done (2026-09-13)**
- **As implemented:**
  - First analysis on analysis-eligible sources only (D-017). The User06 source, quarantined files and
    restricted metadata are not loaded. Excluded sources are listed with their reason.
  - Main groups User01, 22480, 22482, User07 on the A5/A7 audit timeline. User02/User03 legacy are reference
    only.
  - Per channel: statistics per phase, zero and 4095 boundary runs, and constant runs in four cross-channel
    categories (≥ 1 min / 5 min / 30 min / 1 h). Also identical-frame runs, cross-channel shares and
    correlations, and |Δ| ≤ 5 s.
  - Scale by source/month/week/day, with the User01 2026-01-25 sensor change as baseline evidence only.
  - Schema per file; policies A/B/C simulated; flag schema proposed.
  - Code: `src/data/pressure_quality.py`, `scripts/audit_pressure_quality.py`; tests:
    `tests/test_pressure_quality.py`. Parser safeguard: unrecognised layouts are never mapped onto P1–P6.
  - The planned channel-order check using the User03/User06 overlap is dropped: the User06 source is excluded
    (D-017). The `FSR_k` ↔ P_k mapping goes to the provider (OPEN-20).
- **Artifacts:** `outputs/qa/p0/pressure_quality/`; report `docs/P0_A9_PRESSURE_QUALITY_REPORT.md`.
- **Result:**
  - Six populated channels everywhere. No missing channel, non-standard layout or impossible value.
  - 4095 appears only in User01 before the sensor change (plus 17 cells on 22480). All non-zero constant runs are
    4095 plateaus; no stuck channel or frozen frame on the current mats.
  - Sensor change visible as a step. New shift: 22482 P1 from 2026-08-20 (OPEN-19).
  - D-018 (Proposed): input validity from raw layout and encoding only. The stuck heuristic (policy C) is
    rejected: it would remove only User01 4095 plateaus.
- **Purpose:** Check that the six channels are comparable across sources and periods.
- **Input:** Parsed rows.
- **Method:** Per-channel distributions, zero rate, saturation (4095) rate and stuck/constant runs by
  subject, device and period; all-zero-row rates.
- **Expected artifact:** `outputs/qa/p0/pressure_quality/`.
- **Decision it may influence:** OPEN-17, channel inclusion, compatibility of legacy sources.

### A9b. User02 / 22482 P1 channel anomaly — **done (2026-09-13)**
- **As implemented:**
  - Change points on 22482's nightly, session and daily channel summaries without using the A9 date; hourly
    onset; ±1/3/7-night and whole-period comparisons; recovery.
  - Per-channel shift classification; 22480 and T/H as controls; schema/firmware/event timeline; occupancy
    confound; impact.
  - Code: `src/data/channel_anomaly.py`, `scripts/audit_user02_channel_anomaly.py`; tests:
    `tests/test_channel_anomaly.py`.
- **Artifacts:** `outputs/qa/p0/user02_channel_anomaly/`; report `docs/P0_A9B_USER02_CHANNEL_ANOMALY_REPORT.md`.
- **Result:**
  - P1 collapses in the recording of the night 2026-08-19 (onset ≈ 08-20 02:00) and is fully shifted from
    2026-08-20 21:37:33.
  - The change is abrupt, persistent and P1-only; the pressure sum without P1 is stable.
  - There is no concurrent 22480, T/H, schema or firmware change.
  - User02 stays eligible.
  - OPEN-19 closed as class B by D-022 (`channel_quality_phase` / `channel_quality_flag`). The later 22482 P6
    decline (2026-08-25) is an observed distribution shift under OPEN-03.

### A10. User01 sensor phase analysis — **done (2026-09-13)**
- **As implemented:**
  - Per session, night and day: pressure, 4095, active channels, zeros, T/H, sampling, movement labels and
    scale-free activity proxies.
  - Change-point scan without using the known date: robust standardised median differences for windows 1, 3, 7
    and 14; per-metric and consensus ranking with one candidate per event; step vs linear fit.
  - Pre/post comparison over ±1/3/7/14 units, whole periods and placebo windows, with Cliff's δ, Wasserstein and
    KS (no p-values).
  - Channel profiles, 4095 detail, behavioural/T-H confounds, and sampling regimes per day.
  - Comparison at the other candidate events.
  - Code: `src/data/sensor_phase.py`, `scripts/audit_user01_sensor_phase.py`; tests:
    `tests/test_sensor_phase.py`.
- **Artifacts:** `outputs/qa/p0/user01_phase/`; report `docs/P0_A10_USER01_SENSOR_PHASE_REPORT.md`.
- **Result:**
  - The boundary is the 9.4 h gap 2026-01-25 08:07:26 → 17:31:21. It is the strongest change point
    (consensus rank 1 at w = 3 and 7).
  - Nights ±14: complete separation of the 4095 share (16 % → 0), p95 (−51 %) and active channels (+0.9). It is
    a step, not a drift.
  - T/H, duration, clock time and sampling are continuous across it.
  - D-019 (Accepted): `sensor_phase` s1/s2 as a provenance label.
  - Other acquisition changes inside s1 (2025-12-17 activity change at the log-format change; the early-January
    2 s episode): OPEN-21.
  - All 77 of A9's User01 zero runs ≥ 30 min on unloaded channels fall in s1. This is consistent with the
    contact-distribution change (§4 of the report).
- **Purpose:** Measure the effect of known changes in User01's collection: phase_a/b/c, the
  2025-12-17 log-format change, the heating-season start and the 2026-01-25 pressure-sensor replacement.
- **Input:** User01 parsed rows; operational dates from DATA_POLICY §5 / D-008.
- **Method:** Pressure distributions, saturation, occupancy and event rates, and T/H distributions in
  windows before/after each change date (descriptive comparison, no model).
- **Expected artifact:** `outputs/qa/p0/user01_phase/`, figures.
- **Decision it may influence:** OPEN-11, OPEN-14; constraints for the chronological personalization
  design (adaptation vs test spans must not be confounded with a hardware change).

### A11. User / device / date coverage — **done (2026-09-13)**
- **As implemented:**
  - Coverage table per source × sensor phase slice, plus subject, sensor-phase and mat domains. Excluded sources
    are listed with their status and not loaded.
  - Monthly coverage matrix; overlaps on actually recorded days, weeks, months and minutes.
  - Subject × season/quarter/month/phase/device/schema/container/regime matrix.
  - Device evidence found inside the files; hand-over gaps.
  - Structural cohort eligibility and the event timeline, with separate statuses.
  - Code: `src/data/coverage.py`, `scripts/audit_dataset_coverage.py`; tests: `tests/test_coverage.py`. D-019
    phase boundaries now live in `configs/subject_mapping.yaml` (`sensor_phases`).
- **Artifacts:** `outputs/qa/p0/coverage/`; report `docs/P0_A11_COVERAGE_CONFOUNDING_REPORT.md`.
- **Result:**
  - No two primary subjects were recorded at the same time: 0 shared hours; hand-overs of 36 h and 14.5 h.
  - Winter is observed only in User01. Each LOSO fold removes a subject together with a period, a season mix and a
    device/firmware configuration.
  - Hardware IDs exist only for the User02 mats, so mat reuse cannot be checked (OPEN-04: consequences documented).
  - All three primary subjects are `eligible_with_caveat`. D-020 (Accepted) fixes the cohort User01, User02,
    User07 and closes OPEN-16.
  - The 22482 P1 anomaly is not blocking for the cohort; its flag is needed before closure (OPEN-19; short audit
    A9b recommended if the provider cannot answer).
- **Purpose:** Make the subject × device × period × season × firmware structure explicit.
- **Input:** Manifest; de-duplicated timelines.
- **Method:** Calendar coverage per subject-device (hours recorded per night); month/season per
  subject; firmware/log-format family per period; confounding matrix.
- **Expected artifact:** `outputs/qa/p0/coverage/coverage_calendar.csv`, `confounding_matrix.csv`,
  coverage figure.
- **Decision it may influence:** OPEN-04, OPEN-16; scope of P1 domain-shift EDA.

### A12. Target distribution comparison — **partly done within A8 (2026-09-13)**
- **Status:** distributions by subject/device and month, daily and session medians are in A8 §8. Still pending:
  hour-of-day profiles and heater-episode shares.
- **Purpose:** Describe how temperature and humidity differ across subjects, periods and heater states,
  so cohort and target decisions are made knowingly.
- **Input:** Parsed rows with A8 quality flags applied as masks (in memory).
- **Method:** T/H distributions by subject, device, month and hour of day; share of rows in
  heater-control episodes. Descriptive only; no subject is included or excluded because of these
  distributions.
- **Expected artifact:** `outputs/qa/p0/targets/target_distributions.csv`, figures.
- **Decision it may influence:** OPEN-10, OPEN-16; hand-off to P1.

### A13. Legacy timestamp reliability
- **Purpose:** Decide whether minute-resolution legacy sources can be used and how.
- **Input:** `user02_legacy_csv`, `user03_legacy`, and User06 as the parent log of User03.
- **Note (D-017):** the User06 source is now `excluded_invalid`. Using it only as a reference for how the legacy
  export transformed timestamps would be a provenance-QA use, not an analysis of User06. Confirm this use (or
  drop it) before A13 runs.
- **Method:** Use the User03 ↔ User06 alignment as ground truth for the export transformation (seconds
  truncation, row order, dropped rows); check whether within-minute order preserves time order; estimate
  achievable time resolution for User02 legacy, which has no parent log.
- **Expected artifact:** `outputs/qa/p0/legacy/timestamp_reliability.csv`.
- **Decision it may influence:** OPEN-08, OPEN-13 (use of auxiliary legacy data).

## Clarifications needed from the data provider

Tracked as issue drafts in `docs/issues/` (to be filed on GitHub):
1. ~~Relation between User03 legacy and User06 (OPEN-01)~~ — resolved 2026-09-13 (D-017): the User06 source is
   invalid and excluded. User03 legacy is valid auxiliary data (PI, D-021).
2. User02 dual-device recording protocol and the two quarantined files (OPEN-02, OPEN-03) —
   `P0-02_user02-dual-device-protocol.md`.
3. Device IDs of all other sources (OPEN-04) and metadata date inconsistencies (OPEN-14).
4. Upload/export mechanics (A5, A7; OPEN-06, OPEN-07):
   - Are recordings stored and uploaded only as whole 30-minute chunks?
   - Why are 1–3 chunks lost at the morning file cuts of 22482?
   - Why do adjacent daily exports repeat chunks?
   - What causes the recurring ≈ 2-minute logging pauses?
5. Pressure hardware (A9; OPEN-17, OPEN-19, OPEN-20):
   - Is 4095 ADC clipping or a firmware cap, and does the new sensor use the same range?
   - Was mat 22482 moved, replaced or damaged around 2026-08-20 (P1 nearly silent afterwards)?
   - What is the physical position of P1–P6, and does `FSR_k` in the legacy CSVs equal P_k?
6. User01 collection history (A10; OPEN-21, OPEN-17):
   - Which sensor model and range were used before and after 2026-01-25?
   - Did the 2025-12-17 log-format/firmware change also change pressure reporting (threshold, filtering)?
   - Why was the sampling at 2 s on 2026-01-03…07?
7. Mat identity (A11; OPEN-04): which physical mat recorded User01 and User07? Was any mat reused across
   participants (hand-overs of 36 h and 14.5 h)?

## Exit criteria (data freeze)

Status at P0 closure (2026-09-13). Evidence is in `docs/P0_DATASET_AUDIT_REPORT.md` and D-023 … D-028.

- [x] OPEN-01, -02, -03 resolved, or the affected data excluded by a decision entry: OPEN-01 by D-017; OPEN-02
  quarantined and excluded from canonical_v1 (D-006, D-023); OPEN-03, P0 part, by D-027.
- [x] OPEN-04 answered, or its consequences for RQ1 documented: consequences documented (A11 §3, §5); the
  provider question is deferred as non-blocking.
- [x] OPEN-05, -06, -07, -08, -09, -12, -13, -16 decided:
  - OPEN-05: D-005;
  - OPEN-06: D-024;
  - OPEN-07: D-014;
  - OPEN-08: D-026;
  - OPEN-09: D-025;
  - OPEN-12: moot, closed;
  - OPEN-13: D-023;
  - OPEN-16: D-020.
- [x] OPEN-14 deferred to P1/P2 as non-blocking. *Amendment at closure:* the criterion listed OPEN-14 as a P0
  decision, but no frozen P0 policy depends on the metadata dates, and the one date that matters (the sensor
  change) is confirmed by data (D-019).
- [x] Pressure input-validity rule decided (D-018, accepted). OPEN-19 closed by D-022. OPEN-20 consequences
  documented (A9); it is needed only for spatial features (P2).
- [x] Canonical interim dataset v1 built under `data/interim/canonical_v1/` from the accepted rules: parsed,
  de-duplicated, provenance columns (incl. `sensor_phase`, `channel_quality_phase`/`channel_quality_flag`),
  quality flags; **no** resampling, interpolation or normalisation (D-028).
- [x] Interim dataset manifests with content and file SHA-256 committed (`data/interim/manifest/canonical_v1_*`);
  raw integrity verified.
- [x] `docs/P0_DATASET_AUDIT_REPORT.md` written; README roadmap updated.
- [ ] Tests pass (done); PR merged into `main`; tag `p0-data-freeze` created on the merge commit. The merge and
  tag are pending the PI's review and are not done by the build.

### Closure gate (2026-09-13)

| Gate | Status | Evidence |
|---|---|---|
| canonical cohort frozen | pass | D-020, D-023 |
| excluded / quarantine policy frozen | pass | D-017, D-006, D-023 |
| duplicate policy frozen | pass | D-014 (accepted) |
| session policy frozen | pass | D-024 |
| timestamp policy frozen | pass | D-026 |
| target quality policy frozen | pass | D-025 |
| pressure validity policy frozen | pass | D-018 (accepted) |
| User01 sensor phase frozen | pass | D-019 |
| 22482 channel-quality phase frozen | pass | D-022 |
| auxiliary policy frozen | pass | D-023 |
| canonical interim v1 built | pass | `canonical_v1_content.json`; two identical builds |
| manifest reconciliation passed | pass | `canonical_v1_summary.csv` (build fails otherwise) |
| tests passed | pass | full suite |
| raw integrity passed | pass | 377 files, SHA-256 and mtime unchanged |
| no private identifiers | pass | privacy / absolute-path scan of committed files and manifests |
| P0 final report written | pass | `docs/P0_DATASET_AUDIT_REPORT.md` |

### Handoff

- P1 and P2 read canonical_v1, never raw.
- Non-blocking open items move on:
  - OPEN-04, OPEN-14 (P1/P2 interpretation);
  - OPEN-10, OPEN-11, OPEN-15, OPEN-17, OPEN-20, OPEN-21 (P2);
  - OPEN-18 (P7);
  - the cause of the 22482 P1 shift (provider).
- The analyses A6 (legacy rows per minute), A12 (hour-of-day, heater episodes) and A13 (legacy timestamps) are
  not needed for the frozen policies. A12 moves to P1 EDA; A13 is needed only if a secondary protocol uses
  auxiliary data.