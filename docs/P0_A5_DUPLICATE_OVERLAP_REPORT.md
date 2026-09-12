# P0-A5 — Cross-file Duplicate & Temporal Overlap Audit

| | |
|---|---|
| Phase / analysis | P0 — Dataset Audit & Data Freeze / A5 (`docs/P0_DATASET_AUDIT_PLAN.md`; also covers A3 and A4) |
| Date | 2026-09-12 |
| Code | `src/data/duplicates.py` (analysis; reuses `src/data/provenance.py` fingerprints and run alignment), `scripts/audit_cross_file_duplicates.py` |
| Tests | `tests/test_duplicates.py` (synthetic log text only) |
| Command | `python scripts/audit_cross_file_duplicates.py` (≈ 1 min) |
| Artifacts | `outputs/qa/p0/duplicates/` — `duplicate_summary.csv`, `file_ranges.csv`, `overlapping_file_pairs.csv`, `duplicate_sequences.csv`, `timestamp_conflicts.csv`, `metadata_only_differences.csv`, `dedup_policy_impact.csv`, `file_boundaries.csv`, `repeated_chunk_keys.csv`, `cross_device_diagnostic.csv` (regenerable, not committed) |

Evidence only. No row was removed, re-timed or merged, and no interim dataset was produced. Policies are
simulated as row counts.

## 1. Purpose

Adjacent raw files repeat parts of each other. A5 describes exactly what repeats, whether repeated records ever
disagree, how much a duplicate-removal rule would remove, and what the file structure implies for sessions.
The results feed OPEN-07 (de-duplication) and OPEN-06 (sessions).

## 2. Definitions

All comparisons stay inside one **subject + device** group from `configs/subject_mapping.yaml`. User02's devices
22480, 22482 and the quarantined files are separate groups. Cross-subject overlap is A1's topic.

| Relation | Definition |
|---|---|
| R1 exact duplicate | same timestamp, P1–P6, temp, humid **and** event text |
| R2 metadata-only difference | same timestamp and sensor/target values, different event text |
| R3 conflicting timestamp | same timestamp, different sensor/target values |
| R4 repeated sequence | ≥ 10 consecutive rows occur in the same order in two files (or twice in one file) |
| R5 time overlap only | two files' time ranges intersect but share no rows |

Each row keeps its provenance (file, original line number, JSON upload-chunk key).

## 3. Results by subject/device

4,688,889 raw rows in total. The four second-resolution primary groups hold 4,323,873 of them.

| Group | Raw rows | R1 exact dup. (ratio) | across files / within file | R2 | R3 conflicting ts | Overlapping file pairs | Longest repeated sequence |
|---|---|---|---|---|---|---|---|
| **User01** | 2,248,820 | 96,670 (4.30 %) | 96,614 / 56 | 1 | 3,992 | 10 (all duplicate blocks) | 16,204 rows, 13.5 h (`0117` → `0118`) |
| **User02 · 22480** | 431,471 | 33,023 (7.65 %) | 33,006 / 17 | 0 | 992 | 4 (all duplicate blocks) | 13,803 rows, 30.3 h (`0822` → `0823`) |
| **User02 · 22482** | 635,126 | 40,914 (6.44 %) | 40,210 / 704 | 3 | 1,225 | 4 (all duplicate blocks) | 21,606 rows, 34.5 h (`0822` → `0823`) |
| **User07** | 1,008,456 | 17,455 (1.73 %) | 17,360 / 95 | 0 | 4,788 | 2 (all duplicate blocks) | 11,600 rows, 11.0 h (`0703` → `0704`) |
| User02 · quarantined | 22,205 | 3 | 0 / 3 | 0 | 36 | 0 | — |
| User06 | 164,185 | 4 | 0 / 4 | 0 | 1 | 0 | — |
| User02 legacy (minute res.) | 71,370 | 14,839 | 0 / 14,839 | 29 | 3,012 | 0 | — |
| User03 legacy (minute res.) | 107,256 | 37,655 | 0 / 37,655 | 144 | 4,885 | 0 | — |

- **Every overlapping file pair in the primary groups is a duplicate block.** No partial overlaps and no R5
  "time overlap only" pairs exist. Duplicated recording time: User01 89.0 h, 22480 40.3 h, 22482 57.6 h
  (incl. the within-file block), User07 16.5 h.
- **All 300 upload-chunk keys that occur in more than one file have identical content** (User01 173, 22480 43,
  22482 51, User07 33).
- **Within-file exact duplicates** are of two kinds:
  - 272 same-second identical rows directly following their twin (User01 56, 22480 17, 22482 104, User07 95);
  - one 600-row upload chunk written twice inside `sm22482_0816.txt` (lines 10,879 and 11,483). This explains
    the 1,797 s backward time step reported in the inventory.
- **Minute-resolution legacy sources** (User02 legacy, User03) show many "duplicates" and "conflicts" because
  20–24 rows share each minute timestamp. These are expected and are not treated as duplication (§6).
- **Cross-device diagnostic (User02):** 22480, 22482 and the quarantined files share 0 sensor/target rows with each
  other. Shared *timestamps* (simultaneous recording, A2) are not duplicates and are never dedup candidates.

## 4. Conflicting timestamps (R3)

| Group | Conflicting timestamps | Arising inside one file | …of which on adjacent lines | Copied into another file with the chunk | **Between files (copies disagree)** | Pressure-only / T/H involved | Files / dates affected |
|---|---|---|---|---|---|---|---|
| User01 | 3,992 | 3,992 | 3,992 | 375 | **0** | 3,928 / 64 | 86 / 91 |
| 22480 | 992 | 992 | 992 | 42 | **0** | 979 / 13 | 45 / 48 |
| 22482 | 1,225 | 1,225 | 1,223 | 34 | **0** | 1,196 / 29 | 49 / 52 |
| User07 | 4,788 | 4,788 | 4,788 | 472 | **0** | 4,746 / 42 | 100 / 106 |

- **Repeated copies never disagree.** Every conflict originates inside a single file, almost always as two
  consecutive lines with the same second. When that chunk is repeated in another file, the pair is repeated too.
- Conflicts are pressure-only in 97–99 % of cases. The pressure difference has a median of 52–104 ADC counts
  (p95 339–547, max up to 3,417). This fits two separate readings logged within one second, and A2 found 8–9 % of
  steps are ≤ 1 s. They are not copies of one reading.
- The 148 conflicts involving T/H include 29 with a sentinel (T = H = 0) on one side. Across all conflicts,
  104 involve a control-event row (e.g. `AHON`) logged in the same second.
- **R2 in the primary groups:** 4 cases (`NM` vs `WSTOP NM`; `NM` vs `AHOF NM`). Each is a control-event row
  repeating the values of the reading it belongs to.

## 5. Hypothetical de-duplication impact (simulation only)

Provisional primary cohort, second-resolution groups (User01, 22480, 22482, User07), 4,323,873 raw rows:

| Hypothetical policy | Rows after | Removed | % | Unresolved | Status |
|---|---|---|---|---|---|
| A1 — remove exact copies that also occur in another file | 4,136,683 | 187,190 | 4.33 % | 0 | simulated |
| A — remove all exact duplicates (incl. 872 within-file) | 4,135,811 | 188,062 | 4.35 % | 0 | simulated |
| B — one row per timestamp + values (event text must be chosen) | 4,135,807 | 188,066 | 4.35 % | 4 metadata choices | requires decision |
| C — one row per timestamp | 4,124,810 | 199,063 | 4.60 % | **10,997 conflicting timestamps** | requires decision |

Per group: `dedup_policy_impact.csv`. For the minute-resolution legacy groups every policy is marked
`not_applicable_minute_resolution`.

## 6. File boundaries vs sessions

Consecutive files in time order (`file_boundaries.csv`), with descriptive gap bins (no threshold chosen):

| Group | Boundaries | Overlap with repeated rows | 0–10 s (recording continues) | 30 min–2 h | > 2 h | Files with an internal gap > 2 h | Files spanning > 26 h |
|---|---|---|---|---|---|---|---|
| User01 | 150 | 10 | 0 | 1 | 139 | 12 | 10 |
| 22480 | 44 | 3 | 0 | 0 | 41 | 3 | 3 |
| 22482 | 48 | 3 | **10** | 13 | 22 | **29** | 4 |
| User07 | 99 | 2 | 0 | 0 | 97 | 3 | 2 |

- **For User01, 22480 and User07, most file boundaries fall in the long daytime gap.** In most cases one file
  holds one night. The exceptions are the duplicate-block boundaries and a few multi-night files.
- **22482 files are cut in the morning (06:1x–09:1x) while recording continues:**
  - 10 boundaries have the next file starting 2–5 s after the previous one ends;
  - the next file then holds that morning tail, a daytime gap and the following night (29 of 49 files contain an
    internal gap > 2 h);
  - the 13 boundaries in the 30 min–2 h bin measure 1,803–5,404 s, i.e. exactly 1–3 × 1,800 s + 3–8 s. One or
    more 30-minute upload chunks were lost at those cuts;
  - the quarantined pair shows the same 1,804 s pattern.
- **Conclusion on the working hypothesis:** *source file ≠ session* is confirmed quantitatively.
  - A file can contain parts of two nights (User01 12, 22482 29, 22480 3, User07 3 files).
  - One night can be split across two files (22482: 10 seamless cuts).
  - Repeated upload chunks make consecutive files overlap (18 boundaries in the primary groups).
  - Sessions must therefore be derived from the de-duplicated timeline, not from files. No gap threshold is set
    here (OPEN-06).

## 7. What the evidence supports, and what stays open

**Supported by the evidence (proposed, not accepted — D-014):**
- Extra copies of **repeated upload-chunk blocks** are exact copies and never disagree with the original. This
  holds across files (187,190 rows) and for the one within-file block (600 rows). Removing all but one copy would
  lose no information.

**Not decidable yet:**
- **Same-second rows with different values (10,997 timestamps).** They are distinct measurements, not duplicates.
  Keeping both, ordering them, or choosing one is a preprocessing question tied to alignment and resampling (P2).
  Policy C must not be applied by default.
- **272 adjacent same-second identical rows.** They could be a doubled log line or two identical readings; the
  data cannot tell.
- **Which event text to keep** for the 4 metadata-only cases, and how control-event rows are represented at all
  (OPEN-10, OPEN-15).
- **Minute-resolution legacy sources.** Duplicate concepts do not apply (OPEN-08, OPEN-13).
- **Session definition and gap threshold** (OPEN-06). Pending the temporal-gap analysis (A7).
- **Canonical interim representation** (row format, provenance columns, quality flags). Decided at P0 exit.

## 8. Limitations

- Repeated sequences shorter than 10 rows are not listed individually (they are included in the row counts).
- "Adjacent lines" refers to consecutive data rows. Structural lines between them are not counted.
- The analysis relies on the audit parser's year inference for `MM-DD` rows (D-007). Rows only match when
  timestamp *and* values agree, so an inference error would reduce, not create, duplicates.

## 9. Reproduce

```bash
python scripts/build_manifest.py
python scripts/audit_cross_file_duplicates.py     # writes outputs/qa/p0/duplicates/
python -m pytest tests/test_duplicates.py
```
