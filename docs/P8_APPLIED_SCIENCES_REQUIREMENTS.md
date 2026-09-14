# P8 — Applied Sciences submission requirements

> **Status (submission-closure pass, 2026-09-15):** each item is VERIFIED, NOT APPLICABLE or NEEDS FINAL CHECK.
> - VERIFIED means read directly in an official source listed below. A search summary never counts.
>
> **Sources:**
> - **I: Applied Sciences Instructions for Authors,** `https://www.mdpi.com/journal/applsci/instructions`.
>   - The live page returns HTTP 403 to automated access; so it did again on 2026-09-15.
>   - Read directly in the **Internet Archive snapshot of 2025-11-17** (the latest archived copy; checked 2026-09-15).
>     It is an official Applied Sciences page, but ten months old.
>   - **Residual step:** before submission, open the live page in a browser and confirm that nothing below has
>     changed (item 21).
> - **T: the local Applied Sciences Word template** (`applsci-template.dot` and `applsci-template.docx` in the
>   project's journal materials, not in this repository), inspected on 2026-09-15.
>   - Its header reads "Appl. Sci. 2025, 15, x FOR PEER REVIEW" and its copyright line "© 2025", so it is the 2025
>     template.
>   - Local template inspected; current-version confirmation pending (item 18).
> - **A: the authors' reading of current Applied Sciences Special Issue pages** (formatting pass). Superseded where I
>   covers the same item.
> - **S (2026-09-14): search summaries.** Kept for history only; no status rests on them.
>
> **No general "percentage of new content" rule applies.** I states four conditions for expanded conference papers
> and no percentage (item 15). The 50 % rule of an older conference-specific Special Issue is not adopted.

| # | Requirement (source text in brief) | Evidence | Status | Manuscript consequence |
|---|---|---|---|---|
| 1 | Article structure: Abstract, Keywords, Introduction, Materials and Methods, Results, Discussion, Conclusions (optional). Research manuscript sections: Introduction, Materials and Methods, Results, Discussion, Conclusions (optional); back matter Supplementary Materials, Acknowledgments, Author Contributions, Conflicts of Interest, References | I; T | VERIFIED | All required sections are present. Separate Related Work (§2) and Limitations (§6) sections are kept: I says the structure "should include" these sections and prohibits no additional one. If the editor asks, Related Work can become §1.1 and Limitations a Discussion subsection, with the content unchanged |
| 2 | Featured Application: "Authors are encouraged to provide a concise description of the specific application or a potential application of the work. This section is not mandatory." | I; T | VERIFIED | KEEP (conservative wording). Removable as a standalone block |
| 3 | Abstract: about 200 words maximum; single paragraph; structured without headings | I; T | VERIFIED | 200 words rendered; one paragraph |
| 4 | Keywords: three to ten, specific yet common in the discipline | I; T | VERIFIED | 7 proposed (PI to confirm) |
| 5 | References: numbered by appearance (tables and figure legends included); journal pattern "Author 1, A.B.; Author 2, C.D. Title. Abbreviated Journal Name Year, Volume, page range"; proceedings pattern with conference location, country and date; DOIs encouraged | I; T | VERIFIED | rendered in these patterns: ISO abbreviations from the NLM Catalog, conference locations and dates from Crossref, DOIs for 29 entries. The ICFICE entry lacks proceedings pages or DOI (blocker, item 22) |
| 6 | Supplementary Materials: name and title of each element, "Figure S1: title, Table S1: title" | I; T | VERIFIED | back-matter paragraph lists Figures S1–S4 and Tables S1–S19 in this form, with the template's link wording |
| 7 | Author Contributions with the CRediT statement pattern; every author meets the criteria and approved the version | I; T | VERIFIED | skeleton, all `[CONFIRM]` (PI) |
| 8 | Funding: all sources, grant numbers, APC funding | I; T | VERIFIED | `[FUNDING TO BE CONFIRMED BY PI]` |
| 9 | Institutional Review Board Statement: for human data, the Declaration of Helsinki plus IRB/ethics-committee approval (code, date, committee), or the committee's exemption with the reason, or the legislation under which approval is not required | I; T | VERIFIED | `[ETHICS / IRB INFORMATION REQUIRED FROM PI]`. Provider permission (D-002) does not meet any of these routes (`docs/P8_PI_APPROVAL_CHECKLIST.md`) |
| 10 | Informed Consent Statement for human data; example wordings | I; T | VERIFIED | `[INFORMED CONSENT WORDING REQUIRED FROM PI]` |
| 11 | Data Availability Statement: where the data are, or the restriction; suggested statements; restrictions disclosed at submission; deposit in a trusted repository recommended, or the reason given | I; T | VERIFIED | current-state text (release candidate, not published). Code availability and the reproduction statement sit in this section: the template has no separate sections for them |
| 12 | GenAI: disclose in Materials and Methods how GenAI was used (superficial editing excepted); Acknowledgments sentence with tool, version and purpose; GenAI cannot be an author | I; T | VERIFIED | §3.8 and Acknowledgments (D-053); PI approval pending (OPEN-28) |
| 13 | Conflicts of Interest section before the reference list, including any funder role | I; T | VERIFIED | `[CONFLICTS OF INTEREST — CONFIRM]` |
| 14 | Figures after the paragraph of first citation (Word); tables near first citation; table fonts not smaller than 8 pt; images at least 1000 px | I; T | VERIFIED | rendered manuscript and DOCX place every table and figure after its first citation; table text 8–9 pt; figures ≥ 1,380 px wide |
| 15 | Expanded conference papers: (1) expanded to research-article size; (2) the conference paper cited and noted on the first page; (3) permission from the copyright holder if the authors do not hold it; (4) the cover letter discloses the conference paper and states what changed | I (Applied Sciences page) | VERIFIED | (1) full article; (2) first-page note and reference [1]; (3) copyright holder to confirm, and no conference material reused; (4) cover letter. No percentage claimed |
| 16 | Not published previously and not under consideration in another journal; preprints accepted if not peer-reviewed | I | VERIFIED | the ICFICE paper is disclosed under item 15 |
| 17 | Cover letter required: significance and scope fit; any prior MDPI submission acknowledged. Mandatory statements: "We confirm that neither the manuscript nor any parts of its content are currently under consideration for publication with or published in another journal." and "All authors have approved the manuscript and agree with its submission to Applied Sciences." Reviewer suggestions go in the system, not the letter | I | VERIFIED | `COVER_LETTER_DRAFT.md` carries both statements. The approval statement needs every author's approval before it is sent |
| 18 | Word or LaTeX template encouraged; Word as one file with figures inserted; total files ≤ 120 MB; the templates are for submission for peer review only, not for posting online | I; T | template use and limits VERIFIED; **current template version NEEDS FINAL CHECK** (the local one is 2025) | DOCX built from the local template by `scripts/build_submission_docx.py` into `outputs/` (git-ignored; the template and template-formatted files are not committed) |
| 19 | Article length limit | I (none stated for articles) | NOT APPLICABLE | none assumed |
| 20 | Peer-review model and APC | I | NOT APPLICABLE (information, no manuscript text) | — |
| 21 | Live Instructions page equals the archived snapshot | I (snapshot only) | NEEDS FINAL CHECK | read the live page before submission; update any changed item |
| 22 | Conference reference complete (proceedings volume, pages, DOI or URL, if they exist) | ISSN Portal: the proceedings series is ISSN 2765-3811 (online); KIICE lists ICFICE 2025 as Vol. 16, No. 1 | NEEDS FINAL CHECK | the paper's own pages or DOI were not found in an official record. Kept out of the text; blocker OPEN-27 |
| 23 | Special Issue requirements | none selected | NOT APPLICABLE (until the PI selects one) | if selected, read that Special Issue page directly |
| 24 | Author information: full names; PubMed-format affiliations; corresponding author; e-mails of all authors displayed; ORCID encouraged | I | VERIFIED | placeholders only (PI) |
| 25 | Abbreviations defined at first use in the abstract, the main text and the first figure or table | I | VERIFIED | MAE, RMSE, ReLU and TCN defined at first use; Figure 1 caption defines them; an Abbreviations section follows the template |
| 26 | Software name and version, and whether the code is available, stated in Materials and Methods | I | VERIFIED | §3.7 "Software" bullet; code availability in the Data Availability Statement |

## Archived-page evidence

- Snapshot list: `https://web.archive.org/cdx/search/cdx?url=www.mdpi.com/journal/applsci/instructions`. The latest
  capture is 2025-11-17 (HTTP 200).
- Page read: `https://web.archive.org/web/20251117021001/https://www.mdpi.com/journal/applsci/instructions`.
- The quoted rules are in the sections "Manuscript Submission Overview", "Manuscript Preparation", "Research and
  Publication Ethics" and "Preprints and Conference Papers" of that page.
