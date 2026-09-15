# Submission candidate — README and checklist

> **Formatting-complete candidate for PI review. It is not a final submission.** Bracketed items in the manuscript
> are open placeholders, and none of them may be sent as written. The open items and their owners are listed in
> `docs/P8_FINAL_BLOCKERS.md` of the research repository.

## Contents

| Path | Content | Produced by |
|---|---|---|
| `manuscript/manuscript_rendered.md` | the manuscript with every number resolved, Tables 1–9 inlined, Figures 1–5 linked, citations numbered and the reference list rendered | `scripts/build_submission_candidate.py` |
| `manuscript/manuscript_source.md` | the source with its source tokens and `[@key]` citations | copy of `paper/manuscript/manuscript.md` |
| `manuscript/references.bib` | the 31 verified references | copy |
| `tables/` | Tables 1–9 as Markdown and CSV | `scripts/export_manuscript_tables.py` |
| `figures/` | Figures 1–5 (PNG, 300 dpi at print size) | `scripts/render_manuscript_figures.py` |
| `supplementary/tables/` | Tables S1–S34 and the figure source data (index: `supplementary/tables/README.md`) | `scripts/export_manuscript_tables.py` |
| `supplementary/figures/` | Figures S1–S4 | `scripts/render_manuscript_figures.py` |
| `drafts/` | cover letter, conference-extension disclosure, author contributions, data and code availability drafts | copies of `paper/manuscript/*_DRAFT.md` |
| `MANIFEST.json` | SHA-256 of every file above | `scripts/build_submission_candidate.py` |
| `FINAL_SUBMISSION_CHECKLIST.md` | the tick list that must be complete before submission | hand-written |

**Word file:** `python scripts/build_submission_docx.py --template <Applied Sciences Word template (.docx)>`
writes `outputs/p8/submission/manuscript_applsci.docx` (git-ignored). The journal restricts its templates to
submission for peer review, so neither the template nor template-formatted files are committed. While blockers are
open, the file starts with a review-draft notice.

**Excluded:** raw logs, the canonical dataset, the release windows (`windows.parquet`), participant metadata and
local paths. Every number comes from the frozen P3–P6 tables, and every table cell records its source cells
(`paper/manuscript/generated/tables/provenance.json`).

**Rebuild and check:**

```
python scripts/export_manuscript_tables.py
python scripts/render_manuscript_figures.py
python scripts/build_submission_candidate.py
python scripts/validate_manuscript_results.py            # draft checks
python scripts/validate_manuscript_results.py --final    # also fails while any placeholder or blocker remains
```

## Checklist before submission

### A. Author and PI metadata

- [ ] Authors, their order, affiliations, corresponding author and ORCID iDs (`[… — CONFIRM]`)
- [ ] CRediT roles (`drafts/author_contributions_draft.md`)
- [ ] Funding statement: `[FUNDING TO BE CONFIRMED BY PI]`. The conference paper's statement is not copied
- [ ] Conflicts of interest
- [ ] Other acknowledgments
- [ ] Generative-AI disclosure approved (Section 3.8 and Acknowledgments; OPEN-28): the ChatGPT model versions of
  earlier sessions are stated as not logged and are not inferred
- [ ] Keywords (seven are proposed) and the working title

### B. Ethics

- [ ] `[ETHICS / IRB INFORMATION REQUIRED FROM PI]`
- [ ] `[INFORMED CONSENT WORDING REQUIRED FROM PI]`. The data provider's consent confirmation is not an ethics
  approval and not the statement itself

### C. Release

- [ ] Data license, repository and DOI for `public_release_v1`; PI release approval. Until then the Data Availability
  Statement must not say "publicly available"
- [ ] Code license and the public scope of the repository (committed history contains recording dates)

### D. Journal format

- [ ] Live Applied Sciences Instructions page re-read (requirements were verified from the latest archived copy) and
  the current template version confirmed
- [ ] Word file built from the current template (`scripts/build_submission_docx.py`) and checked
- [x] Conference bibliography (Vol. 17, No. 1, pp. 27–30; D-056). No DOI or URL is confirmed, so none is printed
- [ ] Conference copyright holder and permission status
- [ ] Target Special Issue (Future Information & Communication Engineering 2026) confirmed by the PI
- [ ] Cover letter completed (`drafts/cover_letter_draft.md`)
