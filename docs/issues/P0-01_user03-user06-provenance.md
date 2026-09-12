# [P0] Investigate provenance conflict between User03 legacy and User06

> Issue draft (GitHub CLI was not available when this was written). File it on GitHub with this title
> and body, then replace the "Tracking" cell of OPEN-01 in `docs/DECISIONS.md` with the issue link.

**Phase:** P0 — Dataset Audit & Data Freeze · **Open decision:** OPEN-01 · **Type:** provenance / subject identity

## Evidence
From the initial inventory (`docs/initial_dataset_inventory.md` §7.3), read-only analysis:
- Every row of source `user03_legacy` (7 nightly files, 2025-10-06 → 2025-10-13) equals a row of source
  `user06_auxiliary` after truncating User06 timestamps to the minute: 99.99–100 % containment per file.
- For the night starting 2025-10-09 the two sequences are identical row for row (15,717 rows). For the
  night starting 2025-10-11 both files have exactly 14,531 rows.
- User06 additionally covers 2025-10-03…10-05 and 10-13, which User03 does not.
- Negative control: `user02_legacy_csv` (same period, same export format) shares 0 % of rows with User06.
- The User03 files are spreadsheet-style CSV exports (seconds dropped, decimal points turned into
  commas in settings lines); User06 files are the original device logs with second resolution.
- Side result: this alignment confirms that `.` between timestamp and P1 in User06 files 1003–1011 is a
  delimiter (OPEN-12).

## Research impact
- The same physical recording currently exists under two subject IDs. Using both would double-count one
  person, inflate the number of subjects, and leak data between "different" subjects (RESEARCH_PROTOCOL L7).
- Both sources are auxiliary, so the primary cohort is not directly affected, but any use of auxiliary
  subjects (training pools, robustness checks) is blocked.
- If User03 and User06 are actually different people, one folder is mislabelled and the label of the
  shared recording is unknown.

## Required clarification (data provider)
1. Are "User03" and "User06" the same person?
2. If not, who was recorded on 2025-10-06 → 10-13, and how was the User03 legacy CSV produced?
3. Which subject ID should the shared recording carry?

## Blocking decision
OPEN-01 → a decision entry that states which source/subject ID survives and which is excluded.
Blocks: any use of User03 or User06 data; OPEN-13 (auxiliary use); OPEN-16 (cohort).

## Handling until resolved
Neither source is used in any analysis beyond provenance checks. P0 analysis A1
(`docs/P0_DATASET_AUDIT_PLAN.md`) re-implements the containment check reproducibly and extends it to all
subject pairs.
