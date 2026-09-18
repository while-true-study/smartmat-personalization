# Reference final check

Source: `paper/manuscript/references.bib` and the citations of `paper/manuscript/manuscript_p16_final.md` (source
commit 62b1618). Checked against the reference list of
`paper/submission_final/manuscript/Applied_Sciences_SmartMat_Final.docx`.

**Rules for this step:**
- no reference was searched for, added, removed or edited;
- no DOI was guessed;
- the Word reference list is the P16 rendered list, in citation order, in the template's MDPI_8.1_references style
  (left-aligned so that long DOIs do not stretch lines).

## Structural audit (internal, complete)

| Check | Result |
|---|---|
| Distinct cited keys in the manuscript | 31 |
| Entries in references.bib | 31 |
| Cited keys missing from references.bib | none |
| references.bib entries never cited | none |
| Entries in the Word reference list | 31, numbered 1–31 in order of first citation |
| Duplicates in the Word reference list | none |
| DOIs in the Word list vs. references.bib | identical sets (29 DOIs; compared case-insensitively) |
| Entries without a DOI | 2 (below); none was added |
| Broken citation keys or unresolved `[@…]` in the Word text | none |

## Entries without a DOI (no DOI added)

| # | Key | Entry | Status |
|---|---|---|---|
| 1 | maeng2026icfice | The authors' ICFICE 2026 conference paper (proceedings Volume 17, Number 1, pp. 27–30) | No DOI in the source. Add one only if the proceedings publisher assigned it (external confirmation). |
| 9 | bai2018tcn | Bai, Kolter, Koltun, arXiv:1803.01271 (2018) | arXiv preprint, cited by its arXiv identifier; no DOI in the source. |

## Items for external confirmation

These items are not blocking, and nothing was changed.

- **References 10 and 13: conference dates.** These conference entries (Hammerla et al., UbiComp 2015; Stisen et
  al., SenSys 2015) give the place and year without the exact conference dates. MDPI's style normally lists the dates;
  add them only from the publisher record.
- **Reference 26: event location.** Wilson et al. (KDD 2020) is given as "Virtual Event, CA, USA, 2020", as in the
  source.

## Recorded, already resolved

- **Reference 1 and the front-matter Note: conference venue.** Both give Sapporo, Japan, 7–10 July 2026.
  `docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md` records a conflict with the Special Issue page, as the authors read it
  (Guam). Decision D-056 took the official KIICE programme as the primary source, so nothing is open. The cover letter
  does not name the venue.

## Status

- The structural audit is complete: every citation resolves, and there are no duplicates or DOI changes.
- Bibliographic completeness is **OPEN — EXTERNAL CONFIRMATION REQUIRED** for the items above.
