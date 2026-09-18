# P16 — Reference final check

> Checked against `paper/manuscript/references.bib` and `manuscript_p16_final.md` only (no web search, no new
> reference, no guessed DOI). Earlier claim-level audit: `docs/P8_CITATION_AUDIT.md` (42 cited claims, all PASS).

## Automated result (`scripts/validate_p16_submission.py`, check "citations")

| Check | Result |
|---|---|
| Missing cite keys | none |
| Unused references | none (31 entries, 31 cited) |
| Duplicate entries (same title or same DOI) | none |
| Citation order | numbered in order of first citation; reference list in the same order |
| Title and year present | all 31 entries |
| Venue (journal, book title, publisher or preprint) present | all 31 entries |

## Entries without a DOI

| Key | Status | External check |
|---|---|---|
| `maeng2026icfice` | conference paper; volume, issue and pages recorded; whether a DOI or a paper-specific official URL exists is unconfirmed | confirm with the conference publisher |
| `bai2018tcn` | preprint | optional: confirm whether an archival version should be cited |

## Citation contexts changed by the editorial revision

The Introduction and Related Work were restructured; each cited sentence keeps its claim and scope. Changes to check
once by an author:

| Location | Citation | Change |
|---|---|---|
| Introduction ¶3 | `hammerla2015pairwise` | now also cited for "random splits over overlapping sensor segments overstate accuracy", the same claim as in Section 2.3 and Section 3.3 |
| Introduction ¶5 | `gama2014survey` | cited for "the earliest nights may not represent the later period" (concept drift), as before |
| Section 5.4 | `gama2014survey`, `kadlec2011adaptation` | one citation group for drift monitoring and adaptive soft-sensor estimators (unchanged since the previous candidate) |
