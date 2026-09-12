# Initial Dataset Inventory (P0, first pass)

| | |
|---|---|
| Date | 2026-09-12 |
| Scope | Read-only inventory of the delivered raw package. No cleaning, resampling, interpolation, windowing, splitting or normalisation was performed. |
| Raw root | `스마트 매트 데이터 정리/raw` (`configs/paths.yaml`) |
| Manifest | `data/interim/manifest/raw_file_manifest.csv`, SHA-256 `dcf25e98b7d6f3a7…` |
| Code | `scripts/build_manifest.py`, `scripts/audit_dataset.py`, parser `src/data/raw_parser.py` |
| Machine-readable results | `outputs/qa/dataset_audit/` (`file_audit.csv`, `source_summary.csv`, `subject_summary.csv`, `issues.csv`, `cross_file_time_overlap.csv`, `event_vocabulary.csv`, `audit_summary.json`) |

All counts are **raw row counts before de-duplication**. Dates for `MM-DD` rows are inferred
(see §5); every such row carries a `year_source` in the audit.

Policy references: identity and roles in `DATA_POLICY.md`; open questions (OPEN-xx) in `DECISIONS.md`.

---

## 1. Package overview

- 377 files, 211 MB. 375 under `raw/`, plus the provider's `README.md` and `metadata/dataset_manifest.csv`.
- 373 sensor log files (`.txt`, `.csv`), 2 participant-metadata workbooks (`.xlsx`, restricted).
- File counts per folder match the provider's `dataset_manifest.csv` exactly
  (user01 154, user02/legacy_csv 7, user02/mat_22480 47 incl. 2 quarantined, user02/mat_22482 49,
  user03_legacy 7, user06_auxiliary 11, user07 100).
- 4,688,889 parsable sensor rows in total.
- No byte-identical files (the provider had already removed 6 duplicate User01 files).

## 2. Subjects and devices

| subject_id | Role (candidate) | Device(s) | Sensor files | Rows | First row | Last row |
|---|---|---|---|---|---|---|
| User01 | primary | unknown | 152, 151 with rows (+2 xlsx) | 2,248,820 | 2025-08-25 22:21 | 2026-04-02 06:40 |
| User02 | primary (mats) + auxiliary (legacy) + quarantined | 22480, 22482, unknown (legacy), unresolved (2 files) | 103 | 1,160,172 | 2025-10-05 00:50 | 2026-09-11 06:20 |
| User03 | auxiliary | unknown | 7 | 107,256 | 2025-10-06 21:33 | 2025-10-13 09:15 |
| User06 | auxiliary | unknown | 11 | 164,185 | 2025-10-03 19:39 | 2025-10-14 01:05 |
| User07 | primary | unknown | 100 | 1,008,456 | 2026-04-03 19:00 | 2026-07-19 05:11 |

Five subject IDs exist; no other subject appears in any file. Device IDs appear only for User02.

**Timeline.** User01 phase_a (2025-08-25 → 09-01) · gap · User02-legacy / User03 / User06 (2025-10-03 → 10-14,
concurrent) · gap · User01 phase_b → phase_c (2025-11-05 → 2026-04-02) · User07 (2026-04-03 → 07-19 05:11) ·
User02 mats (2026-07-19 19:41 → 09-11). The primary subjects hand over within a day of each other, which
suggests the same physical mat(s) were reused (OPEN-04).

## 3. Per-source inventory

| source_id | Files | Rows | Period | Start dates¹ | Format family | Timestamp | Median Δt | Rows/min | Schema | P ch. | temp / humid range² |
|---|---|---|---|---|---|---|---|---|---|---|---|
| user01_phase_a | 6 | 56,244 | 2025-08-25 → 09-01 | 6 | plain CSV, no header | `YYYY-MM-DD HH:MM:SS` | 2 s | 30 | 10-col | 6 | 26–29 °C / 56–80 % |
| user01_phase_b | 57 | 792,627 | 2025-11-05 → 2026-01-01 | 55 | 42 plain (1105–1216) + 15 quasi-JSON (1217–1231) | `MM-DD HH:MM:SS` (no year) | 3 s | 20 | 10-col | 6 | 0–31 / 0–54 |
| user01_phase_c | 89 | 1,399,949 | 2026-01-01 → 04-02 | 80 | quasi-JSON (0106, 0107 plain) | `MM-DD HH:MM:SS` | 3 s | 20 | 10-col | 6 | 0–31 / 0–56 |
| user02_legacy_csv | 7 | 71,370 | 2025-10-05 → 10-13 | 7 | CSV with header, BOM | `YYYY-MM-DD H:MM` (**no seconds**) | — | 24 | 10-col | 6 | 24–32 / 38–71 |
| user02_mat_22480 | 45 | 431,471 | 2026-07-19 → 09-05 | 42 | quasi-JSON | `MM-DD HH:MM:SS` | 3 s | 20 | 10-col; 11-col from 08-29 | 6 | 0–34 / 0–68 |
| user02_mat_22480_prefix_mismatch | 2 | 22,205 | 2026-08-24 → 08-26 | 2 | quasi-JSON | `MM-DD HH:MM:SS` | 3 s | 20 | 10-col | 6 | 0–36 / 0–92 |
| user02_mat_22482 | 49 | 635,126 | 2026-07-19 → 09-11 | 36 | quasi-JSON | `MM-DD HH:MM:SS` | 3 s | 20 | 10-col; 11-col from 08-31 | 6 | **−254–256 / 0–262** |
| user03_legacy | 7 | 107,256 | 2025-10-06 → 10-13 | 7 | CSV with header, BOM | `YYYY-MM-DD H:MM` (**no seconds**) | — | 20 | 10-col | 6 | 0–34 / 0–72 |
| user06_auxiliary | 11 | 164,185 | 2025-10-03 → 10-14 | 11 | plain CSV, no header | `YYYY-MM-DD HH:MM:SS` | 3 s | 23 | 10-col (see §8.3) | 6 | 0–34 / 0–72 |
| user07 | 100 | 1,008,456 | 2026-04-03 → 07-19 | 97 | quasi-JSON | `MM-DD HH:MM:SS` | 3 s | 20 | 10-col | 6 | 0–31 / 0–82 |

¹ Distinct start dates of files (shifted by −12 h to count nights); files are not sessions (§7.2).
² Including sentinel zeros and glitches (§8.5). All temperature and humidity values are integers
(resolution 1 °C and 1 %RH); no decimal value occurs in any sensor row.

Temperature and humidity columns are present in every sensor source. Every source has exactly six
pressure channels; values are 12-bit ADC counts (0–4095).

## 4. Raw format families

All families share the logical row `timestamp, P1…P6, temp, humid, event`.

| Family | Where | Shape |
|---|---|---|
| Plain, full timestamp | User01 phase_a, User06 | `2025-08-25 22:21:51,0,0,0,0,0,0,28,68, 자리비움` (no header) |
| Plain, MM-DD | User01 phase_b 1105–1216, phase_c 0106–0107 | `11-05 19:23:17,0,0,0,0,4008,0,26,30, DM` |
| Legacy CSV (Excel-style export) | User02 legacy, User03 | header `TS(YYYY-MM-DD HH:MM),FSR1(A0),…,FSR6(A5),Temp(℃),Hum(%),Event`; rows `2025-10-05 0:50,0,0,0,170,77,6,25,67, 우로이동` |
| Quasi-JSON upload chunks | User01 phase_b 1217+, phase_c, User02 mats, User07 | `{"<YYYY-MM-DD_HH-MM-SS>": {"csvData": "<multi-line CSV>"}}`, optionally nested under `"smartmat"` / `"smartmat_<device>"` → `"logs"` |

Quasi-JSON details:
- Not valid JSON: the `csvData` strings contain raw newlines. Files must be parsed line by line.
- One chunk per upload (about every 30 min). In inspected chunks the key is the upload time and the first
  row is about 30 min earlier.
- Daily files are fragments cut from a longer export: some start inside a chunk (e.g. `phase_c/0101.txt`
  starts with rows whose key is in the previous file) or without the opening brace
  (`sm22482_0719.txt`), and some end with a dangling `},`.
- Encoding: UTF-8 everywhere except `user02/legacy_csv/user2_20251008_log.csv` (CP949). The legacy CSVs
  carry a UTF-8 BOM. Line endings are CRLF, with LF inside some JSON string blocks.

## 5. Timestamps and sampling interval

| Format | Sources | Year | Resolution |
|---|---|---|---|
| `YYYY-MM-DD HH:MM:SS` | User01 phase_a, User06 | explicit | 1 s |
| `YYYY-MM-DD H:MM` | User02 legacy, User03 | explicit | **1 min** (seconds lost; 20–24 rows share each minute) |
| `MM-DD HH:MM:SS` | all other sources | **missing** | 1 s |

Year inference for `MM-DD` rows (audit only, D-007): enclosing JSON log key (3,684,631 rows), next key
in the same file (2,029 rows), else `year_hint` from config (603,174 rows: User01 phase_b 1105–1216 → 2025,
phase_c 0106–0107 → 2026). New-year boundaries are handled (`12-31` rows under a `2026-01-01` key → 2025).
No row is left undated. The raw data carry no timezone.

Sampling: nominal interval 3 s (20 rows/min) for all current-firmware sources, 2 s for User01 phase_a.
The 95th percentile of within-file steps is 4–5 s. Gaps > 10 min: User01 phase_b 10, phase_c 11,
User02 22480 6, 22482 39, User07 5, quarantined 2 (largest in `1112_log_누락부분있음.txt`: 174 min, which
matches the provider's "part missing" note).

## 6. Schema differences

1. **10-column vs 11-column.** From 2026-08-29 (22480) and 2026-08-31 (22482) the firmware inserts a
   `device_id` column: `timestamp,device_id,P1,…,P6,temp,humid,event`. `sm22482_0831.txt` mixes both
   schemas. Values in the column always equal the folder device (22480 / 22482).
2. **Column names.** Current logs use `P1…P6,temp,humid`; legacy CSVs use `FSR1(A0)…FSR6(A5),Temp(℃),Hum(%)`.
   The correspondence P_k ↔ FSR_k (analog pin A_{k−1}) is assumed by position, not documented.
3. **Event vocabulary.** Old firmware (phase_a, legacy, User06) writes Korean movement labels
   (`위로이동/아래로이동/우로이동/좌로이동/자리비움`) and long control names (`EVENT:BURST_HOT_STEP_DOWN`).
   Newer firmware writes compressed codes (`UM/DM/RM/LM/NM`, `AHON`, `BHSDOWN`, …). The provider's legend
   (restricted workbook, sheet "로그압축용어") defines movement codes as derived from pressure-sum shifts and
   `NM` as "all six sensors below the occupancy threshold". Control codes describe heater actions and set-point
   changes (e.g. `BHSDOWN` = judged hot → set-point −0.5 °C, `FOH` = forced off at ≥ 45 °C). Counts per
   source: `outputs/qa/dataset_audit/event_vocabulary.csv`.
4. **Pressure scale.** Cells at the ADC maximum 4095 are frequent in User01 (phase_a 25,627; phase_b 197,035;
   phase_c 59,284) and in the 2025-10 sources (User02 legacy 36,378; User03 27,327; User06 30,815), rare in
   User02 22480 (17 cells) and absent in User02 22482 (max 3,731) and User07 (max 4,023). Hardware, gain or
   body-weight differences are not yet distinguishable (OPEN-17).

## 7. Duplicates and overlaps

### 7.1 Byte-level and whole-content duplicates
- Byte-identical files: **none**.
- Files whose complete data-row content is identical: **none**.

### 7.2 Row overlap between files of the same subject
Adjacent daily files repeat the same upload chunks, so the same rows appear in two (sometimes three) files:

| Subject | File pairs | Shared identical rows | Examples |
|---|---|---|---|
| User01 | 10 | 96,614 | `phase_c/0117` ↔ `0118` (16,204); `phase_b/1231` ↔ `phase_c/0101` (5,994) |
| User02 | 8 | 90,021 | `sm22482_0822` ↔ `0823` (21,606); `sm22480_0821` is contained in both `0822` and `0823` |
| User07 | 2 | 17,360 | `0703` ↔ `0704` (11,579) |

19 files span more than 26 h (up to 57 h, `sm22482_0823.txt`). **Files do not correspond to nights or
sessions**, and splitting by file would leak (RESEARCH_PROTOCOL L2).

Within files, 110 files contain repeated identical rows and 283 contain repeated second-level timestamps
(largest counts in the minute-resolution legacy CSVs, where they are partly an artefact of lost seconds).

### 7.3 Rows shared across different subjects — **User03 ⊂ User06**
Every row of `user03_legacy` (99.99–100 % per file) equals a row of `user06_auxiliary` after truncating
User06 timestamps to the minute. For 2025-10-09 the two sequences are identical row for row (15,717 rows);
for 10-11 both files have 14,531 rows. User06 additionally covers 10-03…10-05 and 10-13 that User03 does
not. Control: User02 legacy shares 0 % with User06. The same physical recording therefore exists under two
subject IDs (OPEN-01). Neither may be used until resolved, and never both (L7).

### 7.4 Concurrent recordings on two devices of User02
53 file pairs from 22480 and 22482 overlap in time: about 505 h in total (253 h of minutes with rows from
both devices). In jointly recorded minutes both mats register occupancy (movement label ≠ `NM`) 66.8 % of the
time, only 22480 23.3 %, only 22482 7.8 %. Same-minute temperature differs by a median −2 °C
(correlation 0.28) and humidity by −19 %RH (22480 minus 22482). 22480 records mostly 19:00–06:00; 22482
often records around the clock. The physical arrangement is unknown (OPEN-03). Whatever it is, the two
streams of one night must stay in the same split group (L8).

## 8. Filename / device and structural anomalies

### 8.1 Device prefix mismatch (quarantined)
`user02/mat_22480/_prefix_mismatch/sm22482_0824.txt` and `sm22482_0825.txt`:
- stored in the 22480 archive by the provider, filename prefix `sm22482_`, JSON root key `smartmat_22482`;
- 0824 and 0825 are the only dates for which `mat_22480/` has a file and `mat_22482/` does not
  (both lack 0725, 0729, 0730); `mat_22480/`'s own 0824/0825 files overlap them in time (7.0 h and 5.5 h)
  with no shared rows;
- span 2026-08-24 07:06 → 08-26 06:39 (around-the-clock, like other 22482 files).
Evidence points to device 22482; attribution stays `unresolved` until confirmed (D-006, OPEN-02).
Subject is User02 either way.

### 8.2 Provider annotations in filenames
| File | Note (translated) | Audit observation |
|---|---|---|
| `user01/phase_b/1112_log_누락부분있음.txt` | "part missing" | 174-min gap inside the night |
| `user01/phase_b/1217_로그압축.txt` | "log compressed" | first quasi-JSON file of phase_b |
| `user01/phase_c/0125_센서변경.txt` | "sensor changed" | pressure-sensor replacement on 2026-01-25 (also in metadata) |
| `user06_auxiliary/1008_log_데이터중 07시20분 11초에서 51초사이에 에러.txt` | "error between 07:20:11 and 07:20:51" | ESP32 crash dump (watchdog panic) and a 544-s backward time step in this file |

### 8.3 User06 delimiter anomaly
In files 1003–1011 (148,357 rows) the character between timestamp and P1 is `.` instead of `,`
(`2025-10-03 19:40:10.4012,0,0,2,…`). Treating `.` as a delimiter yields six pressure channels; the value
after `.` is 0 in 97 % of rows and reaches ≥ 1000 in 2,564 rows, i.e. a pressure distribution, not fractional
seconds. Under this reading User06 rows coincide exactly with User03 rows (which have a proper `FSR1`
column), confirming it. Files 1012–1013 use `,`. Adoption for preprocessing: OPEN-12.

### 8.4 Non-data lines inside logs
| Kind | Where | Count |
|---|---|---|
| Serial/uploader messages (Firebase upload, upload-cycle notices) | User01 phase_b 4,896, phase_c 213; User06 96; User02 22482 2 | 5,207 lines |
| `[NVS] 저장: …` settings writes | User01 phase_b/c 92, User02 legacy 40, User03 86, User06 118 | 336 lines in 56 files |
| ESP32 crash dump | `user06_auxiliary/1008_…` | 1 block |
| Blank lines | `phase_b/1118_log.txt` (every other line blank) and others | 13,739 in phase_b |
| Empty CSV rows `,,,,,,,,,` | `user02/legacy_csv/user2_20251008_log.csv` | 1,175 |
| Malformed/truncated | `phase_b/1118_log.txt` (2 JSON keys missing the year), `user2_20251008_log.csv` (`2025-10-09 09,,,,,,,,,`) | 3 |
| Messenger recipient IDs | User06 logs (`chatIDs=…`, `chatCSV=…`) | 6 lines — privacy, see DATA_POLICY §5 |

In legacy CSVs, NVS values appear as `targetTemperature=27,00`, i.e. a decimal point was turned into a comma.
Together with the lost seconds, this indicates the legacy CSVs were re-saved through a spreadsheet tool.

### 8.5 Value anomalies
- **Sentinel zeros.** `temp == 0` and `humid == 0` together in 311 files (User01 phase_b 2,307 rows,
  User02 22482 ~1,400, others < 150 per source). In inspected chunks they occur at the first row of an
  upload chunk (sensor not yet read).
- **Glitches.** `sm22482_0808.txt`: temperature −254 to 256 (147 rows out of range) and humidity up to 262 (50 rows).
- **Out-of-order time.** `sm22482_0816.txt` one backward step of 1,797 s (~one upload chunk);
  `user06_auxiliary/1008_…` one step of 544 s.
- **Empty file.** `user01/phase_c/0209.txt` has 24 upload chunks with headers only and no data rows.
- **All-zero pressure rows** (nobody on the mat): 2–7 % in current-firmware sources, 23 % in User03 and
  35 % in User06 (these two include long unoccupied periods).

## 9. Restricted content

`user01/metadata/meta_legacy_package.xlsx` and `meta_longitudinal.xlsx` hold participant metadata including
demographic and health information. Contents are not reproduced here (DATA_POLICY §5, D-008). Operational facts
taken from them: pressure-sensor replacement on 2026-01-25; indoor heating season start (written as
2026-11-18, most likely 2025-11-18); log-format change (written as 2026-12-17, matching the 2025-12-17 file);
event-code legend. The date inconsistencies are OPEN-14. The two workbooks are not byte-identical; the
longitudinal version adds notes and the code-legend sheet.

## 10. Implications to settle before preprocessing

1. Subject identity: User03 ⊂ User06 (OPEN-01); User02 concurrent devices (OPEN-03); unknown devices (OPEN-04).
2. Build interim tables by **de-duplicated time span**, not by file (OPEN-06, OPEN-07).
3. Adopt explicit timestamp and delimiter policies (OPEN-08, OPEN-12); legacy minute-resolution sources
   cannot support second-level windowing without a decision.
4. Define target handling for sentinels, glitches and heater control (OPEN-09, OPEN-10); exclude
   heater-control events from inputs (L9).
5. Account for the User01 sensor replacement and cross-subject pressure-scale differences (OPEN-11, OPEN-17).

## 11. Reproduce

```bash
python scripts/build_manifest.py   # verifies raw against the existing manifest, refuses on change
python scripts/audit_dataset.py    # ~1 min; writes outputs/qa/dataset_audit/
python -m pytest
```

The User03/User06 containment (§7.3) and User02 co-occupancy (§7.4) figures come from one-off read-only
checks run during this inventory. They are to be added to `audit_dataset.py` in the next P0 step.
