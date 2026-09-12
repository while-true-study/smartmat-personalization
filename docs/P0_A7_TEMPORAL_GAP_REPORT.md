# P0-A7 — Temporal Gap Distribution & Session Boundary Audit

| | |
|---|---|
| Phase / analysis | P0 — Dataset Audit & Data Freeze / A7 (`docs/P0_DATASET_AUDIT_PLAN.md`; partly covers A6) |
| Date | 2026-09-12 |
| Code | `src/data/temporal.py` (analysis), `scripts/audit_temporal_gaps.py`; reuses A5's `upload_copy_mask` from `src/data/duplicates.py` |
| Tests | `tests/test_temporal_gaps.py` (synthetic log text only) |
| Command | `python scripts/audit_temporal_gaps.py` (≈ 2 min) |
| Artifacts | `outputs/qa/p0/temporal/` — `gap_summary.csv`, `gap_distribution.csv`, `gap_ecdf.csv`, `large_gaps.csv`, `user02_22482_gap_patterns.csv`, `threshold_sensitivity.csv`, `session_candidate_summary.csv`, `figures/` (regenerable, not committed) |

Evidence only. No session is fixed, no session ID is created, and no row is removed, re-timed, resampled or
interpolated.

## 1. Purpose

A5 showed that source files are not sessions. A7 measures the real elapsed-time structure of each primary
timeline and asks what candidate session-gap thresholds would do to it. The results feed OPEN-06.

**Timelines** (one per subject/device; User02's devices are never mixed):

| Timeline | Definition |
|---|---|
| A — raw | all parsed rows in time order |
| B — audit view | A minus the later copies of repeated upload blocks identified by A5 (in memory only) |

Timeline B keeps same-second rows with different values, isolated identical rows, legacy minute-resolution rows,
and all cross-device and cross-subject observations.

Rows excluded from B: User01 96,616; 22480 33,007; 22482 40,810; User07 17,381.
- These are 24 rows more than A5's policy-A1 count (and, for 22482, equal to A1 plus the 600-row within-file
  block). Timeline B drops copied blocks row for row, including both lines of 24 same-second identical pairs that
  were copied along with their chunk. Their originals stay in the earlier file.
- User03, User06, User02 legacy and the quarantined files appear only as reference statistics in the artifacts.

## 2. Sampling structure

Timeline B, time difference between consecutive rows ("steps"):

| | User01 | 22480 | 22482 | User07 |
|---|---|---|---|---|
| Steps | 2,152,203 | 398,463 | 594,315 | 991,074 |
| Median / p90 / p95 / p99 | 3 / 4 / 5 / 5 s | 3 / 4 / 5 / 5 s | 3 / 4 / 5 / 5 s | 3 / 4 / 5 / 5 s |
| 0 s (two readings in one second, kept) | 4,047 | 1,008 | 1,332 | 4,862 |
| 1–5 s sampling incl. jitter | 99.0 % | 99.4 % | 99.5 % | 99.0 % |
| 6–15 s (a few samples missing) | 13,812 | 1,424 | 1,545 | 4,097 |
| 15 s–5 min | 3,750 | 12 | 59 | 767 |
| 5–30 min | 4 | 0 | 4 | 0 |
| 30 min–2 h | 5 | 2 | 15 | 1 |
| > 2 h | 151 | 44 | 55 | 100 |

- Sampling is identical across timelines: nominal 3 s with 1–5 s jitter.
- In Timeline A, the same-second count is inflated (User01 100,663; 22480 34,015; 22482 42,142; User07 22,243)
  only by the repeated copies. Nothing else in the step distribution differs between A and B.
- **User01 and User07 have a recurring ≈ 2-minute pause.** Of the 60 s–5 min gaps, 1,812 of 2,205 (User01) and 266
  of 356 (User07) fall between 120 and 140 s. In 84–86 % of these the mat is occupied on both sides. They do not
  coincide with upload-chunk boundaries (0.1–0.2 %, the same as ordinary steps) or with file boundaries. Their
  cause is unknown.

## 3. Gap distribution

Timeline B, counts per bucket (`gap_distribution.csv`; ECDF in `figures/gap_ecdf.png`):

| Bucket | User01 | 22480 | 22482 | User07 |
|---|---|---|---|---|
| 5–15 s | 13,812 | 1,424 | 1,545 | 4,097 |
| 15–30 s | 1,027 | 12 | 35 | 313 |
| 30 s–1 min | 518 | 0 | 16 | 98 |
| 1–5 min | 2,205 | 0 | 8 | 356 |
| 5–15 min | 1 | 0 | 2 | 0 |
| 15–30 min | 3 | 0 | 2 | 0 |
| 30–60 min | 3 | 0 | 10 | 0 |
| 1–2 h | 2 | 2 | 5 | 1 |
| 2–6 h | 2 | 0 | 6 | 3 |
| 6–12 h | 86 | 2 | 13 | 6 |
| > 12 h | 63 | 42 | 36 | 91 |

**The distribution is strongly bimodal.** Gaps are either ≤ 5 min (recording hiccups) or > 2 h (the daytime
pause between nights). Between 5 min and 2 h there are only 9 (User01), 2 (22480), 19 (22482) and 1 (User07)
gaps. 22482 is the exception, with a cluster at 30–60 min.

## 4. Threshold sensitivity

Candidate sessions per recording night (noon-to-noon), Timeline B (`threshold_sensitivity.csv`,
`figures/threshold_sessions.png`):

| Threshold | 1 min | 2 min | 5 min | 10 min | 15 min | 30 min | 45 min | 60 min | 90 min | 120 min |
|---|---|---|---|---|---|---|---|---|---|---|
| User01 (151 nights) | 15.67 | 12.85 | 1.07 | 1.07 | 1.06 | 1.04 | 1.03 | 1.02 | 1.02 | 1.01 |
| 22480 (45 nights) | 1.04 | 1.04 | 1.04 | 1.04 | 1.04 | 1.04 | 1.04 | 1.04 | 1.00 | 1.00 |
| 22482 (50 nights) | 1.66 | 1.56 | 1.50 | 1.46 | 1.46 | 1.42 | 1.22 | 1.22 | 1.14 | 1.12 |
| 22482 + chunk-gap bridge¹ | — | — | 1.24 | — | 1.20 | 1.16 | 1.12 | 1.12 | 1.12 | — |
| User07 (100 nights) | 4.58 | 3.77 | 1.02 | 1.02 | 1.02 | 1.02 | 1.02 | 1.02 | 1.02 | 1.01 |

¹ Gaps equal to 1–3 upload chunks (n × 1,800 s ± 10 s) treated as a missing interval inside a session. The
bridge changes nothing for User01, 22480 or User07.

Median candidate-session duration (hours): User01 12.0–12.3, 22480 6.0–6.5, User07 7.8–8.0 for every threshold
from 5 to 120 min. 22482 rises from 8.5 (5–30 min) to 10.2 h (120 min).

- **Sharp transition between 2 and 5 min** for User01 and User07. Thresholds below 5 min split nights at the
  ≈ 2-minute pauses (median session 3–17 min).
- **A wide plateau from 5 to 90 min** for User01, 22480 and User07. The session count changes by ≤ 7 over that
  range, so the choice within it barely matters for these three.
- **No plateau for 22482 without the bridge** (1.50 → 1.12 per night). With the bridge, 22482 levels off at
  1.12–1.24 per night.
- **Timeline A vs B:** session counts and median durations are identical at every threshold for all four
  timelines. The repeated copies do not distort session statistics.
- **Three boundaries kept separate (30 min, Timeline B):**
  - calendar date: 150/157, 44/47, 47/71, 99/102 candidate sessions cross midnight;
  - file: sessions spanning ≥ 2 files — 0, 0, 12 (25 with the bridge), 0;
  - files containing ≥ 2 sessions — 5, 1, 30, 2.
  A day is not a session, and a file is not a session.
- **Night structure (30 min, Timeline B), start / end time p50 (p10–p90):**

  | | Start | End | Median duration |
  |---|---|---|---|
  | User01 | 18:33 (17:56–20:28) | 06:45 (05:57–08:10) | 12.1 h |
  | 22480 | 19:59 (18:56–21:24) | 01:59 (01:03–06:30) | 6.0 h |
  | 22482 | 21:41 | 07:14 | 8.5 h (10.0 h with the bridge) |
  | User07 | 19:25 (18:15–21:07) | 02:30 (01:26–06:35) | 7.8 h |

- **Session length is quantised in 30-minute chunks.** At 30 min the duration is within 15 s of a multiple of
  30 min for 100 % of 22480 sessions, 89 % of 22482, 90 % of User07 and 54 % of User01. Chance would give ≈ 2 %.
  Recording appears to be kept in whole upload chunks. Session start/end times therefore reflect the chunk grid,
  not necessarily when a person got on or off the mat. Mechanism: provider question (§8).

## 5. User02/22482 missing-chunk pattern

`user02_22482_gap_patterns.csv` lists all 34 gaps of 25 min–12 h:

| Measure | Value |
|---|---|
| Chunk-aligned gaps (n × 1,800 s + 3…8 s) | **13 of 34** (chance ≈ 1.2 %); ≈ 30 min: 8, ≈ 60 min: 4, ≈ 90 min: 1 |
| At a file boundary | **13 of 13** |
| Clock time (gap start) | 05:56–07:17, 13 different mornings between 2026-07-24 and 09-09 |
| Mat occupied before and after (NM share 0 on both sides) | 9 of 13 |
| T/H across the gap | before vs after within 0–2 °C and 0–4 %RH in 12 of 13 |
| Other groups | User07: 1 aligned gap (11 chunks, > 2 h); User01/22480: long aligned gaps only at file boundaries (24–71 chunks), all > 2 h |

- **Evidence:** in 22482 the export cuts files in the morning while recording continues, and 1–3 whole upload
  chunks are lost at those cuts. In most cases the person is on the mat and the microclimate is unchanged on both
  sides of the gap. This looks like data loss inside one recording rather than the end of a recording.
- **Treating the gaps as breaks** (30 min, plain) gives 71 sessions: 15 are sub-1-hour fragments, 13 of them
  exactly one or two chunks (600 / 1,200 rows), mostly left alone after a lost chunk. **Treating them as missing intervals** gives
  58 sessions: median 10.0 h instead of 8.5 h, p10 1.35 h instead of 0.50 h, and 25 sessions span two files.
  Which representation is right is not decided here.
- The quarantined files follow the same pattern (1,804 s between them; OPEN-02).

## 6. What this means for sessionization

1. **Files and calendar days are not session units**, confirmed again (§4). Sessions must come from the
   de-duplicated per-device timeline.
2. **Threshold below 5 min is not viable.** It turns the ≈ 2-minute pauses into session breaks.
3. **Threshold between ≈ 5 and 90 min gives the same structure** for User01, 22480 and User07 (≈ 1 session per
   night).
4. **22482 needs explicit handling of lost upload chunks.** No single threshold both avoids splitting at lost
   chunks and still separates genuine 30–90-min interruptions without a rule for the chunk-aligned gaps.
5. **Gaps inside a session remain.** Sessions will contain 2-minute pauses (User01/User07), 6–15 s sample
   losses, same-second double readings and, with the bridge, 30–90-min missing intervals. Windowing must treat
   these explicitly (P2): a session is a grouping unit, not a guarantee of continuous data.
6. **Leakage.** Night-scale sessions keep correlated data together. Short fragments (e.g. lone 30-min chunks)
   would otherwise become separate groups that could land in different folds. A split protocol may still group
   at a coarser level (recording night per subject) on top of sessions (P2).

## 7. Recommended candidate (Proposed — D-015; not accepted)

**Candidate session policy:**
- A new session starts after a gap **> 30 min** in the de-duplicated per-device timeline.
- **Exception:** a gap of exactly 1–3 upload chunks (n × 1,800 s ± 10 s, n ≤ 3) is recorded as a *missing
  interval within the session*, not a break.
- Timestamps, rows and gaps are never altered. Session membership is a label.

| Criterion | Assessment |
|---|---|
| 1. Sampling jitter and ≈ 2-min pauses are not breaks | yes (30 min ≫ 5 min) |
| 2. Known upload-chunk losses are not over-split | yes, through the explicit bridge (22482: 71 → 58 sessions) |
| 3. Long interruptions are separated | yes: every gap > 2 h and every non-aligned gap > 30 min is a break |
| 4. Similar structure across subjects/devices | 1.04 / 1.04 / 1.16 / 1.02 sessions per night |
| 5. Conservative for leakage | night-scale units; 30 min sits in the plateau, so ±15 min around it changes ≤ 5 sessions per timeline |

**Why 30 min rather than another plateau value:** the choice is insensitive (§4). 30 min is the smallest value
that sits at the upload-chunk scale while keeping the genuine, non-aligned 30–60-min interruptions of User01 and
22482 as breaks. 45–60 min would merge those without a rule; 5–15 min would leave more 22482 fragments. The
choice was made on data structure (gap distribution, chunk mechanics), not on any model result; no model has
been trained.

## 8. Unresolved

- **Acceptance of D-015** (threshold and bridge rule) — together with D-014 at P0 exit.
- **Provider confirmation of the export/upload mechanics:**
  - Are recordings kept only as whole 30-min chunks?
  - Why are chunks lost at the morning file cuts of 22482?
  - What causes the ≈ 2-min pauses?
- **Isolated single-chunk recordings** (e.g. afternoon 30–60-min blocks on 22480/22482): are they genuine short
  uses of the mat, or noise? Include, flag or exclude — no decision.
- **Within-session gaps and windowing** (maximum gap a window may span) — P2.
- **Split grouping level** (session vs recording night) — P2.
- **Sampling change points per period** (A6 remainder, e.g. User01 phase_a vs later phases) — not analysed here.
- **Reference sources** (User06, quarantined, legacy minute-resolution) — not used for the threshold, and no
  session statistics derived for them.

## 9. Reproduce

```bash
python scripts/build_manifest.py
python scripts/audit_temporal_gaps.py      # writes outputs/qa/p0/temporal/ (+ figures/)
python -m pytest tests/test_temporal_gaps.py
```
