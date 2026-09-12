# [P0] Investigate provenance conflict between User03 legacy and User06

> Issue draft (GitHub CLI was not available when this was written). File it on GitHub with this title
> and body, then replace the "Tracking" cell of OPEN-01 in `docs/DECISIONS.md` with the issue link.

**Phase:** P0 — Dataset Audit & Data Freeze · **Open decision:** OPEN-01 · **Type:** provenance / subject identity
**Status:** evidence quantified (P0-A1, 2026-09-12); identity unconfirmed — waiting for the data provider

## Evidence
Reproducible analysis P0-A1 (`docs/P0_A1_PROVENANCE_REPORT.md`, code `scripts/audit_cross_subject_provenance.py`),
read-only, all 10 subject pairs × 3 comparison modes:

| Mode | User03 rows / sequences found in User06 | User06 rows / sequences found in User03 |
|---|---|---|
| A — exact timestamp + values | 10.94 % | 1.12 % |
| B — timestamp floored to the minute + values | **100.00 %** (107,256 / 107,256) | 65.35 % |
| C — 5-row value sequences, no timestamp | **100.00 %** (73,048 / 73,048) | 77.87 % |

- Offsets between matched rows (User06 − User03) are always 0–59 s (median 29 s), which is the signature
  of timestamps truncated to the minute.
- Each of the 7 User03 files corresponds to exactly one User06 file of the same night. Its whole content is a
  contiguous excerpt of that file: the User06 rows missing from User03 lie only at the start or end of the night.
  The longest block of identical value sequences in identical order spans 13,180 sequences (one full night).
- User06 additionally contains the nights starting 2025-10-03…10-05 and the early hours of 2025-10-14, which
  User03 does not.
- **No other subject pair shares any row or sequence**, in any mode. This includes User02 legacy, which was
  recorded on the same dates in the same export format (negative control).
- The User03 export is a spreadsheet-style CSV (seconds dropped, one event label normalised); User06 files are
  device logs with second resolution.
- Side result: User06 files 1003–1011 match User03 only when `.` before P1 is read as a delimiter (OPEN-12).

Interpretation limited to the data: **the observed overlap is inconsistent with treating the two sources as
independent subject recordings.** The data cannot tell whose recording it is.

## Research impact
- The data indicate that one physical recording exists under two subject IDs. Using both would double-count
  it, inflate the number of subjects, and leak data between "different" subjects (RESEARCH_PROTOCOL L7).
- Both sources are auxiliary, so the primary cohort (User01, User02, User07) is not affected. A1 found no
  overlap involving the primary candidates. Any use of auxiliary subjects (training pools, robustness checks)
  is blocked.
- Whatever the answer, the auxiliary pool holds at most two independent October-2025 recording streams
  (User02 legacy and the shared User03/User06 recording), not three.

## Required clarification (data provider)
1. Are "User03" and "User06" the same person?
2. If not, who was recorded on the nights 2025-10-06 → 10-13, and how was the User03 legacy CSV produced?
3. Which subject ID should the shared recording carry, and do User06's extra nights (10-03…10-05, 10-14)
   belong to the same person?

## Blocking decision
OPEN-01 → a decision entry that states which source/subject ID survives and which is excluded.
Blocks: any use of User03 or User06 data; OPEN-13 (auxiliary use); OPEN-16 (cohort).

## Handling until resolved
Subject mapping is unchanged. Neither source is used in any analysis beyond provenance/QA checks.
