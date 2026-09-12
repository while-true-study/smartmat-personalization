# [P0] Investigate provenance conflict between User03 legacy and User06

> Issue draft (GitHub CLI was not available when this was written). File it on GitHub with this title
> and body, then replace the "Tracking" cell of OPEN-01 in `docs/DECISIONS.md` with the issue link.

**Phase:** P0 — Dataset Audit & Data Freeze · **Open decision:** OPEN-01 (closed) · **Type:** provenance / subject identity
**Status: Resolved 2026-09-13 (D-017).** The data provider confirmed that the User06 data are wrong because of a
setting problem and that the User06 source should be left out. Resulting handling:
- User03 ≠ User06; the subjects are not merged.
- `user06_auxiliary` is `excluded_invalid`: excluded from all analyses, models and public analysis data; the raw
  files are kept unchanged.
- `user03_legacy` stays auxiliary. It is valid User03 data (PI, 2026-09-13; D-021). Only the User06 source is
  invalid. Whether auxiliary data are used at all is OPEN-13.

If this issue is filed on GitHub, file it as closed with this resolution.

History: evidence quantified (P0-A1, 2026-09-12); identity answered (User03 and User06 are different people, PI,
2026-09-12); provisional quarantine (D-013, superseded).

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
1. ~~Are "User03" and "User06" the same person?~~ Answered 2026-09-12: they are different people.
2. Since they are different people, whose body was on the mat during the nights 2025-10-06 → 10-13, and how was
   the User03 legacy CSV produced? For example: exported from the User06 device, a shared device, or mis-filed?
3. Which subject should the overlapping measurements be attributed to, and do User06's extra nights
   (10-03…10-05, 10-14) belong to User06?

## Blocking decision
OPEN-01 → a decision entry (superseding D-013) that states to which subject the overlapping measurements
belong and whether they may be used.
Blocks: any use of the overlapping recording; OPEN-13 (auxiliary use). The provisional primary cohort
(User01, User02, User07) is not blocked.

## Handling (final, D-017)
User03 and User06 stay distinct subjects. The User06 source is `excluded_invalid` (analytical exclusion; raw
archive untouched). User03 legacy remains a valid auxiliary source (D-021).
