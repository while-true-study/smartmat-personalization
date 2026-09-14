# P7 — Public data dictionary (`public_release_v1`)

> Column-level documentation of the public release package (D-049, D-050). The machine-readable window schema is
> `schema.json` in the package. Counts and ranges below are those of `public_release_v1`.

| | |
|---|---|
| Package | `data/release/public_release_v1/` (built by `scripts/build_public_release.py`; builder commit recorded in `manifest.json`) |
| Representation | model-ready windows (D-050, option A): one row per 40-s window, no row-level table, no raw log |
| Subjects | `User01`, `User02`, `User07` (streams `User01\|unknown`, `User02\|22480`, `User02\|22482`, `User07\|unknown`) |
| Time | relative only (D-049): seconds since the subject's anchor, night keys `D####`, readable times `D#### HH:MM:SS` |
| Model inputs | the 48 pressure columns only |
| Targets | `temperature`, `humidity` |

## 1. Files

| File | Rows | Content |
|---|---|---|
| `windows.parquet` | 575,265 | every window of the LOSO set (P3/P4) and of the RQ2 set (P5/P6), with membership flags |
| `splits/v1.0_loso/outer_folds.csv` | 1 per fold × session | outer LOSO folds |
| `splits/v1.0_loso/inner_folds.csv` | 1 per fold × inner split × session | inner two-way splits A/B |
| `splits/v1.0_personalization/chronological.csv` | 1 per budget × session × night | chronological personalization split |
| `control_events.csv` | 317 | User02 heater codes `AHON`/`AHOF` |
| `p5_plan_public.yaml` | — | frozen P5 plan, night ids mapped |
| `reference_digests.json` | 102 runs | SHA-256 of the frozen predictions |
| `schema.json` | — | window schema (types, units, ranges, roles) |
| `excluded_sources.csv` | 5 | sources not in the release |
| `manifest.json` | — | identity, counts, method, SHA-256 of every other file |
| `README.md` | — | release description |

`windows.parquet` is 29,955,714 bytes, stored in 5 row groups of 131,072 rows, sorted by `window_index`.

## 2. `windows.parquet`

Column legend: **In** = model input, **Tgt** = target, **Group** = provenance or grouping role.

| Column | dtype | Unit | Range in this release | Meaning | In | Tgt | Group | Privacy transformation |
|---|---|---|---|---|---|---|---|---|
| `window_index` | int64 | — | 0 … 575,264 | row number; windows in canonical first-row order, the order P3/P4/P5 use | no | no | order | new row number |
| `subject_id` | string | — | `User01`, `User02`, `User07` | anonymous subject | no | no | LOSO fold, personalization subject | anonymous ID of canonical_v1 (DATA_POLICY §3); no name, initials or folder name |
| `device_id` | string | — | `unknown`, `22480`, `22482` | mat hardware ID; 22480 and 22482 are two mats of User02 (one subject) | no | no | strata | kept: equipment ID, not a person (D-050) |
| `session_id` | string | — | `<subject>\|<device>\|S####`; 157 / 105 / 101 sessions with windows (User01 / User02 / User07; the split lists 157 / 105 / 102) | canonical recording session (D-024) | no | no | split unit (outer and inner LOSO) | sequence number only; no file reference |
| `sensor_phase` | string | — | `s1`, `s2` (User01); `not_applicable` | User01 sensor phase (D-019) | no | no | stratum; window boundary | none |
| `channel_quality_phase` | string | — | `normal`, `p1_transition`, `p1_response_shift` (22482 only) | 22482 channel-quality phase (D-022) | no | no | stratum; window boundary | none |
| `night_id` | string | — | `D0001` … `D0220` (User01), … `D0054` (User02), … `D0107` (User07) | night (noon to noon) of the target row | no | no | personalization partition unit; per-night metrics; bootstrap cluster | calendar date → relative night day (D-049) |
| `night_ordinal` | int16 | — | 1 … 151 / 51 / 100 | chronological number of the subject's recorded night | no | no | budget assignment (nights 1…b adaptation, b + 1 buffer, ≥ 16 primary test) | none (no date) |
| `window_start_time_s` | int64 | s | ≥ 0 | window start t0, seconds since the subject anchor | no | no | order; provenance | relative seconds (D-049) |
| `target_time_s` | int64 | s | `window_start_time_s` + 35 … 39 | time of the target row (last row of bin 7) | no | no | P6 heater context | relative seconds (D-049) |
| `in_loso` | bool | — | 574,849 true | window of the D-032 LOSO set (P3, P4) | no | no | window-set membership | none |
| `in_rq2` | bool | — | 574,848 true | window of the D-037 RQ2 set, also cut at night boundaries (P5, P6) | no | no | window-set membership | none |
| `s{k}_p{c}` (48 columns) | int16 | ADC count | 0 … 4095 | pressure channel P`c` (1…6) at step `k` (0…7): the last observed row of 5-s bin `k` | **yes** | no | — | none (sensor values; 4095 kept, D-033) |
| `temperature` | float64 | °C | labelled windows 17 … 38 | temperature at the target row | no | **yes** | — | none |
| `humidity` | float64 | %RH | labelled windows 6 … 95 | relative humidity at the target row | no | **yes** | — | none |
| `target_temp_valid` | bool | — | 574,823 true | D-025 temperature validity | no | label flag | — | none |
| `target_humidity_valid` | bool | — | 574,823 true | D-025 humidity validity | no | label flag | — | none |

- **Window rule (D-032):** 40-s windows of 8 bins × 5 s, stride 20 s, last observed row per bin, gaps of at most
  5 s. A window never crosses a session, device or phase boundary. RQ2 windows also never cross a night (D-037).
  - 574,432 windows are in both sets, 417 only in the LOSO set and 416 only in the RQ2 set (the night cut).
- **Model input:** `x[k, c-1] = s{k}_p{c} / 4095`, shape 8 × 6. The P4 derived families (MOVEMENT, CONTACT and
  their RAW combinations) are computed from these values by `src/features/pressure_features.py`. No precomputed
  feature is shipped.
- **Labelled window:** both validity flags true. The 442 unlabelled windows are never used for training or
  evaluation. Their target cells hold the recorded values, including sensor out-of-range values (temperature
  −254 … 256, humidity 0 … 152).
- **Target resolution:** as recorded (whole units). No missing value occurs in this release.
- **Per subject:** 289,672 (User01), 144,205 (User02), 141,388 (User07) windows.

## 3. Relative time (D-049)

- **Anchor:** local midnight of the date of the subject's first night, i.e. of the date of (first row − 12 h). One
  anchor per subject; both User02 mats share it.
- **Seconds:** `*_time_s` = timestamp − anchor, as integer seconds.
- **Night key:** `D####` = ⌊(time_s − 43,200) / 86,400⌋ + 1. The first night of every subject is `D0001`.
- **Readable time:** `D#### HH:MM:SS` with `D####` = ⌊time_s / 86,400⌋ + 1 (the relative calendar day) and the local
  clock time.
- **Preserved exactly:** order, gaps and durations, clock time of day, night grouping, night ordinals, the time
  alignment of the two User02 mats.
- **Removed:** calendar date, weekday, month and season as dates, and the calendar alignment between subjects.

## 4. Split files

All three are the protocol v1.0 split files with `start_timestamp` / `end_timestamp` (and, in the personalization
split, `night_id`) in relative form. Every other value is unchanged; the build-time equivalence gate compares the
public and private files (D-050).

| Column | Files | Meaning |
|---|---|---|
| `protocol_version`, `split_id` | all | `v1.0`; `v1.0_loso` or `v1.0_personalization` |
| `fold`, `held_out_subject` | LOSO | outer fold 1 / 2 / 3 and its held-out subject (User01 / User02 / User07) |
| `inner_split` | inner | `A` or `B` (the two inner subjects swap roles) |
| `budget_nights` | personalization | 0, 1, 3, 7 or 14 |
| `subject_id`, `device_id`, `session_id`, `sensor_phase`, `channel_quality_phase` | all | as in `windows.parquet` |
| `night_id`, `night_ordinal` | personalization | as in `windows.parquet` |
| `partition` | all | outer: `train` / `test`; inner: `inner_train` / `inner_val`; personalization: `adaptation` / `buffer` / `test` |
| `primary_test` | personalization | 1 if the night belongs to the common primary test span (ordinal ≥ 16) |
| `start_timestamp`, `end_timestamp` | all | first and last canonical row of the session (or session × night piece), `D#### HH:MM:SS` |
| `n_rows` | all | canonical rows in the session (or piece) |

- **Outer fold data:** windows with `in_loso = true`, partition = the outer split's partition of their
  `session_id`. The inner split gives `inner_train` / `inner_val` per session.
- **Personalization data:** windows with `in_rq2 = true` of one subject, partition = the personalization split's
  partition of their (`session_id`, `night_id`) piece for the chosen budget.
- `src/data/public_release.py` (`PublicRelease.fold_data`, `PublicRelease.subject_windows`) rebuilds exactly the
  arrays that P3/P4 and P5 used.

## 5. Other files

**`control_events.csv`** — `subject_id`, `device_id`, `time_s` (relative seconds), `time` (`D#### HH:MM:SS`),
`code` (`AHON` or `AHOF`).
- User02 only: 317 heater on/off codes, as parsed for the P6 heater-context strata (the last heater code of a row).
- Descriptive strata only (D-047). Never a model input.
- No raw event text, no other control code.

**`p5_plan_public.yaml`** — the committed P5 plan with every night id mapped to its `D####` key and the P3 run ids
and local run paths removed.
- Kept unchanged: base configurations, outer target-scaler statistics, base checkpoint weight digests, adaptation
  recipe, budgets and window counts.
- `primary_test.windows_sha256` is the private digest of the primary test windows. `manifest.json`
  (`p5_primary_windows`) records the matching digest of the public windows.

**`reference_digests.json`** — per frozen run: `n` prediction rows and the SHA-256 of `y_true` and of `y_pred` (float64
bytes in stored order).
- 3 P3 training-mean folds, 9 P3 RAW-TCN finals, 45 P4 finals, 45 P5 runs.
- The public reproduction must match them bitwise.

**`excluded_sources.csv`** — `source_id`, `subject_id`, `dataset_role`, `exclusion_reason`, `exclusion_confirmed_by`,
`exclusion_decision`.
- Five sources: one restricted metadata source, one quarantined source, two auxiliary legacy sources and the
  provider-confirmed invalid source.
- No data of these sources is in the release.

**`manifest.json`** — release version and identity of the frozen inputs:
- protocol, split and source-dataset hashes; base tag and builder commit;
- subjects, streams, counts, targets, pressure representation, the temporal method, window sets;
- the private/public equivalence result and the privacy checks passed;
- the SHA-256 of every other file.

## 6. Not in the release

- Raw log files, canonical rows, file names, source paths and provenance fields (`file_id`, `source_line_no`).
- Participant metadata (restricted) and anything from the excluded sources.
- Absolute timestamps and calendar dates.
- Inner-search runs, checkpoints and predictions. Checkpoints are rebuilt bitwise by the reproduction; the digests
  above fix the prediction values.
