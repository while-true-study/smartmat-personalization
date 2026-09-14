# P8 — Final blockers before submission and `v1.0-paper`

> **State at the end of the P8 formatting pass** (branch `paper/p8-manuscript`).
> - The submission candidate (`paper/submission_candidate/`) is formatting-complete for PI review.
> - The items below are still open. Each appears in the manuscript or drafts as a bracketed placeholder, never as a
>   fact, and `scripts/validate_manuscript_results.py` fails if one is removed or written as resolved.
> - `v1.0-paper` is not created, and P8 is not merged, until every gate in §6 holds. No frozen result changes.

## A. Scientific blockers

**None.** Every result and claim is fixed and validated:
- 102 source tokens resolve;
- Tables 1–5 trace 261 cells to frozen cells;
- the citation audit, the claim scan and the privacy scan pass;
- no conference text, table or figure is reused.

A scientific change would need a new evidence check and is out of scope for P8.

## B. Metadata blockers (PI / authors)

| # | Item | State | Placeholder | Tracking |
|---|---|---|---|---|
| B1 | Authors, order, affiliations, corresponding author, ORCID | open | `[AUTHOR NAMES AND ORDER — CONFIRM]`, `[AFFILIATIONS — CONFIRM]`, `[NAME AND E-MAIL — CONFIRM]`, `[ORCID iDs — CONFIRM]` | — |
| B2 | CRediT roles | open | `[CRediT ROLES — CONFIRM]`; `AUTHOR_CONTRIBUTIONS_DRAFT.md` | — |
| B3 | Funding (the conference statement is not copied) | open | `[FUNDING TO BE CONFIRMED BY PI]` | — |
| B4 | Conflicts of interest; other acknowledgments | open | `[CONFLICTS OF INTEREST — CONFIRM]`, `[OTHER ACKNOWLEDGMENTS — CONFIRM]` | — |
| B5 | Ethics / IRB information | open | `[ETHICS / IRB INFORMATION REQUIRED FROM PI]` | OPEN-26 |
| B6 | Informed consent wording. The provider's consent confirmation (D-002) is not an ethics approval and not the statement itself | open | `[INFORMED CONSENT WORDING REQUIRED FROM PI]` | OPEN-26 |
| B7 | GenAI disclosure approval. The text names both tools (§G below) | drafted; PI approval pending | §3.8 and Acknowledgments text | OPEN-28; D-053 |
| B8 | Conference final bibliography (proceedings volume, pages, DOI, URL) | open | `[PENDING: …]` in the rendered reference; `pending` field in `references.bib` | OPEN-27 |
| B9 | Conference copyright holder (no permission expected: nothing is reused) | open | `[COPYRIGHT HOLDER … — CONFIRM]` in the cover letter; `[PENDING]` in the disclosure draft | OPEN-27 |
| B10 | Keywords and working title (proposed; PI may adjust) | proposed | — | D-054 |

## C. External-release blockers

| # | Item | State | Placeholder | Tracking |
|---|---|---|---|---|
| C1 | Code license | open; the repository has no LICENSE file | `[LICENSE]` | OPEN-22 |
| C2 | Data license of `public_release_v1` | open | `[LICENSE]` | OPEN-22 |
| C3 | Hosting of the data (and of a code archive) | open | `[DATA REPOSITORY]`, `[CODE REPOSITORY]` | OPEN-23 |
| C4 | DOI (data; code archive) | open | `[DOI]` | OPEN-23 |
| C5 | PI approval of the release subset and of the final manuscript/release state | open | — | OPEN-24 |
| C6 | Public scope of the recording dates in committed repository files outside the release package (code availability stays conservative) | open | `[PI DECISION: public code release scope and license.]` | OPEN-25 |
| C7 | Interim data access ("on reasonable request", and from whom) | open | `[PI DECISION: …]` in the Data Availability Statement | — |

## D. Submission-format blockers

| # | Item | State |
|---|---|---|
| D1 | Applied Sciences Instructions for Authors read directly: section structure (separate Related Work and Limitations), Featured Application, abstract and keywords, reference style, cover-letter content, template version, file limits | open. mdpi.com returns HTTP 403 to automated access. The authors verified the Special-Issue items listed in `docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md` |
| D2 | Transfer into the current MDPI Word or LaTeX template: tables and figures at first citation, footnotes, back-matter order | open. The Markdown and CSV sources are ready for conversion |
| D3 | Reference style details: ISO 4 journal abbreviations; conference locations and dates for the 8 proceedings references without them | open. Rendered now in full names with DOIs (D-054) |
| D4 | First-page note wording for the extended conference paper | drafted as a placeholder note; confirm with D1 |
| D5 | Cover letter completion (`COVER_LETTER_DRAFT.md`) | drafted; placeholders B1, B3, B5, B6, B8, B9 |

## G. Generative-AI tools (OPEN-28, D-053)

| Product | Provider | Model / version | Evidence | Purpose |
|---|---|---|---|---|
| Claude Code (command-line client) | Anthropic | CLI 2.1.263 and 2.1.270; Claude Opus 5 (`claude-opus-5`) | local session logs of this repository | code drafting and debugging; analysis-workflow organization; repository documentation; reference-metadata checks; manuscript drafting |
| ChatGPT | OpenAI | historical model versions not consistently logged (stated as such, not inferred); GPT-5.6 Sol for the final manuscript-review interaction | authors' statement (P8 formatting pass) | research planning; analysis and protocol review; manuscript architecture; manuscript drafting; language refinement; consistency review |

No historical ChatGPT model version is inferred.

## 5. Production state (formatting pass)

| Item | State |
|---|---|
| Tables 1–5 (`scripts/export_manuscript_tables.py`) | done: Markdown and CSV with cell provenance |
| Tables S1–S19 and figure data | done: 31 CSV copies without calendar dates, plus Table S19 |
| Figures 1–4 and S1–S4 (`scripts/render_manuscript_figures.py`) | done: PNG, 300 dpi at print size (≥ 1,380 px wide), text ≥ 6 pt, no overlapping labels |
| Rendered manuscript and references (`scripts/build_submission_candidate.py`) | done: 31 references numbered by first appearance |
| Manuscript validator (`scripts/validate_manuscript_results.py`) | done: 11/11 checks pass; `--rerender-figures` also passes |
| Word/LaTeX template conversion | open (D2) |

## 6. Gates to `v1.0-paper`

- Every item in B, C and D is resolved, or deliberately stated as open in the submitted text with PI approval.
- The rendered manuscript and the validator pass on the final state. No rendered number may differ from its frozen cell.
- The frozen P3–P7 artifacts are unchanged against `p7-release-candidate`.
- PI approval (OPEN-24).
