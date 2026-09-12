# P0-A1 — Cross-subject Provenance Analysis

| | |
|---|---|
| Phase / analysis | P0 — Dataset Audit & Data Freeze / A1 (`docs/P0_DATASET_AUDIT_PLAN.md`) |
| Date | 2026-09-12 |
| Code | `src/data/provenance.py` (analysis), `scripts/audit_cross_subject_provenance.py` (I/O, tables) |
| Tests | `tests/test_provenance.py` (synthetic fixtures only) |
| Command | `python scripts/audit_cross_subject_provenance.py` (≈ 3.5 min) |
| Input | 373 sensor files from the raw manifest (SHA-256 `dcf25e98b7d6f3a7…`); raw integrity verified before the run |
| Parameters | k = 5 rows per value sequence; flag thresholds: ≥ 10 informative matches or ordered run ≥ 10 |
| Artifacts | `outputs/qa/p0/provenance/` — `cross_subject_provenance_summary.csv`, `cross_subject_provenance_by_date.csv`, `cross_subject_provenance_by_source.csv`, `cross_subject_file_correspondence.csv`, `provenance_tables.md`, `provenance_run_meta.json` (regenerable, not committed; `CONVENTIONS.md` §5) |

This analysis quantifies evidence. It does not change the subject mapping, remove or merge rows, or decide
which data are used.

---

## 1. Purpose

The initial inventory found, in a one-off check, that the rows of `user03_legacy` also occur in
`user06_auxiliary` (OPEN-01). A1 turns that observation into a reproducible measurement and asks the same
question for **every** pair of subjects:

> Does any recording appear under more than one subject ID?

## 2. Method

**Scope.** All 10 sensor sources (4,688,889 parsed rows) grouped into the 5 subjects defined in
`configs/subject_mapping.yaml`. All of User02's sources, including the quarantined files, are pooled under
User02; device IDs are never treated as subjects. Restricted metadata are not sensor data and are excluded.
Rows are parsed by the existing read-only parser (`src/data/raw_parser.py`). Timestamps and values are never
modified; fingerprints are analysis keys only.

**Comparable channels.** Each comparison uses the channels present in both sides. All sources have
`P1–P6, temp, humid`, so every comparison uses these 8 channels. If a source lacked a channel (e.g. a 5-channel
schema), the code would compare only the common subset and report it in `channels_used`.

**Three comparison modes.**

| Mode | Fingerprint of a row | Detects |
|---|---|---|
| A `exact_ts_values` | parsed timestamp (1 s) + 8 channel values | verbatim copies |
| B `minute_ts_values` | timestamp floored to the minute + 8 channel values | copies whose seconds were dropped (legacy CSV exports) |
| C `value_sequence` | 5 consecutive rows of 8 channel values, **no timestamp** | copies that were re-dated or time-shifted |

**Guarding against coincidental matches.** Independent mats can produce identical rows, e.g. an empty mat
(all pressures 0) with the same room temperature at the same minute. Therefore:
- a row is *informative* when its pressure sum is > 0; matches are reported both in total and as
  `informative_matched_*`;
- mode C uses only 5-row sequences whose rows are all informative and not all identical;
- a cross-subject pair is **flagged** only if a mode has ≥ 10 informative matches or an ordered run ≥ 10 rows.

**Metrics** (per pair and mode): comparable and matched rows on each side (set membership: a row matches if
its fingerprint occurs anywhere on the other side), match ratios, dates with data on both sides
(`co_covered_dates`), dates with matches, first/last matched time, the longest run of consecutive matched rows,
and the **longest ordered run**: the longest block of consecutive informative rows that also appear
consecutively and in the same order on the other side. Time offset (`other − this`) is computed only where the
fingerprint occurs exactly once on the other side. For flagged pairs, each file is aligned to its
best-matching file on the other side, with unmatched rows split into leading / trailing / interior.

**Pair scope.** Pairs of sources of the same subject (e.g. User02 devices 22480 and 22482) are labelled
`same_subject` and are never flagged as cross-subject conflicts; they are reported separately (§5).

Hash collisions: 64-bit fingerprints over ≈ 5 × 10⁶ items give a collision probability of order 10⁻⁶ per run.

## 3. Results — all subject pairs

10 subject pairs × 3 modes. Counts are rows (modes A, B) or valid 5-row sequences (mode C).

| Subject pair | Dates with data on both sides | Mode A matched (a / b) | Mode B matched (a / b) | Mode C matched (a / b) | Flagged |
|---|---|---|---|---|---|
| User01 – User02 | 0 | 0 / 0 | 0 / 0 | 0 / 0 | no |
| User01 – User03 | 0 | 0 / 0 | 0 / 0 | 0 / 0 | no |
| User01 – User06 | 0 | 0 / 0 | 0 / 0 | 0 / 0 | no |
| User01 – User07 | 0 | 0 / 0 | 0 / 0 | 0 / 0 | no |
| User02 – User03 | 7 | 0 / 0 | 0 / 0 | 0 / 0 | no |
| User02 – User06 | 8 | 0 / 0 | 0 / 0 | 0 / 0 | no |
| User02 – User07 | 1 | 0 / 0 | 0 / 0 | 0 / 0 | no |
| **User03 – User06** | **8** | **11,732 / 1,831** | **107,256 / 107,300** | **73,048 / 73,048** | **yes** |
| User03 – User07 | 0 | 0 / 0 | 0 / 0 | 0 / 0 | no |
| User06 – User07 | 0 | 0 / 0 | 0 / 0 | 0 / 0 | no |

- **Exactly one pair is flagged: User03 – User06.** The other nine pairs have zero matches in every mode,
  including mode C, which does not depend on timestamps or on year inference.
- Three of the nine pairs were recorded on the same dates (User02 – User03: 7 dates, User02 – User06: 8,
  User02 – User07: 1), yet share nothing. They act as negative controls: recordings made at the same time
  and with the same export format do not produce spurious matches under these fingerprints.

## 4. User03 legacy ↔ User06 in detail

### 4.1 Pair-level results

| Mode | Comparable (User03 / User06) | Matched (User03 / User06) | Ratio User03 | Ratio User06 | Informative matched | Longest ordered run | Offset User06 − User03 |
|---|---|---|---|---|---|---|---|
| A exact | 107,256 / 164,185 | 11,732 / 1,831 | 10.94 % | 1.12 % | 4,007 / 1,400 | 1 | 0 s |
| B minute | 107,256 / 164,185 | 107,256 / 107,300 | **100.00 %** | 65.35 % | 82,172 / 82,172 | 14,218 | 0 … 59 s, median 29 s |
| C sequence | 73,048 / 93,806 | 73,048 / 73,048 | **100.00 %** | 77.87 % | 73,048 / 73,048 | 13,180 | 0 … 59 s, median 29 s |

Reading the three modes together:
- **Mode A is low, mode B is 100 %.** Exact timestamps match only for User06 rows that happened to fall on
  second :00; once seconds are dropped, every User03 row has a counterpart in User06.
- **The offset is always 0–59 s** (62,760 unambiguous row matches in mode B, 72,672 sequence matches in mode C).
  This is the signature of timestamps truncated to the minute, and nothing else.
- **Mode C is also 100 %.** Every valid 5-row value sequence of User03 appears in User06, so the match does not
  depend on timestamps.
- **Order is preserved over long stretches.** Up to 13,180 consecutive sequences (one entire night file) appear
  in the same order in both sources. Coincidence cannot produce this.

### 4.2 By date (mode B)

| Date | User03 rows | User06 rows | User03 matched | User06 matched | Ratio User03 | Ratio User06 |
|---|---|---|---|---|---|---|
| 2025-10-06 | 3,890 | 14,476 | 3,890 | 3,890 | 100 % | 26.9 % |
| 2025-10-07 | 18,281 | 19,317 | 18,281 | 18,285 | 100 % | 94.7 % |
| 2025-10-08 | 15,611 | 19,555 | 15,611 | 15,641 | 100 % | 80.0 % |
| 2025-10-09 | 14,080 | 14,511 | 14,080 | 14,080 | 100 % | 97.0 % |
| 2025-10-10 | 15,551 | 15,735 | 15,551 | 15,558 | 100 % | 98.9 % |
| 2025-10-11 | 14,000 | 14,000 | 14,000 | 14,000 | 100 % | 100 % |
| 2025-10-12 | 15,286 | 15,548 | 15,286 | 15,289 | 100 % | 98.3 % |
| 2025-10-13 | 10,557 | 10,557 | 10,557 | 10,557 | 100 % | 100 % |

User06 also has 2025-10-03…10-05 and the early hours of 10-14, where User03 has no data (0 % shared). The low
User06 ratio on 10-06 comes from the preceding night (10-05 → 10-06), which exists only in User06.

### 4.3 File-to-file correspondence

Each User03 file corresponds to exactly **one** User06 file, of the same night:

| User03 file (night) | User03 span | User06 span | User03 rows found | User06 rows unmatched: leading / trailing / interior (mode B) | Interior unmatched (mode C) |
|---|---|---|---|---|---|
| 2025-10-06 | 21:33 → 09:35 | 21:33:23 → 10:13:20 | 19,024 / 19,024 | 0 / 1,023 / 9 | 0 |
| 2025-10-07 | 21:59 → 07:16 | 21:59:41 → 09:18:46 | 14,518 / 14,518 | 0 / 2,950 / 1 | 0 |
| 2025-10-08 | 20:42 → 07:20 | 20:00:51 → 07:38:24 | 13,402 / 13,402 | 962 / 431 / 1 | 0 |
| 2025-10-09 | 19:56 → 09:14 | 19:56:33 → 09:14:09 | 15,717 / 15,717 | 0 / 0 / 0 | 0 |
| 2025-10-10 | 19:57 → 09:58 | 19:47:21 → 09:58:36 | 15,076 / 15,076 | 176 / 0 / 1 | 0 |
| 2025-10-11 | 20:50 → 09:33 | 20:50:00 → 09:33:20 | 14,531 / 14,531 | 0 / 0 / 0 | 0 |
| 2025-10-12 | 20:17 → 09:15 | 20:04:27 → 09:15:51 | 14,988 / 14,988 | 258 / 0 / 1 | 0 |

The rows of User06 that are missing from User03 lie at the start or end of a night. In mode C no User06
sequence inside a User03 time span is missing. In data terms, each User03 file is a contiguous excerpt of one
User06 night file, with the seconds dropped. The 1–9 interior mode-B differences are User06 rows that are
not part of any valid 5-row sequence (mode C shows no interior gaps); they are not investigated further here.

### 4.4 Interpretation (data evidence only)

**The observed overlap is inconsistent with treating the two sources as independent subject recordings.**
In sensor terms, `user03_legacy` contains no row that is absent from `user06_auxiliary`. The data are consistent
with User03 legacy being a minute-resolution export of part of the User06 device logs.

What the data cannot establish is whose recording it is. Both sources may be the same person under two IDs, one
folder may be mislabelled, or the export may have been filed under the wrong subject. **Identity requires
confirmation by the data provider** (issue draft `docs/issues/P0-01_user03-user06-provenance.md`).

Side findings:
- The User03 export carries its own `FSR1` column and matches User06 rows parsed with `.` as the delimiter
  before P1. This independently supports that reading of User06 files 1003–1011 (OPEN-12).
- One User03 row (2025-10-11 05:02) has the event text `우로이동` where the matching User06 row has
  `우로이동.`. The export apparently normalised the event text. Event text is not part of the fingerprint.

## 5. Same-subject source pairs (not provenance conflicts)

Reported for completeness from `cross_subject_provenance_by_source.csv` (scope `same_subject`):

| Source pair | Dates with data on both sides | Shared rows / sequences | Note |
|---|---|---|---|
| User01 `phase_b` ↔ `phase_c` | 1 | 5,994 rows (modes A and B), 5,306 sequences (mode C) | Known file-boundary overlap (`1231` ↔ `0101`, inventory §7.2); de-duplication belongs to A5/OPEN-07 |
| User02 `mat_22480` ↔ `mat_22482` | 46 | 0 in every mode | The two devices record at the same time, but neither stream is a copy of the other |
| User02 quarantined ↔ `mat_22480` / `mat_22482` | 3 / 2 | 0 in every mode | The two quarantined files duplicate neither device's files (OPEN-02 remains an attribution question) |

All other same-subject source pairs (User01 phase_a with phase_b/c; User02 legacy with the mats) share
nothing. Overlaps between files **within** one source (adjacent daily files) are outside A1 and belong to A5.

## 6. Additional suspicious pairs

**None.** Apart from User03 – User06, no subject pair and no cross-subject source pair (36 cross-subject
source pairs out of 45 source pairs examined) reaches the flag thresholds; all have zero matches in all
three modes.

## 7. Reconciliation with the initial inventory

| Inventory statement | A1 result | Explanation |
|---|---|---|
| 1,831 identical rows shared between User03 and User06 files (exact comparison) | Mode A, User06 side: 1,831 | Identical. On the User03 side 11,732 rows match, because several User03 rows can share one minute-level timestamp and one set of values |
| 99.99–100 % of User03 rows found in User06 per file | 100 % for every file | The one-off check also compared the event text; one row differs only by a trailing `.` in User06 (§4.4) |
| User03 ⊂ User06 for 2025-10-06…10-12 | Confirmed, plus the morning of 10-13 (end of the 10-12 night) | Same data; the inventory counted nights, A1 counts calendar dates |

No inventory figure had to be revised.

## 8. Limitations

- **Transformations not covered.** The fingerprints detect verbatim copies, second truncation and time shifts.
  A copy with rescaled or recalibrated values, resampled rows, or reordered channels would not be detected.
- **Empty-mat periods.** About 23 % of User03 rows have zero pressure. Their correspondence rests on mode B
  (timestamp + T/H), not on the stronger sequence evidence.
- **Year inference.** Modes A and B use inferred years for `MM-DD` rows (D-007). Mode C does not use
  timestamps, so the "no other pair matches" result does not depend on year inference.
- **Set membership.** Ratios count rows whose fingerprint occurs on the other side, not one-to-one pairings.
  A multiset check for User03 gave the same 100 %.
- **Flag thresholds are heuristic** (≥ 10 informative matches or ordered run ≥ 10). The unflagged pairs have
  zero matches, so the conclusion does not depend on them.
- **Scope.** Only data inside this package are compared. Copies of these recordings elsewhere, or identity
  information outside the sensor data, are out of reach.

## 9. Impact on P0

- **OPEN-01** now has reproducible, quantitative evidence and remains unresolved pending provider
  confirmation. Rule L7 applies: the shared recording must never enter an analysis twice. Until resolution,
  neither User03 nor User06 is used beyond provenance/QA analyses.
- **Auxiliary pool.** Whatever the identity answer, the auxiliary sources contain at most two independent
  recording streams from October 2025 (User02 legacy and the User03/User06 recording), not three (OPEN-13).
- **Primary candidates.** User01, User02 and User07 share no recordings with each other or with any auxiliary
  source. Nothing in A1 blocks them.
- **OPEN-12.** A1 adds independent support for reading `.` as the delimiter in User06 files 1003–1011.
- **A13 (legacy timestamp reliability)** can use the User03 ↔ User06 alignment as ground truth for how the
  legacy export transformed the data.
- **OPEN-02 / OPEN-03.** The User02 devices and the quarantined files share no rows. This excludes duplication
  but leaves device attribution and recording setup open.

## 10. Not yet decidable

- Whether User03 and User06 are the same person, and which subject ID the shared recording should carry.
- Whether User06's extra recordings (nights starting 2025-10-03…10-05 and the early hours of 10-14) belong
  to the same person as the shared nights.
- Whether User03 legacy has any use at all, given that its sensor content is a lower-resolution subset of
  User06 (a data-policy decision, after provider confirmation).
- Whether User06 (or the shared recording) enters any training pool (OPEN-13, OPEN-16).

## 11. Reproduce

```bash
python scripts/build_manifest.py                    # verifies raw against the committed manifest
python scripts/audit_cross_subject_provenance.py    # writes outputs/qa/p0/provenance/
python -m pytest tests/test_provenance.py
```
