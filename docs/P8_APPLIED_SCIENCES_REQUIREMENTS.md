# P8 — Applied Sciences submission requirements

> **Status categories:**
> - **MDPI-WIDE VERIFIED:** a publisher-level statement read directly in an official MDPI document.
> - **APPLIED SCIENCES VERIFIED:** read directly on an Applied Sciences-specific official page. **No item has this
>   status yet.**
> - **NEEDS APPLIED SCIENCES FINAL CHECK:** anything journal-specific not yet read on the journal's own page.
>
> **Sources (2026-09-14):**
> - **T: the MDPI *Applied Sciences* Word template** (`applsci-template.docx`, a copy in the project's journal
>   materials, not in this repository). Its placeholder copyright line reads "© 2025". This file was read directly.
>   It is an official MDPI document, but a template, not the Instructions for Authors page; which template version is
>   current must still be confirmed.
> - **S: web-search summaries of official mdpi.com pages.** They are secondary: every mdpi.com page (Instructions for
>   Authors, ethics, reference guide, layout, LaTeX, the template download) returned HTTP 403 to automated access via
>   WebFetch and direct requests.
>
> **No fixed "percentage of new content" for extended conference papers was found in any source, so none is used.**
>
> **Final integration pass (2026-09-14):** no status changed. mdpi.com still returned HTTP 403, so nothing became
> APPLIED SCIENCES VERIFIED. The manuscript consequences of items 2, 3, 7, 10 and 12 were updated. Item 15 stays
> conservative MDPI-wide / other-journal practice and is not treated as an Applied Sciences rule.

| # | Requirement | Evidence | Status | Manuscript consequence |
|---|---|---|---|---|
| 1 | Article sections: Introduction, Materials and Methods, Results, Discussion; Conclusions (not mandatory); Patents (optional); abbreviations and appendices optional | T (section list and notes); S (required-section list) | NEEDS APPLIED SCIENCES FINAL CHECK | Current: 1 Introduction, 2 Related Work, 3 Materials and Methods (protocol §3.5), 4 Results, 5 Discussion, 6 Limitations, 7 Conclusions. The template does not list separate Related Work or Limitations sections. If the journal requires its structure, Related Work moves into §1 and Limitations into §5, with the content unchanged |
| 2 | **Featured Application** (Applied Sciences): a short description of the application, encouraged but not mandatory | T | NEEDS APPLIED SCIENCES FINAL CHECK | final wording in the manuscript as a standalone paragraph (evaluation framework; offset correction and negative transfer "in three held-out cases"; no clinical, pressure-injury or population claim). Removable at formatting if the journal does not use it |
| 3 | Abstract: one paragraph of about 200 words at most; structured background–methods–results–conclusions without headings; must not contain results absent from the main text or exaggerate the conclusions | T; S | NEEDS APPLIED SCIENCES FINAL CHECK | Abstract finalised in the integration pass: 200 words rendered, one paragraph in the order problem–design–adaptation–positive–negative–interpretation/limit; all 3 numbers tokenised |
| 4 | Keywords: three to ten | T; S | NEEDS APPLIED SCIENCES FINAL CHECK | 8 keywords |
| 5 | References: numbered in order of appearance, in square brackets before punctuation ([1], [1–3], [1,3]); a DOI for every reference where available; example formats for journal articles, proceedings, unpublished work ("submitted; accepted; in press") and websites | T; S | the MDPI referencing rules are **MDPI-WIDE VERIFIED** (T). The Applied Sciences-specific style is NEEDS APPLIED SCIENCES FINAL CHECK | `references.bib` holds DOIs for every reference that has one; the Markdown uses keys, converted to numbers in order of first appearance at formatting |
| 6 | Supplementary materials: citations there must also appear in the main reference list | T | MDPI-WIDE VERIFIED | S-tables cite nothing outside the main list |
| 7 | Author Contributions with CRediT roles; authorship limited to substantial contributors | T | MDPI-WIDE VERIFIED | skeleton with every role `[CONFIRM]` (`paper/manuscript/AUTHOR_CONTRIBUTIONS_DRAFT.md`); no role assigned before PI confirmation |
| 8 | Funding: "This research received no external funding" or funder and grant number; APC funding; standard funder names | T | MDPI-WIDE VERIFIED | `[FUNDING TO BE CONFIRMED BY PI]`; the conference paper's funding is not carried over |
| 9 | Institutional Review Board Statement: for studies involving humans, the approving body and protocol code/date, or a justified waiver, or "Not applicable". Studies requiring ethical approval must name the authority and approval code in Methods | T | MDPI-WIDE VERIFIED | `[ETHICS / IRB INFORMATION REQUIRED FROM PI]` (OPEN-26). The provider consent confirmation (D-002) is not an IRB approval |
| 10 | Informed Consent Statement for research involving humans ("obtained from all subjects", or a justified waiver) | T | MDPI-WIDE VERIFIED | `[INFORMED CONSENT WORDING REQUIRED FROM PI]`; the provider statement (D-002) is recorded as a note for the PI only, not as the statement |
| 11 | Data Availability Statement is always required: where the data are, or why they are not available (privacy/ethics); MDPI suggested statements; data sharing encouraged. Methods: disclose any restrictions on the availability of materials, data, code or protocols at submission | T | MDPI-WIDE VERIFIED | `DATA_AVAILABILITY_DRAFT.md` / `CODE_AVAILABILITY_DRAFT.md` state the current restrictions and keep `[DATA REPOSITORY]`, `[DOI]`, `[LICENSE]` |
| 12 | **Generative-AI disclosure:** Materials and Methods must describe any use of generative AI for text, data, graphics, study design, analysis or interpretation (superficial editing excepted). The Acknowledgments carry the tool, version and purpose statement | T | MDPI-WIDE VERIFIED | **Drafted (D-052; OPEN-28 open for PI approval).** §3.8 describes the uses and the author-side controls (tests, frozen-result checks, deterministic tables, clean-checkout reproduction; no number accepted from AI output alone). The Acknowledgments use the template sentence with the inventoried tool (Claude Code 2.1.263/2.1.270, model Claude Opus 5), plus a placeholder for any other tool (`docs/P8_FINAL_BLOCKERS.md` §2) |
| 13 | Conflicts of Interest statement, including any funder role | T | MDPI-WIDE VERIFIED | [PI] |
| 14 | Figures and tables cited in order, placed near their first citation | T | MDPI-WIDE VERIFIED | follows the table/figure selection |
| 15 | Extended conference papers: expand to research-article size; cite the conference paper and note it on the first page; obtain the copyright holder's permission if needed; disclose the extension and the changes in the cover letter | S (other MDPI journals' instructions) | **Conservative MDPI-wide/other-journal practice; Applied Sciences-specific confirmation pending** | kept as manuscript policy: first-page note, citation, copyright check, cover-letter paragraph (`CONFERENCE_EXTENSION_DISCLOSURE_DRAFT.md`) |
| 16 | Prior publication: manuscripts must not be published or under consideration elsewhere, except conference proceedings papers | S (Applied Sciences instructions) | NEEDS APPLIED SCIENCES FINAL CHECK | disclose the ICFICE paper |
| 17 | Cover letter: required; significance, context, scope fit | S | NEEDS APPLIED SCIENCES FINAL CHECK | drafted at submission time |
| 18 | Template version, file format and size limits, Special Issue rules | not read | NEEDS APPLIED SCIENCES FINAL CHECK | confirm at submission |
| 19 | Word or page limit | not found | NEEDS APPLIED SCIENCES FINAL CHECK | none assumed |
| 20 | Peer-review model; APC (information) | S | NEEDS APPLIED SCIENCES FINAL CHECK | information only |

## Search-summary sources (S), 2026-09-14

These pages returned HTTP 403 when opened directly:
- https://www.mdpi.com/journal/applsci/instructions
- https://www.mdpi.com/authors/references, https://www.mdpi.com/files/authors/mdpi_references_guide.pdf
- https://www.mdpi.com/ethics
- https://www.mdpi.com/journal/information/instructions, https://www.mdpi.com/journal/materials/instructions
- https://www.mdpi.com/journal/applsci/special_issues

## Final check procedure

1. Open the Applied Sciences Instructions for Authors and the current template in a browser. Record the date and
   exact wording, and move items to APPLIED SCIENCES VERIFIED only when read there.
2. Confirm the section structure (item 1) and the extended-conference-paper wording (item 15) for Applied Sciences.
3. Re-map sections to the template if required. Science content must not change.
